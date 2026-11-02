"""The file name scripts/bench gives ollama for a model file: `ollama_from`."""

import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "scripts", "bench")


def ollama_from(path):
    text = open(BENCH).read()
    source = re.search(r"^ollama_from\(\) \{.*?^\}\n", text, re.S | re.M).group(0)
    r = subprocess.run(
        ["bash", "-c", source + 'ollama_from "$1"', "bash", path], capture_output=True, text=True
    )
    return r.stdout


def ollama_manifest(store, rel):
    text = open(BENCH).read()
    source = re.search(r"^ollama_manifest\(\) \{.*?^\}\n", text, re.S | re.M).group(0)
    r = subprocess.run(
        ["bash", "-c", source + 'ollama_manifest "$1" "$2"', "bash", store, rel],
        capture_output=True,
        text=True,
    )
    return r.stdout


class OllamaManifest(unittest.TestCase):
    def put(self, store, folder, rel):
        path = os.path.join(store, folder, rel)
        os.makedirs(os.path.dirname(path))
        open(path, "w").write("{}")
        return path

    def test_manifest_in_the_older_folder(self):
        with tempfile.TemporaryDirectory() as store:
            path = self.put(store, "manifests", "hf.co/o/m/Q4")
            self.assertEqual(ollama_manifest(store, "hf.co/o/m/Q4"), path)

    def test_manifest_in_the_newer_folder(self):
        with tempfile.TemporaryDirectory() as store:
            path = self.put(store, "manifests-v2", "hf.co/o/m/Q4")
            self.assertEqual(ollama_manifest(store, "hf.co/o/m/Q4"), path)

    def test_no_manifest(self):
        with tempfile.TemporaryDirectory() as store:
            self.assertEqual(ollama_manifest(store, "hf.co/o/m/Q4"), "")


class OllamaFrom(unittest.TestCase):
    def test_first_shard_becomes_the_wildcard_of_every_shard(self):
        self.assertEqual(
            ollama_from("/m/IQ1_M/Model-IQ1_M-00001-of-00002.gguf"), "/m/IQ1_M/Model-IQ1_M-*.gguf"
        )

    def test_single_file_is_named_as_it_is(self):
        self.assertEqual(ollama_from("/m/Model-Q4_K_M.gguf"), "/m/Model-Q4_K_M.gguf")

    def test_companion_file_is_not_taken_for_a_shard(self):
        self.assertEqual(ollama_from("/m/Model-IQ1_M.mtp.gguf"), "/m/Model-IQ1_M.mtp.gguf")


if __name__ == "__main__":
    unittest.main()
