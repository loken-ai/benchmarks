"""The window a checkpoint of the Hugging Face store declares: `checkpoint_context` in scripts/bench."""

import json
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "scripts", "bench")


def checkpoint_context(store, repo):
    with open(BENCH) as f:
        text = f.read()
    source = re.search(r"^checkpoint_context\(\) \{.*?^\}\n", text, re.S | re.M).group(0)
    r = subprocess.run(
        ["bash", "-c", source + 'checkpoint_context "$1"', "bash", repo],
        capture_output=True,
        text=True,
        env={**os.environ, "HF_HOME": store},
    )
    return r.stdout


def put(store, repo, config):
    snap = os.path.join(store, "hub", "models--" + repo.replace("/", "--"), "snapshots", "0")
    os.makedirs(snap)
    with open(os.path.join(snap, "config.json"), "w") as f:
        json.dump(config, f)


class CheckpointContext(unittest.TestCase):
    def test_a_checkpoint_declares_its_window_at_the_top(self):
        with tempfile.TemporaryDirectory() as store:
            put(store, "o/m", {"max_position_embeddings": 40960})
            self.assertEqual(checkpoint_context(store, "o/m"), "40960")

    def test_the_text_model_of_a_composite_checkpoint_declares_it(self):
        with tempfile.TemporaryDirectory() as store:
            put(store, "o/m", {"max_position_embeddings": 4096, "text_config": {"max_position_embeddings": 262144}})
            self.assertEqual(checkpoint_context(store, "o/m"), "262144")

    def test_the_first_length_key_wins(self):
        with tempfile.TemporaryDirectory() as store:
            put(store, "o/m", {"n_positions": 1024, "seq_length": 8192})
            self.assertEqual(checkpoint_context(store, "o/m"), "8192")

    def test_a_speech_tower_declares_the_window_of_the_text_model_it_names(self):
        with tempfile.TemporaryDirectory() as store:
            put(store, "o/tower", {"audio_config": {}, "text_model_id": "o/text"})
            put(store, "o/text", {"max_position_embeddings": 131072})
            self.assertEqual(checkpoint_context(store, "o/tower"), "131072")

    def test_the_text_model_is_found_under_another_owner(self):
        with tempfile.TemporaryDirectory() as store:
            put(store, "o/tower", {"audio_config": {"d": 1}, "text_model_id": "first/Text-1B"})
            put(store, "second/text-1b", {"max_position_embeddings": 131072})
            self.assertEqual(checkpoint_context(store, "o/tower"), "131072")

    def test_a_store_that_names_the_hub_itself(self):
        with tempfile.TemporaryDirectory() as store:
            put(store, "o/m", {"max_position_embeddings": 32768})
            self.assertEqual(checkpoint_context(os.path.join(store, "hub"), "o/m"), "32768")

    def test_no_configuration_declares_nothing(self):
        with tempfile.TemporaryDirectory() as store:
            put(store, "o/m", {"hidden_size": 8})
            self.assertEqual(checkpoint_context(store, "o/m"), "")
            self.assertEqual(checkpoint_context(store, "o/absent"), "")


if __name__ == "__main__":
    unittest.main()
