#!/usr/bin/env python3
"""Keep what a replayed-prompt record measured truly, and remove what the prompt cache served.

The first campaigns of the token-sized prompts replayed one prompt at every iteration of a cell.
An engine with a prefix cache then served the prompt of the second and third iterations from the
cache: their prefill, first-token time, end-to-end latency and whole-request energy measure the
cache, not the engine. Their decode is untouched, and the first iteration is whole.

So the replayed iterations lose those figures, the aggregates built on them go too, and the
protocol block says what was removed. Each record is written under its new content hash.

    transform-replayed.py <record.json> [more.json ...] --into <runs directory>
"""
import argparse, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import store as S  # noqa: E402

# Per iteration, what the cached prompt changed.
ITERATION_FIELDS = ("prompt_tok_s", "ttft_ms", "e2e_latency_ms", "wall_clock_ms")
# In an iteration's energy block, what covers the whole request rather than the decode.
ENERGY_FIELDS = ("energy_j", "gpu_energy_j", "cpu_pkg_energy_j", "dram_energy_j", "duration_s",
                 "j_per_tok", "wh_per_tok", "gco2_per_tok")
# Aggregates over the three iterations built on those figures, by name or name prefix.
STAT_PREFIXES = ("E2E latency", "TTFT", "Prompt tok/s", "Energy J/tok", "Energy Wh/tok", "Carbon gCO2/tok")
NOTE = ("one prompt was replayed at every iteration: the prefill, first-token time, end-to-end "
        "latency and whole-request energy of the second and third iterations, and the aggregates "
        "built on them, are removed; the decode figures and the first iteration are kept")


def transform(record: dict) -> dict:
    if (record.get("protocol") or {}).get("unique_prompt") is not False:
        raise ValueError("not a replayed-prompt record")
    for cell in record["results"]:
        for it in (cell.get("iterations") or [])[1:]:
            for f in ITERATION_FIELDS:
                if f in it:
                    it[f] = None
            energy = it.get("energy")
            if isinstance(energy, dict):
                for f in ENERGY_FIELDS:
                    if f in energy:
                        energy[f] = None
        stats = cell.get("stats")
        if isinstance(stats, dict):
            for k in list(stats):
                if k.startswith(STAT_PREFIXES):
                    stats[k] = None
    record["protocol"]["replayed_prompt_removed"] = NOTE
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("records", nargs="+", type=pathlib.Path)
    ap.add_argument("--into", type=pathlib.Path, required=True)
    a = ap.parse_args()
    for p in a.records:
        record = transform(json.loads(p.read_text()))
        out = a.into / p.parent.name / f"{S.run_id(record)}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2) + "\n")
        print(f"{p} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
