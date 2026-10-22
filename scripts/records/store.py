#!/usr/bin/env python3
"""The store: every run kept once, named by what it contains, never overwritten.

A run is one record in the lokprof schema. It is filed under the hash of its own content, so a
rerun is a new file, the same file filed twice is one, and a name can never point at a
different measurement than it did yesterday. The store is data with its own lifecycle and sits
outside the code repositories.

    store.py add <record.json ...> --store <dir>     # file records under runs/<run_id>.json
    store.py index --store <dir>                     # rebuild index.tsv from runs/
    store.py list --store <dir>                      # one line per run

`submitted/` beside `runs/` is the quarantine pool of submissions.py; nothing here reads it.
"""
import argparse, hashlib, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import classes as C
import hardware as H

COLUMNS = ("run_id", "taken_at", "host_id", "hardware_id", "hardware", "cells", "models", "source")


def run_id(record):
    """Sixteen hex digits of the SHA-256 of the record's canonical JSON."""
    canon = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def load(path):
    try:
        record = json.loads(pathlib.Path(path).read_text())
    except Exception as e:
        return None, str(e)
    if not isinstance(record, dict) or C.major(record.get("schema")) is None:
        return None, "no readable schema"
    if not record.get("results"):
        return None, "no cells"
    return record, None


def row(rid, record):
    m = record.get("machine")
    models = sorted({c.get("model") for c in record["results"] if c.get("model")})
    return {
        "run_id": rid,
        "taken_at": record.get("timestamp") or "",
        "host_id": (m or {}).get("host_id") or "",
        "hardware_id": H.hardware_id(m) or "",
        "hardware": H.label(m),
        "cells": str(len(record["results"])),
        "models": str(len(models)),
        "source": record.get("converted_from") or "",
    }


def add(paths, store):
    runs = store / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    new = known = refused = 0
    for path in paths:
        record, why = load(path)
        if record is None:
            print(f"refused {pathlib.Path(path).name}: {why}", file=sys.stderr)
            refused += 1
            continue
        target = runs / f"{run_id(record)}.json"
        if target.exists():
            known += 1
            continue
        target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        new += 1
    print(f"filed {new} new, {known} already held, {refused} refused")
    return 1 if refused and not new and not known else 0


def rows(store):
    out = []
    for path in sorted((store / "runs").glob("*.json")):
        record, _ = load(path)
        if record is not None:
            out.append(row(path.stem, record))
    out.sort(key=lambda r: (r["taken_at"], r["run_id"]))
    return out


def index(store):
    lines = ["\t".join(COLUMNS)] + ["\t".join(r[c] for c in COLUMNS) for r in rows(store)]
    (store / "index.tsv").write_text("\n".join(lines) + "\n")
    print(f"indexed {len(lines) - 1} run(s)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("records", nargs="+", type=pathlib.Path)
    for name in ("add", "index", "list"):
        p = a if name == "add" else sub.add_parser(name)
        p.add_argument("--store", required=True, type=pathlib.Path)
    args = ap.parse_args()
    if args.cmd == "add":
        return add(args.records, args.store)
    if args.cmd == "index":
        return index(args.store)
    for r in rows(args.store):
        print(f"{r['run_id']}  {r['taken_at'][:19]}  {r['cells']:>3} cells  {r['hardware']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
