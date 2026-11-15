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

    def test_an_embedding_cell_with_its_figures_in_the_stats_is_not_failed(self):
        done = self.cell("e/embed", None)
        done["stats"] = {"Embedding latency": {"mean": 12.0}}
        empty = self.cell("f/embed", None)
        docs = B.load_docs([({"config": {"streaming": True}, "results": [done, empty]}, "x.json", "r1")])
        (key_done,) = [k for k in docs if k[0] == "e/embed"]
        (key_empty,) = [k for k in docs if k[0] == "f/embed"]
        self.assertFalse(docs[key_done]["ollama"]["failed"])
        self.assertTrue(docs[key_empty]["ollama"]["failed"])

    def test_a_media_cell_with_its_latency_in_the_stats_is_measured(self):
        kinds = ("Image latency", "Music latency", "TTS latency", "ASR latency")
        cells = []
        for n, kind in enumerate(kinds):
            c = self.cell(f"m/{n}", None)
            c["target"] = "LOKEN"
            c["stats"] = {kind: {"count": 3, "mean": 900.0, "p50": 880.0}, "Real-time factor": {"count": 3, "mean": 0.2}}
            cells.append(c)
        load_only = self.cell("m/load", None)
        load_only["target"] = "LOKEN"
        load_only["stats"] = {"Model load": {"count": 1, "mean": 5000.0}}
        docs = B.load_docs([({"config": {"streaming": True}, "results": cells + [load_only]}, "x.json", "r1")])
        by_model = {k[0]: v["loken"] for k, v in docs.items()}
        for n in range(len(kinds)):
            self.assertFalse(by_model[f"m/{n}"]["failed"])
            self.assertEqual(by_model[f"m/{n}"]["e2e"], 900.0)
        self.assertTrue(by_model["m/load"]["failed"])


if __name__ == "__main__":
    unittest.main()
