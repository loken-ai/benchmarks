"""The engines a cell runs on, from the modality and the format: `plan_cell` in scripts/bench."""

import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "scripts", "bench")


def plan(model, modality, fmt):
    """The 4 fields `plan_cell` prints: engines, lokprof modality, vLLM target, error."""
    text = open(BENCH).read()
    source = re.search(r"^plan_cell\(\) \{.*?^\}\n", text, re.S | re.M).group(0)
    out = subprocess.run(
        ["bash", "-c", f'ASR_AUDIO=/nonexistent; {source}\nplan_cell "{model}" {modality} {fmt}'],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return out.split("|")


class Embedding(unittest.TestCase):
    def test_a_gguf_embedding_model_runs_on_loken_and_ollama(self):
        engines, modality, vserve, err = plan("nomic-embed-text:latest", "embedding", "gguf")
        self.assertEqual((engines, modality, vserve, err), ("ollama loken", "embedding", "", ""))

    def test_a_safetensors_embedding_model_runs_on_loken_and_vllm(self):
        engines, modality, vserve, err = plan("org/embedder", "embedding", "safetensors")
        self.assertEqual((engines, modality, err), ("loken vllm", "embedding", ""))
        self.assertEqual(vserve, "hf:org/embedder --name org/embedder")

    def test_an_embedding_model_of_unknown_format_is_an_error_cell(self):
        self.assertIn("unknown format", plan("m", "embedding", "")[3])

    def test_the_peers_follow_the_format_whatever_the_model_name(self):
        for name in ("a", "b:1", "owner/c"):
            self.assertEqual(plan(name, "embedding", "gguf")[0], "ollama loken")


if __name__ == "__main__":
    unittest.main()
