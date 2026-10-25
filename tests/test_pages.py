"""The look of the pages: what the result tables, the cards and the shell say.

    python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "records"))
import pages as P


class Shell(unittest.TestCase):
    def test_a_page_carries_the_brand_and_marks_its_own_link(self):
        html = P.page("T", "<p>x</p>", active="charts.html")
        self.assertIn(P.BRAND + "/icon.svg", html)
        self.assertIn('href="charts.html" aria-current="page"', html)
        self.assertNotIn('href="search.html" aria-current', html)

    def test_a_page_in_a_folder_reaches_the_assets_above_it(self):
        html = P.page("T", "", depth=1)
        self.assertIn('href="../style.css"', html)
        self.assertIn('href="../index.html"', html)

    def test_the_title_is_escaped(self):
        self.assertIn("&lt;b&gt;", P.page("<b>", ""))


class Tables(unittest.TestCase):
    HEAD = ["Model", "Ctx", "Prompt", "Mode", "Device", "Engine", "Prefill tok/s", "TTFT ms", "Decode tok/s",
            "Tokens", "E2E ms", "J/req", "J/token", "Δ prefill", "Δ TTFT", "Δ decode", "Δ energy",
            "Date (UTC)", "Run", "Status"]

    def row(self, engine="**loken**", decode="**120.0** / 118.0", delta="+10.0% / -5.0%"):
        return ["m1", "4096", "short", "stream", "GPU", engine, "900 / 950", "20 / 15", decode, "128", "1000", "64",
                "0.5", "", "", delta, "", "2026-10-20", "abcd1234"]

    def test_a_delta_is_green_when_positive_and_red_when_negative(self):
        html = P.result_table(self.HEAD, [self.row()], ["submitted"])
        self.assertIn('<span class="pos">+10.0%</span>', html)
        self.assertIn('<span class="neg">-5.0%</span>', html)

    def test_a_rate_shows_cold_muted_and_warm_plain(self):
        html = P.result_table(self.HEAD, [self.row(decode="100.0 / 110.0")], ["submitted"])
        self.assertIn('<span class="cold">100.0</span> / 110.0', html)

    def test_the_engine_cell_names_its_family_and_models_alternate(self):
        rows = [self.row(), self.row("Ollama 0.35.1"), self.row()]
        rows[2][0] = "m2"
        html = P.result_table(self.HEAD, rows, ["submitted"] * 3)
        self.assertIn('class="eng loken"', html)
        self.assertIn('class="eng ollama"', html)
        self.assertEqual(html.count("<tr class=alt>"), 2)

    def test_the_status_is_a_badge(self):
        html = P.result_table(self.HEAD, [self.row()], ["confirmed"])
        self.assertIn('<span class="badge confirmed">confirmed</span>', html)

    def test_a_cell_is_escaped(self):
        row = self.row()
        row[0] = "<img src=x>"
        self.assertNotIn("<img", P.result_table(self.HEAD, [row], ["submitted"]))


class Cards(unittest.TestCase):
    def info(self, **over):
        base = {"hid": "abc", "title": "RTX 5070 Ti", "cpu": "Cpu", "backends": ["cuda"], "vram": "16 GB",
                "archs": ["sm_120"], "cpu_only": False, "runs": 3, "rows": 9, "confirmed": 1, "hosts": 2, "wins": 6, "losses": 2,
                "span": "2026-10-01 to 2026-10-02"}
        base.update(over)
        return base

    def test_a_card_links_its_page_and_shows_the_win_ratio(self):
        html = P.hardware_card(self.info())
        self.assertIn('href="hw/abc.html"', html)
        self.assertIn("6 of 8 compared cells", html)
        self.assertIn("width:75.0%", html)

    def test_a_card_without_a_comparison_shows_no_bar(self):
        self.assertNotIn('class="win"', P.hardware_card(self.info(wins=0, losses=0)))

    def test_an_unrecorded_backend_is_said_plainly(self):
        self.assertIn("backend not recorded", P.hardware_card(self.info(backends=["unstated"])))

    def test_a_hardware_without_a_card_is_named_by_its_processor(self):
        machine = {"cpu": "Some Cpu @ 3 GHz", "gpus": []}
        self.assertEqual(P.cards_title(machine), "Some Cpu @ 3 GHz")
        html = P.hardware_card(self.info(title="Some Cpu @ 3 GHz", cpu_only=True, vram="", archs=[]))
        self.assertIn("CPU only", html)

    def test_the_title_counts_identical_cards(self):
        machine = {"gpus": [{"name": "NVIDIA GeForce RTX 5070 Ti"}, {"name": "NVIDIA GeForce RTX 5070 Ti"}]}
        self.assertEqual(P.cards_title(machine), "2 x RTX 5070 Ti")
        self.assertEqual(P.cards_title({"gpus": []}), "CPU only")


class Specs(unittest.TestCase):
    def test_each_node_of_a_cluster_has_its_own_blocks(self):
        node = {"cpu": "C", "threads": 8, "gpus": [{"name": "X", "arch": "sm_89", "vram_mib": 8192}]}
        html = P.specs({"nodes": [node, dict(node, cpu="D")]}, [])
        self.assertIn("Node 1: Cards", html)
        self.assertIn("Node 2: Host", html)
        self.assertIn("sm_89, 8 GB", html)


if __name__ == "__main__":
    unittest.main()
