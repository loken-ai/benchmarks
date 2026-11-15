"""A cell compared over the iterations both sides kept: `sound_iterations` and `over` in
scripts/bench_row.py.

    python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import bench_row as B  # noqa: E402


def iteration(n, rate, verdict=True, finish="length", tokens=128, jtok=1.0, with_verdict=True):
    it = {"iteration": n, "prompt_tokens": 100, "ttft_ms": 100.0, "completion_tok_s": rate,
          "tokens_generated": tokens, "e2e_latency_ms": 2000.0, "response_preview": "an answer of some length",
          "energy": {"complete": True, "domains_counted": ["gpu", "cpu_pkg"], "j_per_tok": jtok}}
    if with_verdict:
        it.update(coherence_pass=verdict, coherence_rule=None if verdict else "few_distinct_words",
                  finish_reason=finish)
    return it


def row(target, rates, verdicts=(True, True, True), with_verdict=True, finish="length", tokens=128, jtok=1.0):
    its = [iteration(n + 1, r, v, finish, tokens, jtok, with_verdict) for n, (r, v) in enumerate(zip(rates, verdicts))]
    return {"target": target, "url": "", "model": "m", "num_ctx": 4096, "prompt": "100", "prompt_chars": 0,
            "stats": {"Tokens generated": {"mean": float(tokens)},
                      "Energy J/tok [gpu+cpu_pkg]": {"count": 3, "mean": jtok, "p50": jtok}},
            "iterations": its, "iteration_errors": [], "first_response_preview": "an answer of some length",
            "coherence_pass": all(verdicts), "load_error": None}


def loken_info(*rows):
    cells = B.load_docs([({"config": {"streaming": True}, "results": list(rows)}, "x.json", "r1")])
    (info,) = [i for _, i in B.cells_detail(cells) if i["plain"]]
    return info


class SoundIterations(unittest.TestCase):
    def test_a_peer_with_a_flagged_first_iteration_is_compared_over_the_others(self):
        info = loken_info(row("LOKEN", [60.0, 66.0, 70.0]),
                          row("Ollama", [10.0, 50.0, 60.0], verdicts=(False, True, True), jtok=2.0))
        self.assertEqual(info["kept"], [1, 2])
        cold, warm = info["dec"]
        self.assertIsNone(cold)
        self.assertAlmostEqual(warm, (68.0 / 55.0 - 1) * 100)
        # The energy of each iteration is recorded: the kept ones are compared.
        self.assertAlmostEqual(info["energy"], 100.0)

    def test_an_old_record_compares_whole_rows_as_before(self):
        old = row("Ollama", [10.0, 50.0, 60.0], verdicts=(False, True, True), with_verdict=False)
        info = loken_info(row("LOKEN", [60.0, 66.0, 70.0], with_verdict=False), old)
        self.assertIsNone(info["kept"])
        self.assertEqual(info["dec"], (None, None))
        self.assertIsNone(info["energy"])

    def test_every_index_flagged_on_some_side_compares_whole_rows(self):
        info = loken_info(row("LOKEN", [60.0, 66.0, 70.0], verdicts=(True, False, True)),
                          row("Ollama", [10.0, 50.0, 60.0], verdicts=(False, True, False)))
        self.assertIsNone(info["kept"])
        self.assertEqual(info["dec"], (None, None))


if __name__ == "__main__":
    unittest.main()
