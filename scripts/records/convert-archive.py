#!/usr/bin/env python3
"""Bring an archived report up to the current schema, marking what it cannot know.

An old report says what was measured and almost nothing about what produced it: no driver, no
kernel, no card identity, no engine commit. Those facts cannot be recovered afterwards, and
inventing them would be worse than leaving them out - a reader comparing an old row with a new
one has to be able to see that the old one cannot say where it came from.

So every field this cannot fill is written as null, never as a default, and the record carries
`converted_from` naming the file it came out of. A null here means "nobody recorded it"; the
absence of the whole block would have meant "this tool is old", which is a different fact.

    convert-archive.py <report.json> [more.json ...] --into <directory>
        [--attest-machine <reference.json> [--attest-host]] [--archive-label NAME]

`--archive-label` marks every record as taken from a named archive (a folder of superseded or
differently-protocoled runs). The store keeps them; the pages do not table them.

A person who knows which machine took an archive can say so. `--attest-machine` copies the
cards, processor and memory of a reference record, leaves driver, kernel and OS null (the
reference's are not the archive's), and marks the block `attested` so nobody reads it as
measured. `--attest-host` adds this machine's host_id. The attestation fills only what is
absent: a record that already carries a machine keeps it.
"""
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hardware as H

SCHEMA = "loken/2"


def convert(old: dict, source: pathlib.Path) -> dict:
    cfg = old.get("config", {}) or {}
    return {
        "schema": SCHEMA,
        "converted_from": source.name,
        "timestamp": old.get("timestamp"),
        # Nothing in an old report identifies the machine. Said, rather than guessed.
        "machine": None,
        # The engine build is the same gap: `engine_build` was a timestamp of a binary's
        # mtime, stamped after the fact, and it names no commit. Kept verbatim under its own
        # name rather than promoted into a field that implies more than it holds.
        "subjects": None,
        "legacy_engine_build": old.get("engine_build"),
        # What an old report said about the engines it measured, kept under the names it used.
        "ollama_version": old.get("ollama_version"),
        "vllm_version": old.get("vllm_version"),
        "protocol": {
            "iterations": cfg.get("iterations"),
            "warmup": cfg.get("warmup"),
            "streaming": cfg.get("streaming"),
            "max_tokens": cfg.get("max_tokens"),
            "unique_prompt": cfg.get("unique_prompt"),
            "prefix_reuse_offered": cfg.get("session_id") is not None,
            "engines_alone": None,
            "cards_by_uuid": None,
            "thermal_gate_c": None,
        },
        "config": cfg,
        "idle_energy_baseline": old.get("idle_energy_baseline"),
        "results": old.get("results", []),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+", type=pathlib.Path)
    ap.add_argument("--into", required=True, type=pathlib.Path)
    ap.add_argument("--attest-machine", type=pathlib.Path)
    ap.add_argument("--attest-host", action="store_true")
    ap.add_argument("--archive-label")
    args = ap.parse_args()
    reference = json.loads(args.attest_machine.read_text()) if args.attest_machine else None
    args.into.mkdir(parents=True, exist_ok=True)
    done = 0
    for path in args.reports:
        try:
            old = json.loads(path.read_text())
        except Exception as e:  # a truncated archive is skipped, and said
            print(f"  skipped {path.name}: {e}", file=sys.stderr)
            continue
        if old.get("schema") in (SCHEMA, "assay/2"):
            wants_host = args.attest_host and not (old.get("machine") or {}).get("host_id")
            if reference is None or (old.get("machine") and not wants_host):
                print(f"  already current: {path.name}")
                continue
            new = old
            if old.get("machine"):
                new["machine"]["host_id"] = H.host_id_here()
        else:
            new = convert(old, path)
        if reference is not None and not new.get("machine"):
            new["machine"] = H.attested(reference, args.attest_host, args.attest_machine.name)
        if args.archive_label:
            new["archive"] = args.archive_label
        out = args.into / path.name
        out.write_text(json.dumps(new, indent=2) + "\n")
        done += 1
    print(f"converted {done} report(s) into {args.into}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
