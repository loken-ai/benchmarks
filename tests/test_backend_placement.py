"""Whether loken ran wholly on a backend: `loken_placements` and `wholly_on` in fair-run.sh."""

import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FAIR_RUN = os.path.join(HERE, "..", "scripts", "engines", "fair-run.sh")


def functions(*names):
    with open(FAIR_RUN) as f:
        text = f.read()
    return "".join(re.search(rf"^{n}\(\) \{{.*?^\}}\n", text, re.S | re.M).group(0) for n in names)


def line(placement):
    return (
        "2026-11-15T15:00:22.404060Z \x1b[32m INFO\x1b[0m loken::inference::engine::llm_engine::loading: "
        f"✅ qwen3 loaded: layers {placement} (kv_quant=Off, kv_ctx=Some(40960))\n"
    )


def judge(backend, log_text):
    """The placements a log holds, and whether they are wholly on `backend`."""
    with tempfile.TemporaryDirectory() as logs:
        log = os.path.join(logs, "loken.log")
        with open(log, "w") as f:
            f.write(log_text)
        script = functions("loken_placements", "wholly_on") + (
            'p=$(loken_placements "$2"); printf "%s\\n" "$p"; wholly_on "$1" "$p" && echo yes || echo no'
        )
        r = subprocess.run(["bash", "-c", script, "bash", backend, log], capture_output=True, text=True)
    *placements, verdict = r.stdout.splitlines()
    return [p for p in placements if p], verdict == "yes"


class Placement(unittest.TestCase):
    def test_every_layer_on_the_backend(self):
        self.assertEqual(judge("opencl", line("opencl(0):0-28")), (["opencl(0):0-28"], True))

    def test_a_segment_on_the_host_after_the_first_is_seen(self):
        placements, wholly = judge("opencl", line("opencl(0):0-20, CPU:20-28"))
        self.assertEqual(placements, ["opencl(0):0-20, CPU:20-28"])
        self.assertFalse(wholly)

    def test_a_second_model_on_the_host_counts(self):
        self.assertFalse(judge("vulkan", line("vulkan(0):0-36") + line("CPU:0-24"))[1])

    def test_the_host_alone(self):
        self.assertFalse(judge("opencl", line("CPU:0-24"))[1])

    def test_no_model_loaded(self):
        self.assertEqual(judge("opencl", "nothing\n"), ([], False))


if __name__ == "__main__":
    unittest.main()
