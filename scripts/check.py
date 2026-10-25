#!/usr/bin/env python3
"""Check records before they join the repository.

    scripts/check.py runs/<hardware_id>/<run_id>.json [...]

Each record must be readable JSON of a known schema major, hold cells, be named by the
content hash store.py computes, sit in the folder of the hardware_id its machine block hashes
to, follow the campaign's protocol and exist once in `runs/`.
It must also be anonymous: dates without a time of day, a machine block that holds only the
listed fields, and no path, private address or mailbox in any string.
Prints one line per refused record with every reason, and exits 1 when any is refused.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "records"))
import repository as R  # noqa: E402

# The schema majors lokprof writes (`SCHEMA` in lokprof/src/provenance.rs).
KNOWN_MAJORS = ("2",)

# The protocol of `scripts/bench run`: three iterations, no warm-up (engines/fair-run.sh),
# 128 tokens, streaming on or off (matrix.toml).
CAMPAIGN = {"iterations": 3, "warmup": 0, "max_tokens": 128}


def error_cell(cell):
    """A cell the campaign writes for a model it cannot measure: a reason and no iteration."""
    return bool(cell.get("load_error")) and not cell.get("iterations")


def protocol_problems(record):
    protocol = record.get("protocol")
    if protocol is None:
        if all(error_cell(c) for c in record["results"]):
            return []
        return ["no protocol block, and not every cell is an error cell"]
    out = [f"protocol {k} is {protocol.get(k)!r}, the campaign uses {v!r}"
           for k, v in CAMPAIGN.items() if protocol.get(k) != v]
    if not isinstance(protocol.get("streaming"), bool):
        out.append(f"protocol streaming is {protocol.get('streaming')!r}, the campaign sets true or false")
    return out


def anonymity_problems(record):
    out = []
    machine = record.get("machine")
    if R.is_cpu_run(record) and isinstance(machine, dict) and (machine.get("gpus") or machine.get("nodes")):
        out.append("a CPU run names a card; the host alone was measured (scripts/add.py removes it)")
    if R.clock_fields(record):
        out.append("a date carries a time of day; keep the day only (scripts/add.py does)")
    machine = record.get("machine")
    if isinstance(machine, dict):
        foreign = R.foreign_machine_fields(machine)
        if foreign:
            out.append("machine fields outside the list: " + ", ".join(foreign)
                       + " (scripts/add.py removes them)")
    local = R.local_strings(record)
    if local:
        out.append("a string names a path, a private address or a mailbox: " + repr(local[0]))
    return out


def problems(path, record, holders):
    """Every reason to refuse `record` filed at `path`; `holders` maps run_id to its paths."""
    if not isinstance(record, dict):
        return ["not a JSON object"]
    if R.C.major(record.get("schema")) not in KNOWN_MAJORS:
        return [f"schema {record.get('schema')!r} is not loken/{' or '.join(KNOWN_MAJORS)}"]
    if not isinstance(record.get("results"), list) or not record["results"]:
        return ["no cells in results"]
    out = []
    rid = R.S.run_id(record)
    if path.stem != rid:
        out.append(f"named {path.stem}, its content hashes to run_id {rid}")
    machine = record.get("machine")
    if not machine:
        out.append("no machine block: a run must say what it ran on")
    else:
        block = {k: v for k, v in machine.items() if k != "hardware_id"}
        computed = R.H.hardware_id(block)
        stated = machine.get("hardware_id")
        if stated and stated != computed:
            out.append(f"machine states hardware_id {stated}, its block hashes to {computed}")
        if path.parent.name != computed:
            out.append(f"in folder {path.parent.name}, its machine is hardware_id {computed}")
    out += anonymity_problems(record)
    out += protocol_problems(record)
    others = [p for p in holders.get(path.stem, []) if p.resolve() != path.resolve()]
    if others:
        out.append("duplicate of " + ", ".join(str(p.relative_to(R.ROOT)) for p in others))
    return out


def holders_of(paths):
    held = {}
    for p in set(R.all_paths()) | {p.resolve() for p in paths}:
        held.setdefault(p.stem, set()).add(p.resolve())
    return {k: sorted(v) for k, v in held.items()}


def check(paths):
    """(accepted paths, [(path, reasons)])."""
    paths = [pathlib.Path(p).resolve() for p in paths]
    holders = holders_of(paths)
    accepted, refused, seen = [], [], set()
    for path in paths:
        try:
            record = json.loads(path.read_text())
        except Exception as e:
            refused.append((path, [f"not readable JSON: {e}"]))
            continue
        why = problems(path, record, holders)
        if path in seen:
            why.append("listed twice")
        seen.add(path)
        if why:
            refused.append((path, why))
        else:
            accepted.append(path)
    return accepted, refused


def show(path):
    try:
        return str(path.relative_to(R.ROOT))
    except ValueError:
        return str(path)


def main(argv):
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    accepted, refused = check(argv)
    for path, why in refused:
        print(f"REFUSED {show(path)}: " + "; ".join(why))
    print(f"{len(accepted)} record(s) accepted, {len(refused)} refused")
    return 1 if refused else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
