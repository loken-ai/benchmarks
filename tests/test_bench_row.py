"""The words and reasons of a cell that has no rate.

    python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import bench_row as B


class NoRate(unittest.TestCase):
    def test_a_pair_the_harness_did_not_run_is_not_run(self):
        self.assertEqual(B.mark_of("not run: no image generation endpoint in the harness"), "not run")

    def test_an_engine_that_could_not_take_the_model_is_unsupported(self):
        self.assertEqual(B.mark_of('Load failed: {"error":"model not found"}'), "unsupported")

    def test_the_reason_of_an_engine_error_is_unwrapped(self):
        reason = 'Load failed: {"error":"model \'x\' not found"}'
        self.assertEqual(B.short_reason(reason), "model 'x' not found")

    def test_the_reason_of_a_pair_not_run_drops_its_prefix_and_is_short(self):
        self.assertEqual(B.short_reason("not run: paired with GGUF weights only"), "paired with GGUF weights only")
        self.assertLessEqual(len(B.short_reason("not run: " + "x " * 200)), 90)


class Rendering(unittest.TestCase):
    def cell(self, model, reason):
        return {"target": "Ollama", "url": "", "model": model, "num_ctx": 4096, "prompt": "100",
                "prompt_chars": 0, "stats": {}, "iterations": [], "iteration_errors": [],
                "coherence_pass": None, "first_response_preview": "", "load_error": reason}

    def test_a_cell_with_no_rate_says_why_in_the_table(self):
        doc = {"config": {"streaming": True}, "results": [
            self.cell("a/image", "not run: no image generation endpoint in the harness"),
            self.cell("b/gguf", 'Load failed: {"error":"model \'b/gguf\' not found"}')]}
        rows = B.cells(B.load_docs([(doc, "x.json", "r1")]))
        said = {r[0]: [c.strip() for c in r if "run" in c or "unsupported" in c] for r in rows}
        self.assertEqual(said["a/image"], ["not run: no image generation endpoint in the harness"])
        self.assertEqual(said["b/gguf"], ["unsupported: model 'b/gguf' not found"])


if __name__ == "__main__":
    unittest.main()
