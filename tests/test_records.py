"""How a run is kept anonymous, filed, checked and confirmed.

    python3 -m unittest discover tests
"""
import copy
import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "records"))
import architecture as A
import check as K
import hardware as H
import repository as R


def card(name="Card", **more):
    return {"index": 0, "name": name, "vram_mib": 16000, "power_cap_w": 300, **more}


def record(**machine):
    block = {"cpu": "Cpu", "threads": 8, "ram_gib": 32, "gpus": [card()], "host_id": "aaaa", **machine}
    block["hardware_id"] = H.hardware_id({k: v for k, v in block.items() if k != "hardware_id"})
    return {
        "schema": "loken/2",
        "timestamp": "2026-10-21T12:38:57.420195068+02:00",
        "machine": block,
        "protocol": {"iterations": 3, "warmup": 0, "max_tokens": 128, "streaming": True},
        "results": [{"model": "m", "prompt": "1000", "prompt_chars": 4384, "iterations": [{}], "model_fingerprint": {"modified_at": "2026-09-29T12:35:31+02:00"}}],
    }


def filed(rec):
    return pathlib.Path("runs") / rec["machine"]["hardware_id"] / f"{R.S.run_id(rec)}.json"


class Days(unittest.TestCase):
    def test_a_stamp_keeps_its_utc_day_and_loses_its_hour(self):
        self.assertEqual(R.day_of("2026-10-21T01:30:00+02:00"), "2026-10-20")
        self.assertEqual(R.day_of("2026-10-21T12:38:57.420195068+00:00"), "2026-10-21")

    def test_a_day_is_left_as_it_is(self):
        self.assertEqual(R.day_of("2026-10-21"), "2026-10-21")
        self.assertEqual(R.day_of(""), "")

    def test_every_clock_of_a_record_is_found_and_cut(self):
        rec = record()
        self.assertEqual(len(R.clock_fields(rec)), 2)
        R.anonymised(rec)
        self.assertEqual(rec["timestamp"], "2026-10-21")
        self.assertEqual(rec["results"][0]["model_fingerprint"]["modified_at"], "2026-09-29")
        self.assertEqual(R.clock_fields(rec), [])


class Machine(unittest.TestCase):
    def test_a_card_serial_and_an_unknown_field_are_dropped(self):
        rec = record(gpus=[card(uuid="GPU-1234"), card("Other", serial="x")], hostname="box")
        R.anonymised(rec)
        self.assertNotIn("hostname", rec["machine"])
        self.assertTrue(all(set(g) <= set(R.CARD_FIELDS) for g in rec["machine"]["gpus"]))
        self.assertEqual(R.foreign_machine_fields(rec["machine"]), [])

    def test_the_foreign_fields_are_named(self):
        machine = record(gpus=[card(uuid="GPU-1234")], hostname="box")["machine"]
        self.assertEqual(sorted(R.foreign_machine_fields(machine)), ["gpus[0].uuid", "hostname"])

    def test_a_path_an_address_and_a_mailbox_are_found(self):
        rec = record()
        samples = ("/".join(["", "home", "someone", "models"]),
                   "http://" + ".".join(["192", "168", "1", "4"]) + ":11434",
                   "me" + "@" + "example.org",
                   "/".join(["", "mnt", "data", "x"]))
        for text in samples:
            rec["results"][0]["note"] = text
            self.assertTrue(R.local_strings(rec), text)
        rec["results"][0]["note"] = "http://127.0.0.1:11435"
        self.assertEqual(R.local_strings(rec), [])


class Cluster(unittest.TestCase):
    NODE_A = {"cpu": "A", "threads": 8, "ram_gib": 32, "gpus": [card("X")]}
    NODE_B = {"cpu": "B", "threads": 16, "ram_gib": 64, "gpus": [card("Y"), card("Y")]}

    def test_the_same_nodes_in_another_order_are_the_same_cluster(self):
        one = H.hardware_id({"nodes": [self.NODE_A, self.NODE_B]})
        two = H.hardware_id({"nodes": [self.NODE_B, self.NODE_A]})
        self.assertEqual(one, two)

    def test_a_changed_node_is_another_cluster(self):
        other = dict(self.NODE_B, ram_gib=128)
        self.assertNotEqual(H.hardware_id({"nodes": [self.NODE_A, self.NODE_B]}),
                            H.hardware_id({"nodes": [self.NODE_A, other]}))

    def test_a_cluster_is_not_one_of_its_nodes(self):
        self.assertNotEqual(H.hardware_id({"nodes": [self.NODE_A]}), H.hardware_id(self.NODE_A))

    def test_a_cluster_record_is_filed_under_its_cluster_id(self):
        rec = R.anonymised(record(nodes=[self.NODE_A, self.NODE_B]))
        self.assertEqual(rec["machine"]["hardware_id"], H.hardware_id({"nodes": [self.NODE_A, self.NODE_B]}))
        self.assertEqual(K.problems(filed(rec), rec, {}), [])


class Checks(unittest.TestCase):
    def test_an_anonymous_record_is_accepted(self):
        rec = R.anonymised(record())
        self.assertEqual(K.problems(filed(rec), rec, {}), [])

    def test_a_record_with_a_clock_a_serial_or_a_path_is_refused(self):
        clock = record()
        self.assertTrue(any("time of day" in why for why in K.problems(filed(clock), clock, {})))
        serial = R.anonymised(record())
        serial["machine"]["gpus"][0]["uuid"] = "GPU-1"
        self.assertTrue(any("outside the list" in why for why in K.problems(filed(serial), serial, {})))
        path = R.anonymised(record())
        path["results"][0]["note"] = "/".join(["", "home", "someone", "x"])
        self.assertTrue(any("path" in why for why in K.problems(filed(path), path, {})))

    def test_a_record_without_a_machine_is_refused(self):
        rec = R.anonymised(record())
        del rec["machine"]
        path = pathlib.Path("runs") / "0000000000000000" / f"{R.S.run_id(rec)}.json"
        self.assertTrue(any("no machine block" in why for why in K.problems(path, rec, {})))

    def test_a_record_named_by_something_else_than_its_hash_is_refused(self):
        rec = R.anonymised(record())
        wrong = pathlib.Path("runs") / rec["machine"]["hardware_id"] / "0000000000000000.json"
        self.assertTrue(any("hashes to run_id" in why for why in K.problems(wrong, rec, {})))


class Energy(unittest.TestCase):
    def with_energy(self, **energy):
        rec = R.anonymised(record())
        block = {"complete": True, "missing_domains": [], "domains_counted": ["gpu", "cpu_pkg"], "energy_j": 4.0}
        block.update(energy)
        rec["results"][0]["target"] = "LOKEN"
        rec["results"][0]["iterations"] = [{"energy": block}]
        return rec

    def reasons(self, rec):
        return K.energy_problems(rec)

    def test_a_complete_block_is_accepted(self):
        self.assertEqual(self.reasons(self.with_energy()), [])

    def test_an_old_block_without_the_flag_is_refused(self):
        rec = self.with_energy()
        del rec["results"][0]["iterations"][0]["energy"]["complete"]
        self.assertTrue(any("does not say" in why for why in self.reasons(rec)))

    def test_an_incomplete_block_may_not_store_a_figure(self):
        rec = self.with_energy(complete=False, missing_domains=["cpu_pkg"], energy_j=4.0, j_per_tok=0.03)
        self.assertTrue(any("incomplete energy block that stores" in why for why in self.reasons(rec)))
        clean = self.with_energy(complete=False, missing_domains=["cpu_pkg"], energy_j=None)
        self.assertEqual(self.reasons(clean), [])

    def test_a_block_called_complete_must_count_the_processor(self):
        rec = self.with_energy(domains_counted=["gpu"])
        self.assertTrue(any("left out" in why for why in self.reasons(rec)))
        rec = self.with_energy(missing_domains=["card0"])
        self.assertTrue(any("left out" in why for why in self.reasons(rec)))


class PromptChecks(unittest.TestCase):
    def cell(self, label, chars):
        return {"target": "LOKEN", "model": "m", "prompt": label, "prompt_chars": chars}

    def test_a_cell_with_a_prompt_of_the_protocol_is_accepted(self):
        record = {"results": [self.cell("1000", 4384), self.cell("100", 451)]}
        self.assertEqual(K.prompt_problems(record), [])

    def test_a_prompt_outside_the_protocol_is_refused(self):
        record = {"results": [self.cell("short", 58), self.cell("2500", 11000)]}
        self.assertTrue(any("not one of the protocol" in why for why in K.prompt_problems(record)))

    def test_a_prompt_whose_text_is_not_the_size_it_says_is_refused(self):
        record = {"results": [self.cell("1000", 939)]}
        self.assertTrue(any("holds 939 characters, not the text" in why for why in K.prompt_problems(record)))


class CpuRuns(unittest.TestCase):
    def cpu_record(self):
        rec = record()
        rec["config"] = {"num_gpu": 0}
        return rec

    def test_a_run_that_gave_no_engine_a_card_is_a_cpu_run(self):
        self.assertTrue(R.is_cpu_run(self.cpu_record()))
        self.assertFalse(R.is_cpu_run(record()))

    def test_a_cpu_run_names_no_card_and_is_filed_under_the_host_alone(self):
        gpu, cpu = R.anonymised(record()), R.anonymised(self.cpu_record())
        self.assertEqual(cpu["machine"]["gpus"], [])
        self.assertNotIn("driver", cpu["machine"])
        self.assertNotEqual(cpu["machine"]["hardware_id"], gpu["machine"]["hardware_id"])
        self.assertEqual(K.problems(filed(cpu), cpu, {}), [])

    def test_the_same_host_has_one_cpu_hardware_whatever_its_cards(self):
        one = R.anonymised(self.cpu_record())
        other = self.cpu_record()
        other["machine"]["gpus"] = [card("Other", index=1)]
        self.assertEqual(R.anonymised(other)["machine"]["hardware_id"], one["machine"]["hardware_id"])

    def test_a_cpu_run_that_still_names_a_card_is_refused(self):
        rec = R.anonymised(self.cpu_record())
        rec["machine"]["gpus"] = [card()]
        rec["machine"]["hardware_id"] = H.hardware_id({k: v for k, v in rec["machine"].items() if k != "hardware_id"})
        self.assertTrue(any("names a card" in why for why in K.problems(filed(rec), rec, {})))


class Confirmation(unittest.TestCase):
    def test_a_second_host_confirms_a_run_and_the_same_host_does_not(self):
        one, two = R.anonymised(record()), R.anonymised(record(host_id="bbbb"))
        two["timestamp"] = "2026-10-22"
        again = R.anonymised(record())
        again["timestamp"] = "2026-10-23"
        status = R.statuses([("one", one), ("two", two), ("again", again)])
        self.assertEqual(status["one"], R.CONFIRMED)
        self.assertEqual(status["two"], R.CONFIRMED)
        alone = R.statuses([("one", one), ("again", again)])
        self.assertEqual(alone, {"one": R.SUBMITTED, "again": R.SUBMITTED})


class Architecture(unittest.TestCase):
    def test_a_kfd_target_version_reads_as_a_gfx_name(self):
        self.assertEqual(A.gfx_name(120001), "gfx1201")
        self.assertEqual(A.gfx_name(90010), "gfx90a")
        self.assertEqual(A.gfx_name(100300), "gfx1030")

    def test_the_description_holds_only_fields_a_run_may_state(self):
        node = A.describe()
        self.assertEqual([k for k in node if k not in R.NODE_FIELDS], [])
        for gpu in node["gpus"]:
            self.assertEqual([k for k in gpu if k not in R.CARD_FIELDS], [])

    def test_enriching_a_record_adds_no_forbidden_field(self):
        rec = A.enrich(R.anonymised(record(gpus=[card("Nothing here")])))
        self.assertEqual(R.foreign_machine_fields(rec["machine"]), [])
        self.assertEqual(rec["machine"]["gpus"][0]["name"], "Nothing here")
        self.assertEqual(rec["machine"]["hardware_id"], record(gpus=[card("Nothing here")])["machine"]["hardware_id"])


if __name__ == "__main__":
    unittest.main()
