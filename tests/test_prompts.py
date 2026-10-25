"""The prompts of the protocol: each is the start of the next, plain ASCII, named by its size in tokens.

    python3 -m unittest discover tests
"""
import pathlib
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "records"))


def prompts():
    matrix = tomllib.loads((ROOT / "matrix.toml").read_text())
    return [(str(p), (ROOT / "prompts" / f"{p}.txt").read_text()) for p in matrix["axes"]["prompts"]]


class Prompts(unittest.TestCase):
    def test_each_prompt_is_the_start_of_the_next(self):
        texts = [t for _, t in prompts()]
        for shorter, longer in zip(texts, texts[1:]):
            self.assertTrue(longer.startswith(shorter))

    def test_the_prompts_are_plain_ascii_without_a_trailing_newline(self):
        for name, text in prompts():
            self.assertTrue(text.isascii(), name)
            self.assertFalse(text.endswith("\n"), name)

    def test_the_protocol_has_the_four_sizes(self):
        self.assertEqual([n for n, _ in prompts()], ["100", "1000", "10000"])


if __name__ == "__main__":
    unittest.main()
