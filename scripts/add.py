#!/usr/bin/env python3
"""File the records of a campaign under `runs/<hardware_id>/`, anonymised, keeping the accepted ones.

    scripts/add.py results/*.json

Each record loses the time of day of its dates and every machine field outside the list in
records/repository.py, then is filed under the hash of what is kept. A record already held is
skipped. A refused record is not filed, and its reasons are printed.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "records"))
import check as K  # noqa: E402
import repository as R  # noqa: E402


def target(record):
    machine = {k: v for k, v in record["machine"].items() if k != "hardware_id"}
    return R.RUNS / R.H.hardware_id(machine) / f"{R.S.run_id(record)}.json"


def main(argv):
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    held = {p.stem for p in R.all_paths()}
    holders = K.holders_of([])
    new = known = 0
    refused = []
    incoming = []
    for src in map(pathlib.Path, argv):
        try:
            record = R.anonymised(R.read(src))
        except Exception as e:
            refused.append((src, [f"not readable JSON: {e}"]))
            continue
        if not isinstance(record.get("machine"), dict):
            refused.append((src, ["no machine block: a run must say what it ran on"]))
            continue
        incoming.append((src, record, target(record)))
    # Each run is held against every record of its host, filed or arriving with it.
    filed = []
    for p in R.all_paths():
        try:
            filed.append((p.resolve(), json.loads(p.read_text())))
        except Exception:
            continue
    partial = K.partial_machine_problems(filed + [(dest, record) for _, record, dest in incoming])
    for src, record, dest in incoming:
        if dest.stem in held:
            known += 1
            continue
        why = K.problems(dest, record, holders)
        if dest in partial:
            why.append(partial[dest])
        if why:
            refused.append((src, why))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        held.add(dest.stem)
        new += 1
    for src, why in refused:
        print(f"REFUSED {src.name}: " + "; ".join(why))
    print(f"filed {new}, {known} already held, {len(refused)} refused")
    return 1 if refused else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
