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
import json, pathlib, sys, tomllib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "records"))
import repository as R  # noqa: E402

# The schema majors lokprof writes (`SCHEMA` in lokprof/src/provenance.rs).
KNOWN_MAJORS = ("2",)

# The protocol of `scripts/bench run`: three iterations, no warm-up (engines/fair-run.sh), a prompt
# no engine has seen at each iteration (replaying one prompt measures an engine's prefix cache, not
# its prefill), 128 tokens, streaming on or off (matrix.toml).
CAMPAIGN = {"iterations": 3, "warmup": 0, "max_tokens": 128, "unique_prompt": True}


def error_cell(cell):
    """A cell the campaign writes for a model it cannot measure: a reason and no iteration."""
    return bool(cell.get("load_error")) and not cell.get("iterations")


# What a cached prompt changes in the iterations that replayed it (records/transform-replayed.py).
REPLAYED_FIELDS = ("prompt_tok_s", "ttft_ms", "e2e_latency_ms", "wall_clock_ms")


def replay_removed(record):
    """A record that replayed one prompt and kept, of its replayed iterations, only what the
    prompt cache does not touch, saying so in its protocol block."""
    if not record["protocol"].get("replayed_prompt_removed"):
        return False
    return all(it.get(f) is None for c in record["results"]
               for it in (c.get("iterations") or [])[1:] for f in REPLAYED_FIELDS)


def protocol_problems(record):
    protocol = record.get("protocol")
    if protocol is None:
        if all(error_cell(c) for c in record["results"]):
            return []
        return ["no protocol block, and not every cell is an error cell"]
    out = [f"protocol {k} is {protocol.get(k)!r}, the campaign uses {v!r}"
           for k, v in CAMPAIGN.items() if protocol.get(k) != v
           and not (k == "unique_prompt" and replay_removed(record))]
    if not isinstance(protocol.get("streaming"), bool):
        out.append(f"protocol streaming is {protocol.get('streaming')!r}, the campaign sets true or false")
    return out


def protocol_prompts():
    """The prompt sizes of the protocol, in tokens, from matrix.toml."""
    matrix = tomllib.loads((R.ROOT / "matrix.toml").read_text())
    return [str(p) for p in matrix["axes"]["prompts"]]


def prompt_problems(record):
    """A cell is measured with a prompt of the protocol, and the prompt it names has the size it
    says: the text it was given is the file of that name."""
    allowed = protocol_prompts()
    out = []
    for cell in record.get("results") or []:
        label = str(cell.get("prompt"))
        if label not in allowed:
            out.append(f"{cell.get('target')} {cell.get('model')}: prompt '{label}' is not one of the protocol's "
                       f"({', '.join(allowed)} tokens)")
        elif cell.get("prompt_chars") and cell["prompt_chars"] != len((R.ROOT / "prompts" / f"{label}.txt").read_text()):
            out.append(f"{cell.get('target')} {cell.get('model')}: prompt '{label}' holds "
                       f"{cell['prompt_chars']} characters, not the text of the protocol")
        if len(out) >= 3:
            break
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


# What every card of a machine block states: the hardware id and the pages' memory totals rest on them.
CARD_REQUIRED = ("name", "vram_mib")


def card_problems(machine):
    """Reasons to refuse a machine block whose cards were not all read: a card known by its name
    alone would be filed as another machine, with its memory missing from every total."""
    out = []
    nodes = machine.get("nodes") if isinstance(machine.get("nodes"), list) else [machine]
    for node in nodes:
        for i, card in enumerate((node.get("gpus") or []) if isinstance(node, dict) else []):
            missing = [k for k in CARD_REQUIRED if not isinstance(card, dict) or card.get(k) in (None, "")]
            if missing:
                out.append(f"card {i} states no {' and no '.join(missing)}: the run did not read the machine whole")
    return out


# The energy figures of an iteration: null unless the window was complete.
ENERGY_FIGURES = ("energy_j", "gpu_energy_j", "cpu_pkg_energy_j", "dram_energy_j", "j_per_tok",
                  "wh_per_tok", "gco2_per_tok", "gpu_decode_j", "cpu_pkg_decode_j",
                  "dram_decode_j", "decode_energy_j", "j_per_decode_tok")


def energy_problems(record):
    """Reasons to refuse the energy blocks of a record: a total that leaves a domain out must
    not be stored as if it were complete."""
    out = []
    for cell in record.get("results") or []:
        for n, it in enumerate(cell.get("iterations") or []):
            energy = it.get("energy")
            if not isinstance(energy, dict):
                continue
            where = f"{cell.get('target')} {cell.get('model')} iteration {n + 1}"
            if "complete" not in energy:
                out.append(f"{where}: an energy block that does not say whether it is complete")
            elif energy["complete"]:
                if energy.get("missing_domains") or "cpu_pkg" not in (energy.get("domains_counted") or []):
                    out.append(f"{where}: an energy block called complete that left out the processor or a card")
            else:
                stored = [k for k in ENERGY_FIGURES if energy.get(k) is not None]
                if stored:
                    out.append(f"{where}: an incomplete energy block that stores {', '.join(stored)}")
            if len(out) >= 3:
                return out
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
        out += card_problems(machine)
    out += anonymity_problems(record)
    out += energy_problems(record)
    out += prompt_problems(record)
    out += protocol_problems(record)
    others = [p for p in holders.get(path.stem, []) if p.resolve() != path.resolve()]
    if others:
        out.append("duplicate of " + ", ".join(str(p.relative_to(R.ROOT)) for p in others))
    return out


def host_of(record):
    """What a run says of the host it ran on, cards aside; `None` for a cluster, a CPU run or a
    record that names no host."""
    m = record.get("machine")
    if not isinstance(m, dict) or not m.get("host_id") or m.get("nodes") or R.is_cpu_run(record):
        return None
    return tuple(str(m.get(k)) for k in ("host_id", "cpu", "threads", "ram_gib", "driver", "kernel"))


def partial_machine_problems(records):
    """{path: reason} for the card runs of a host that list only part of the cards its other card
    runs list: a card the run could not see was missing from the machine, not absent from it."""
    by_host = {}
    for path, record in records:
        host = host_of(record)
        if host is not None:
            cards = sorted(str(g.get("name")) for g in record["machine"].get("gpus") or [] if isinstance(g, dict))
            by_host.setdefault(host, []).append((path, cards))
    out = {}
    for runs in by_host.values():
        sets = {tuple(cards) for _, cards in runs}
        for path, cards in runs:
            fuller = [s for s in sets if len(s) > len(cards) and all(s.count(c) >= cards.count(c) for c in cards)]
            if fuller:
                out[path] = ("a card of this host was not read: its other runs list "
                             + ", ".join(max(fuller, key=len)))
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
    # A run is held against every other record of its host, filed or being checked.
    every = []
    for p in sorted(set(R.all_paths()) | set(paths)):
        try:
            every.append((pathlib.Path(p).resolve(), json.loads(pathlib.Path(p).read_text())))
        except Exception:
            continue
    partial = partial_machine_problems(every)
    accepted, refused, seen = [], [], set()
    for path in paths:
        try:
            record = json.loads(path.read_text())
        except Exception as e:
            refused.append((path, [f"not readable JSON: {e}"]))
            continue
        why = problems(path, record, holders)
        if path in partial:
            why.append(partial[path])
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
