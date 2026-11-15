"""The ollama row of a Hugging Face GGUF meets the loken row of its cell.

The driver imports such a model into ollama as `hf.co/<repository>:<quantisation>`.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import bench_row as B  # noqa: E402

REPO = "o/m-GGUF"
ALIAS = "hf.co/o/m-GGUF:Q4_K_M"


def row(target, model, rate):
    return {"target": target, "url": "", "model": model, "num_ctx": 4096, "prompt": "100",
            "prompt_chars": 0, "stats": {"Tokens generated": {"mean": 128.0}},
            "iterations": [{"completion_tok_s": rate, "tokens_generated": 128}] * 3,
            "iteration_errors": [], "coherence_pass": True, "first_response_preview": "an answer",
            "load_error": None}


def part(target, model, rate):
    return {"schema": "loken/2", "timestamp": "2026-11-15T10:00:00+00:00", "config": {"streaming": True},
            "machine": {}, "protocol": {}, "subjects": {}, "results": [row(target, model, rate)]}


def merged(parts):
    """The record fair-run.sh merges from engine parts, with its own jq program."""
    with open(SCRIPTS / "engines" / "fair-run.sh") as f:
        text = f.read()
    program = re.search(r"^jq -s '(.*?)' --arg", text, re.S | re.M).group(1)
    with tempfile.TemporaryDirectory() as folder:
        paths = []
        for n, p in enumerate(parts):
            path = os.path.join(folder, f"{n}.json")
            with open(path, "w") as f:
                json.dump(p, f)
            paths.append(path)
        out = subprocess.run(["jq", "-s", program, "--arg", "alias", ALIAS, "--arg", "cell", REPO, *paths],
                             capture_output=True, text=True, check=True).stdout
    return json.loads(out)


class Merge(unittest.TestCase):
    def test_the_merge_names_the_ollama_row_after_the_cell(self):
        doc = merged([part("Ollama", ALIAS, 50.0), part("LOKEN", REPO, 60.0)])
        self.assertEqual({r["model"] for r in doc["results"]}, {REPO})


class Reading(unittest.TestCase):
    def test_a_record_written_with_the_alias_pairs_its_rows(self):
        doc = {"config": {"streaming": True}, "results": [row("Ollama", ALIAS, 50.0), row("LOKEN", REPO, 60.0)]}
        cells = B.load_docs([(doc, "x.json", "r1")])
        self.assertEqual(list(cells), [(REPO, 4096, "100", "stream", "GPU")])
        (_, info), = [(r, i) for r, i in B.cells_detail(cells) if i["plain"]]
        self.assertAlmostEqual(info["dec"][0], 20.0)

    def test_another_model_keeps_its_name(self):
        doc = {"config": {"streaming": True}, "results": [row("Ollama", "hf.co/o/other:Q4_K_M", 50.0),
                                                          row("LOKEN", REPO, 60.0)]}
        self.assertEqual(len(B.load_docs([(doc, "x.json", "r1")])), 2)


if __name__ == "__main__":
    unittest.main()
