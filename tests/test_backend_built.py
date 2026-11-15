"""Whether the lokend measured was built with a backend: `backend_built` in scripts/bench."""

import json
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "scripts", "bench")


def backend_built(backend, answer):
    with open(BENCH) as f:
        text = f.read()
    source = re.search(r"^backend_built\(\) \{.*?^\}\n", text, re.S | re.M).group(0)
    script = 'curl() { printf "%s" "$ANSWER"; }\n' + source + 'backend_built "$1"'
    r = subprocess.run(
        ["bash", "-c", script, "bash", backend],
        capture_output=True,
        text=True,
        env={**os.environ, "ANSWER": answer, "LOKEN_URL": "http://loken"},
    )
    return r.stdout


def devices(features):
    return json.dumps({"devices": [], "summary": {"compiled_features": features}})


class BackendBuilt(unittest.TestCase):
    def test_a_build_without_vulkan(self):
        self.assertEqual(backend_built("vulkan", devices({"cuda": True, "opencl": True, "vulkan": False})), "no")

    def test_a_build_with_opencl(self):
        self.assertEqual(backend_built("opencl", devices({"cuda": True, "opencl": True, "vulkan": False})), "yes")

    def test_a_server_that_does_not_say(self):
        self.assertEqual(backend_built("vulkan", devices({})), "")
        self.assertEqual(backend_built("vulkan", ""), "")


if __name__ == "__main__":
    unittest.main()
