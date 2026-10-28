"""Which result files a resumed campaign keeps: `cell_current` in scripts/bench."""

import json
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "scripts", "bench")


def cell_current_source():
    """The `cell_current` function of scripts/bench, as bash source."""
    text = open(BENCH).read()
    m = re.search(r"^cell_current\(\) \{.*?^PY\n\}\n", text, re.S | re.M)
    return m.group(0)


def kept(record, stamp, keep_earlier=False):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(record, f)
    env = dict(os.environ, OLLAMA_VER="0.40.11", VLLM_VER="")
    env.pop("KEEP_EARLIER_BUILDS", None)
    if keep_earlier:
        env["KEEP_EARLIER_BUILDS"] = "1"
    try:
        r = subprocess.run(
            ["bash", "-c", cell_current_source() + f'cell_current "{f.name}" {stamp}'], env=env
        )
        return r.returncode == 0
    finally:
        os.unlink(f.name)


def record(build, loken_iterations):
    return {
        "engine_build": build,
        "ollama_version": "0.40.11",
        "results": [
            {"target": "ollama", "iterations": [{"tokens_per_second": 9.0}]},
            {"target": "loken", "iterations": loken_iterations},
        ],
    }


class Resume(unittest.TestCase):
    def test_a_complete_cell_of_this_build_is_kept(self):
        self.assertTrue(kept(record(42, [{"tokens_per_second": 10.0}]), 42))

    def test_an_earlier_build_is_measured_again_by_default(self):
        self.assertFalse(kept(record(41, [{"tokens_per_second": 10.0}]), 42))

    def test_an_earlier_complete_cell_is_kept_when_asked(self):
        self.assertTrue(kept(record(41, [{"tokens_per_second": 10.0}]), 42, keep_earlier=True))

    def test_a_cell_that_lost_an_iteration_is_measured_again_when_keeping_earlier_builds(self):
        partial = record(41, [{"tokens_per_second": 10.0}, {"tokens_per_second": 11.0}])
        partial["results"][1]["iteration_errors"] = ["#3: connection closed during headers"]
        self.assertFalse(kept(partial, 42, keep_earlier=True))
        self.assertTrue(kept(partial, 41), "the build that measured it keeps what it has")

    def test_a_failed_engine_is_measured_again_whatever_the_build(self):
        self.assertFalse(kept(record(41, []), 42, keep_earlier=True))
        self.assertFalse(kept(record(42, []), 42))


if __name__ == "__main__":
    unittest.main()
