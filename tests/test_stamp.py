"""What the driver stamps into a measured record: `stamp_result` in scripts/bench."""

import json
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "scripts", "bench")


def stamped(lokprof_version):
    with open(BENCH) as f:
        text = f.read()
    source = re.search(r"^stamp_result\(\) \{.*?^PY\n\}\n", text, re.S | re.M).group(0)
    cell = {"target": "LOKEN", "model": "m", "prompt": "custom", "iterations": [{}]}
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "cell.json")
        with open(path, "w") as f:
            json.dump({"results": [cell]}, f)
        env = {**os.environ, "OLLAMA_VER": "", "VLLM_VER": "", "LOKPROF_VER": lokprof_version}
        subprocess.run(
            ["bash", "-c", source + 'stamp_result "$1" 1 100 image gguf loken', "bash", path],
            env=env,
            check=True,
        )
        with open(path) as f:
            return json.load(f)


class Stamp(unittest.TestCase):
    def test_the_record_names_the_lokprof_that_measured_it(self):
        self.assertEqual(stamped("0.6.0")["lokprof_version"], "0.6.0")

    def test_no_version_read_adds_no_field(self):
        self.assertNotIn("lokprof_version", stamped(""))


if __name__ == "__main__":
    unittest.main()
