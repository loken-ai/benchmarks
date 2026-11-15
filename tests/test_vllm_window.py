"""The window vLLM is started with: `cell_context` and `failure_reason` in fair-run.sh, and the launchers."""

import os
import re
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINES = os.path.join(HERE, "..", "scripts", "engines")
FAIR_RUN = os.path.join(ENGINES, "fair-run.sh")


def function(name):
    with open(FAIR_RUN) as f:
        text = f.read()
    return re.search(rf"^{name}\(\) \{{.*?^\}}\n", text, re.S | re.M).group(0)


def cell_context(*args):
    r = subprocess.run(
        ["bash", "-c", function("cell_context") + 'cell_context "$@"', "bash", *args],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


def failure_reason(log_text):
    with tempfile.TemporaryDirectory() as logs:
        with open(os.path.join(logs, "vllm.log"), "w") as f:
            f.write(log_text)
        r = subprocess.run(
            ["bash", "-c", function("failure_reason") + "failure_reason vllm 0"],
            capture_output=True,
            text=True,
            env={**os.environ, "LOGDIR": logs},
        )
    return r.stdout.strip()


def launched(launcher, *args):
    """The arguments a launcher gives vLLM, read from a stand-in vllm that prints them."""
    with tempfile.TemporaryDirectory() as venv:
        os.makedirs(os.path.join(venv, "bin"))
        fake = os.path.join(venv, "bin", "vllm")
        with open(fake, "w") as f:
            f.write('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IXUSR)
        r = subprocess.run(
            [os.path.join(ENGINES, launcher), *args],
            capture_output=True,
            text=True,
            env={**os.environ, "VLLM_VENV": venv, "HF_HOME": venv},
        )
    return r.stdout.splitlines()


class CellContext(unittest.TestCase):
    def test_the_window_of_the_cell(self):
        self.assertEqual(cell_context("--models", "m", "--num-ctx", "131072", "--iterations", "3"), "131072")

    def test_the_largest_of_a_list(self):
        self.assertEqual(cell_context("--num-ctx", "4096,131072,8192"), "131072")

    def test_a_cell_without_a_window(self):
        self.assertEqual(cell_context("--models", "m"), "")


class Launcher(unittest.TestCase):
    def test_the_window_given_is_the_window_held(self):
        args = launched("vllm-serve-hf.sh", "o/m", "--max-len", "131072")
        self.assertIn("--max-model-len", args)
        self.assertEqual(args[args.index("--max-model-len") + 1], "131072")

    def test_without_a_window_vllm_takes_the_one_the_model_declares(self):
        self.assertNotIn("--max-model-len", launched("vllm-serve-hf.sh", "o/m"))


class FailureReason(unittest.TestCase):
    def test_a_window_the_cache_cannot_hold_is_named(self):
        log = (
            "ValueError: To serve at least one request with the model's max seq len (131072), "
            "(20.0 GiB KV cache is needed, which is larger than the available KV cache memory (3.1 GiB)."
        )
        self.assertEqual(failure_reason(log), "the window of the cell does not fit the memory the engine was given")


if __name__ == "__main__":
    unittest.main()
