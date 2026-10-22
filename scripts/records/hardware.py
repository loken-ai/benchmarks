#!/usr/bin/env python3
"""The identity of a machine and of a hardware configuration, as a record states it.

`hardware_id` hashes what a result depends on and a swap changes: the cards (model, memory,
power cap), the processor, its threads and the memory. Card serials, driver and OS are left
out, so two machines built alike share it and one machine that changes a card does not.
`host_id` is one machine across swaps; only the runner can compute it, from the OS machine id.

The algorithm is the one in src/provenance.rs, and the vector in that file's tests is the one
`self_check` verifies here. A record written before the runner computed it gets the same id
from the fields it already holds.

    hardware.py [record.json ...]       # print each record's ids, check the shared vector
"""
import hashlib, json, pathlib, sys


def short_hash(*parts):
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode())
        h.update(b"\0")
    return h.digest()[:8].hex()


def _s(value):
    return "?" if value is None else str(value)


def hardware_id(machine):
    """The id of a `machine` block, or None for a record that never described one."""
    if not machine:
        return None
    if machine.get("hardware_id"):
        return machine["hardware_id"]
    cards = sorted(f"{_s(g.get('name'))}/{_s(g.get('vram_mib'))}/{_s(g.get('power_cap_w'))}"
                   for g in machine.get("gpus", []))
    return short_hash("loken/hardware", ",".join(cards), _s(machine.get("cpu")),
                      _s(machine.get("threads")), _s(machine.get("ram_gib")))


ATTEST_FIELDS = ("cpu", "threads", "ram_gib", "gpus")


def attested(reference, host, source):
    """A machine block an operator vouches for, built from a reference record's cards,
    processor and memory. Driver, kernel and OS stay absent: the reference's are not the
    archive's."""
    ref = reference["machine"]
    m = {k: ref[k] for k in ATTEST_FIELDS if k in ref}
    m["gpus"] = [{k: v for k, v in g.items() if k != "uuid"} for g in m.get("gpus", [])]
    m["hardware_id"] = hardware_id(m)
    if host:
        m["host_id"] = host_id_here()
    m["attested"] = f"by the operator, from {source}; driver, kernel and OS unknown"
    return m


def host_id_here():
    """This machine's host_id, by the runner's rule (src/provenance.rs)."""
    return short_hash("loken/host", pathlib.Path("/etc/machine-id").read_text().splitlines()[0].strip())


def label(machine):
    """A name a person can read: the cards, then the processor."""
    if not machine:
        return "unknown hardware"
    counts = {}
    for g in machine.get("gpus", []):
        counts[g.get("name") or "?"] = counts.get(g.get("name") or "?", 0) + 1
    cards = " + ".join(f"{n}x {name}" if n > 1 else name for name, n in sorted(counts.items()))
    return f"{cards or 'no card'} on {machine.get('cpu') or '?'}"


def self_check():
    card = lambda cap: {"name": "Card", "vram_mib": 16000, "power_cap_w": cap}
    got = hardware_id({"cpu": "Cpu", "threads": 8, "ram_gib": 32, "gpus": [card(300), card(180)]})
    assert got == "9e3586b770949eea", got


def main():
    self_check()
    for path in sys.argv[1:]:
        m = json.loads(pathlib.Path(path).read_text()).get("machine")
        print(f"{path}: {hardware_id(m)}  {label(m)}")


if __name__ == "__main__":
    main()
