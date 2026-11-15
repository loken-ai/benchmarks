"""Why a cell of the score has no delta: `blank_reason` in scripts/bench_row.py and the score line.

    python3 -m unittest discover tests
"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import bench_row as B  # noqa: E402
import scoreboard as S  # noqa: E402


def row(target, model, tokens=128, reason=None, stats=None, rate=50.0):
    its = [] if reason or stats else [{"completion_tok_s": rate, "tokens_generated": tokens}] * 3
    return {"target": target, "url": "", "model": model, "num_ctx": 4096, "prompt": "100",
            "prompt_chars": 0, "stats": stats or ({} if reason else {"Tokens generated": {"mean": float(tokens)}}),
            "iterations": its, "iteration_errors": [], "coherence_pass": None if reason else True,
            "first_response_preview": "" if reason else "an answer of some length", "load_error": reason}


CASES = {
    "loken failed": [row("LOKEN", "a", reason='Load failed: {"error":"cannot load"}'), row("Ollama", "a")],
    "not run": [row("LOKEN", "b", stats={"Image latency": {"count": 3, "mean": 900.0}}),
                row("Ollama", "b", reason="not run: no image generation endpoint in the harness")],
    "no peer row": [row("LOKEN", "c")],
    "peer failed": [row("LOKEN", "d"), row("Ollama", "d", reason='Load failed: {"error":"model not found"}'),
                    row("vLLM", "d", reason="not run: paired with safetensors weights only")],
    "tokens differ": [row("LOKEN", "e", tokens=128), row("Ollama", "e", tokens=40)],
}


def blanks():
    docs = [({"config": {"streaming": True}, "results": rows}, f"{name}.json", "r")
            for name, rows in CASES.items()]
    return {i["key"][0]: i["blank"] for _, i in B.cells_detail(B.load_docs(docs)) if i["plain"]}


class BlankReason(unittest.TestCase):
    def test_each_blank_is_named_for_what_it_is(self):
        got = blanks()
        for name, rows in CASES.items():
            self.assertEqual(got[rows[0]["model"]], name)

    def test_the_score_line_counts_each_reason(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, rows in CASES.items():
                with open(pathlib.Path(folder) / f"{rows[0]['model']}.json", "w") as f:
                    json.dump({"config": {"streaming": True}, "results": rows}, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                S.main(folder, brief=True)
        cold = out.getvalue().splitlines()[0]
        self.assertIn("blank: 1 loken failed, 1 not run, 1 no peer row, 1 peer failed, 1 tokens differ, 0 other", cold)


if __name__ == "__main__":
    unittest.main()
