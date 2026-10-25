"""The runs of this repository: where they are filed, who took them and how they are kept private.

A run lives at `runs/<hardware_id>/<run_id>.json`. Its submitter is the `host_id` of its machine,
a one-way hash: a run names no person and no machine.

A run is anonymised when it enters: the time of day is cut from its dates, and the machine block
keeps only the fields listed here. Anything else a recorder wrote about the machine is dropped.
"""
import datetime, json, pathlib, re

import classes as C
import hardware as H
import store as S

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RUNS = ROOT / "runs"

SUBMITTED, CONFIRMED = "submitted", "confirmed"

# What a machine block may hold, and what a card or a node of a cluster may hold.
MACHINE_FIELDS = ("host_id", "hardware_id", "attested", "cpu", "threads", "sockets", "cpu_flags", "ram_gib",
                  "os", "kernel", "driver", "gpus", "nodes")
NODE_FIELDS = ("cpu", "threads", "sockets", "cpu_flags", "ram_gib", "os", "kernel", "driver", "gpus")
CARD_FIELDS = ("index", "name", "vendor", "arch", "vram_mib", "power_cap_w", "pcie_gen", "pcie_width")

# A string of a record that names a place or a person.
LOCAL = re.compile(r"(/home/|/Users/|/mnt/|[A-Za-z]:\\|\b192\.168\.|\b10\.\d+\.\d+\.\d+|"
                   r"\b172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|[\w.+-]+@[\w-]+\.[\w.-]+)")


def submitter(record):
    """The host_id that took the record, or None when the record does not say."""
    return (record.get("machine") or {}).get("host_id") or None


def all_paths():
    return sorted(RUNS.glob("*/*.json"))


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def statuses(entries):
    """run_id -> status for (run_id, record) pairs.

    A record is confirmed when another record of the same hardware and the same equivalence
    class comes from a different host.
    """
    groups = {}
    for rid, rec in entries:
        key = (H.hardware_id(rec.get("machine")), C.class_of(rec))
        groups.setdefault(key, []).append((rid, submitter(rec)))
    out = {}
    for members in groups.values():
        for rid, who in members:
            ok = any(o != rid and s and who and s != who for o, s in members)
            out[rid] = CONFIRMED if ok else SUBMITTED
    return out


def day_of(stamp):
    """The UTC date (YYYY-MM-DD) of an ISO 8601 stamp, or the stamp itself when it has no time."""
    if not isinstance(stamp, str) or not re.match(r"\d{4}-\d\d-\d\d[T ]\d\d:\d\d", stamp):
        return stamp
    when = datetime.datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", stamp))
    if when.tzinfo:
        when = when.astimezone(datetime.timezone.utc)
    return when.strftime("%Y-%m-%d")


def clock_fields(record):
    """The (container, key) pairs of a record that carry a time of day."""
    out = [(record, "timestamp")]
    for cell in record.get("results") or []:
        if isinstance(cell, dict) and isinstance(cell.get("model_fingerprint"), dict):
            out.append((cell["model_fingerprint"], "modified_at"))
    return [(c, k) for c, k in out if isinstance(c.get(k), str) and day_of(c[k]) != c[k]]


def _keep(block, fields):
    return {k: block[k] for k in fields if k in block}


def kept_machine(machine):
    """The machine block reduced to the fields a run may state, cards and nodes included."""
    out = _keep(machine, MACHINE_FIELDS)
    if isinstance(out.get("gpus"), list):
        out["gpus"] = [_keep(g, CARD_FIELDS) for g in out["gpus"] if isinstance(g, dict)]
    if isinstance(out.get("nodes"), list):
        nodes = []
        for node in out["nodes"]:
            node = _keep(node, NODE_FIELDS)
            if isinstance(node.get("gpus"), list):
                node["gpus"] = [_keep(g, CARD_FIELDS) for g in node["gpus"] if isinstance(g, dict)]
            nodes.append(node)
        out["nodes"] = nodes
    return out


def foreign_machine_fields(machine):
    """The machine fields outside the list, as dotted names."""
    kept = kept_machine(machine)
    out = [k for k in machine if k not in kept]
    for i, card in enumerate(machine.get("gpus") or []):
        if isinstance(card, dict):
            out += [f"gpus[{i}].{k}" for k in card if k not in CARD_FIELDS]
    for n, node in enumerate(machine.get("nodes") or []):
        if isinstance(node, dict):
            out += [f"nodes[{n}].{k}" for k in node if k not in NODE_FIELDS]
    return out


def local_strings(record):
    """The strings of a record that name a path, a private address or a mailbox."""
    found = []

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and LOCAL.search(value):
            found.append(value[:60])

    walk(record)
    return found


def is_cpu_run(record):
    """True for a run that gave no engine a card: the host alone was measured."""
    return (record.get("config") or {}).get("num_gpu") == 0


def host_only(machine):
    """The machine block of a CPU run: the host, with no card and no card driver, and its own id."""
    machine = {k: v for k, v in machine.items() if k not in ("gpus", "nodes", "driver", "hardware_id")}
    machine["gpus"] = []
    machine["hardware_id"] = H.hardware_id({k: v for k, v in machine.items() if k != "hardware_id"})
    return machine


def anonymised(record):
    """The record with its dates cut to the day, its machine block cut to the listed fields, and no
    card named when only the host was measured."""
    for container, key in clock_fields(record):
        container[key] = day_of(container[key])
    if isinstance(record.get("machine"), dict):
        record["machine"] = kept_machine(record["machine"])
        if is_cpu_run(record):
            record["machine"] = host_only(record["machine"])
    return record
