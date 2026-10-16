#!/usr/bin/env python3
"""Bring replayable measurement records into the assay schema, keeping their inputs.

A record directory holds request.json (the exact body, prompt included), meta.json (model tag
and blob digest, the server's version and commit, binary sha256, config text, date) and
results.json (per run: prompt tokens, prefill and decode rates, wall time). It is one engine
measured on one prompt, repeated. This writes it as a run of the assay schema with one cell and
one iteration per run, and carries the inputs under `replay` so the run can be played again on
another binary.

The machine is the one the operator attests (see convert-archive.py): meta.json names the
cards and the driver as text, with no power cap, and a hardware id built from less than the
runner's would never match one.

    ingest-benchrec.py <record-dir ...> --into <directory> --attest-machine <reference.json>
                       [--attest-host]
"""
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hardware as H

SCHEMA = "assay/2"


def convert(directory: pathlib.Path, reference: dict, host: bool) -> dict:
    meta = json.loads((directory / "meta.json").read_text())
    request = json.loads((directory / "request.json").read_text())
    runs = json.loads((directory / "results.json").read_text())
    machine = H.attested(reference, host, directory.name)
    driver = (meta.get("cards") or [""])[0].rsplit(",", 1)[-1].strip()
    machine["driver"] = driver or None
    said = meta.get("version") or {}
    iterations = [
        {
            "completion_tok_s": r.get("decode_tok_s"),
            "prompt_tok_s": r.get("prefill_tok_s"),
            "tokens_generated": r.get("eval_tokens"),
            "prompt_tokens": r.get("prompt_tokens"),
            "wall_clock_ms": None if r.get("wall_s") is None else r["wall_s"] * 1000.0,
        }
        for r in runs
    ]
    return {
        "schema": SCHEMA,
        "converted_from": directory.name,
        "timestamp": meta.get("date"),
        "machine": machine,
        "subjects": {"loken": {"url": meta.get("server"), "says": said}},
        "protocol": {
            "iterations": len(runs),
            "warmup": 0,
            "streaming": None,
            "max_tokens": (request.get("body", {}).get("options") or {}).get("num_predict"),
            "engines_alone": None,
            "cards_by_uuid": None,
        },
        "replay": {
            "request": request,
            "binary_sha256": meta.get("binary_sha256"),
            "config": meta.get("config"),
            "model_digest": meta.get("model_digest"),
        },
        "results": [
            {
                "model": meta.get("model"),
                "target": "loken",
                "prompt": directory.name,
                "model_digest": meta.get("model_digest"),
                "iterations": iterations,
            }
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("records", nargs="+", type=pathlib.Path)
    ap.add_argument("--into", required=True, type=pathlib.Path)
    ap.add_argument("--attest-machine", required=True, type=pathlib.Path)
    ap.add_argument("--attest-host", action="store_true")
    args = ap.parse_args()
    reference = json.loads(args.attest_machine.read_text())
    args.into.mkdir(parents=True, exist_ok=True)
    done = 0
    for d in args.records:
        try:
            out = convert(d, reference, args.attest_host)
        except Exception as e:
            print(f"  skipped {d.name}: {e}", file=sys.stderr)
            continue
        (args.into / f"{d.name}.json").write_text(json.dumps(out, indent=2) + "\n")
        done += 1
    print(f"ingested {done} record(s) into {args.into}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
