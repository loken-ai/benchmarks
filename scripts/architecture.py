#!/usr/bin/env python3
"""Describe the architecture a campaign ran on, and add the description to its records.

    scripts/architecture.py describe                      # this machine, as JSON
    scripts/architecture.py enrich record.json [...]      # add it to each record's machine block
    scripts/architecture.py enrich record.json --node user@host [--node ...]

A machine block says the processor, its threads, the memory and the cards. This adds what the
speed of a run also depends on: the sockets, the instruction sets the host kernels use, and for
each card its maker, its architecture and the link it sits on. With `--node`, the record is that
of a cluster: the block lists every node, this machine first, each described by running this
same file on it over ssh, and the hardware id becomes the one of the sorted nodes.

Everything is read from /proc, /sys and the vendors' tools when present, never typed. A fact that
cannot be read is left out, not guessed. Python 3 and the standard library only.
"""
import json, pathlib, re, subprocess, sys

# The instruction sets a host kernel picks a path by.
CPU_FLAGS = ("avx2", "fma", "bmi2", "f16c", "avx512f", "avx512bw", "avx512vl", "avx512_vnni",
             "avx512_bf16", "amx_tile", "amx_int8", "amx_bf16")
VENDORS = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}
# PCIe transfer rate in GT/s -> generation.
PCIE_GEN = {"2.5": 1, "5.0": 2, "8.0": 3, "16.0": 4, "32.0": 5, "64.0": 6}


def read(path):
    try:
        return pathlib.Path(path).read_text().strip()
    except OSError:
        return None


def run(*cmd):
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def cpu():
    text = read("/proc/cpuinfo") or ""
    out = {}
    names = re.findall(r"^model name\s*:\s*(.+)$", text, re.M)
    if names:
        out["cpu"] = names[0].strip()
    threads = len(re.findall(r"^processor\s*:", text, re.M))
    if threads:
        out["threads"] = threads
    packages = set(re.findall(r"^physical id\s*:\s*(\d+)", text, re.M))
    out["sockets"] = len(packages) or 1
    flags = re.search(r"^flags\s*:\s*(.+)$", text, re.M)
    if flags:
        have = set(flags.group(1).split())
        out["cpu_flags"] = [f for f in CPU_FLAGS if f in have]
    return out


def memory():
    for line in (read("/proc/meminfo") or "").splitlines():
        if line.startswith("MemTotal:"):
            return {"ram_gib": int(line.split()[1]) // 1024 // 1024}
    return {}


def system():
    out = {}
    osr = read("/etc/os-release") or ""
    m = re.search(r'^PRETTY_NAME="?([^"\n]+)"?', osr, re.M)
    if m:
        out["os"] = m.group(1)
    kernel = read("/proc/sys/kernel/osrelease")
    if kernel:
        out["kernel"] = kernel
    return out


def link(device):
    """(generation, width) of the PCIe link a card sits on.

    The generation is the one the card supports, because the link trains down to the slowest rate
    when idle; the width is the one negotiated with the slot."""
    speed = (read(f"{device}/max_link_speed") or "").split()
    width = read(f"{device}/current_link_width")
    gen = PCIE_GEN.get(speed[0]) if speed else None
    return gen, int(width) if width and width.isdigit() else None


def gfx_name(version):
    """The gfx name of a KFD `gfx_target_version`: 120001 is gfx1201, 90010 is gfx90a."""
    major, minor, step = version // 10000, version // 100 % 100, version % 100
    return f"gfx{major}{minor:x}{step:x}"


def amd_arch():
    """PCI address -> gfx name, from the KFD topology."""
    out = {}
    for node in sorted(pathlib.Path("/sys/class/kfd/kfd/topology/nodes").glob("*")):
        props = dict(line.split(None, 1) for line in (read(node / "properties") or "").splitlines()
                     if " " in line)
        version = int(props.get("gfx_target_version", 0))
        location = int(props.get("location_id", 0))
        domain = int(props.get("domain", 0))
        if version:
            out[f"{domain:04x}:{location >> 8:02x}:{location >> 3 & 31:02x}.{location & 7}"] = gfx_name(version)
    return out


def amd_names():
    """(marketing name, gfx name) of each AMD agent rocminfo lists, in its order."""
    text = run("rocminfo") or ""
    out = []
    for agent in text.split("Agent ")[1:]:
        gfx = re.search(r"^\s*Name:\s+(gfx\w+)", agent, re.M)
        name = re.search(r"^\s*Marketing Name:\s+(.+)$", agent, re.M)
        if gfx and name:
            out.append((name.group(1).strip(), gfx.group(1)))
    return out


def amd_details(device, arch, names):
    """name, vram_mib and power_cap_w of an AMD card, as far as the system states them."""
    out = {}
    for i, (name, gfx) in enumerate(names):
        if gfx == arch:
            out["name"] = name
            names.pop(i)
            break
    vram = read(device / "mem_info_vram_total")
    if vram and vram.isdigit():
        out["vram_mib"] = int(vram) // 1024 // 1024
    cap = next(iter(sorted(device.glob("hwmon/hwmon*/power1_cap"))), None)
    watts = read(cap) if cap else None
    if watts and watts.isdigit():
        out["power_cap_w"] = int(watts) // 1_000_000
    return out


def cards():
    """The graphics devices of this machine, each with what a run depends on."""
    arch = amd_arch()
    nvidia = {}
    table = run("nvidia-smi", "--query-gpu=index,name,memory.total,power.limit,compute_cap,pci.bus_id",
                "--format=csv,noheader,nounits")
    for line in (table or "").splitlines():
        index, name, vram, cap, ccap, bus = [x.strip() for x in line.split(",")]
        fields = {"index": int(index), "name": name}
        if vram.isdigit():
            fields["vram_mib"] = int(vram)
        if re.fullmatch(r"\d+(\.\d+)?", cap):
            fields["power_cap_w"] = int(float(cap))
        if re.fullmatch(r"\d+\.\d+", ccap):
            fields["arch"] = "sm_" + ccap.replace(".", "")
        nvidia[bus.lower()[-12:]] = fields
    found, names = [], amd_names()
    for device in sorted(pathlib.Path("/sys/bus/pci/devices").glob("*")):
        if not (read(device / "class") or "").startswith(("0x03", "0x12")):
            continue
        vendor = VENDORS.get(read(device / "vendor") or "")
        if vendor is None:
            continue
        gen, width = link(device)
        card = {"vendor": vendor}
        if vendor == "amd" and device.name in arch:
            card["arch"] = arch[device.name]
            card.update(amd_details(device, card["arch"], names))
        if vendor == "nvidia" and device.name in nvidia:
            card.update(nvidia[device.name])
        if gen:
            card["pcie_gen"] = gen
        if width:
            card["pcie_width"] = width
        found.append(card)
    found.sort(key=lambda c: (c.get("index", 1 << 16), c["vendor"]))
    return found


def driver():
    out = run("nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader")
    return {"driver": out.splitlines()[0].strip()} if out else {}


def describe():
    """This machine as a node of a block."""
    node = {**cpu(), **memory(), **system(), **driver()}
    node["gpus"] = [c for c in cards() if c["vendor"] == "nvidia" or "name" in c or "arch" in c]
    return node


def remote(target):
    """A node, described by running this file on it over ssh."""
    done = subprocess.run(["ssh", target, "python3", "-", "describe"], input=pathlib.Path(__file__).read_text(),
                          capture_output=True, text=True, timeout=120)
    if done.returncode:
        sys.exit(f"architecture: could not describe {target}: {done.stderr.strip()[:200]}")
    return json.loads(done.stdout)


def enrich(record, nodes=()):
    """Add the architecture to the machine block of `record`; `nodes` are ssh targets."""
    machine = record.get("machine")
    if not isinstance(machine, dict):
        return record
    here = describe()
    for key in ("sockets", "cpu_flags"):
        if key in here:
            machine[key] = here[key]
    spare = list(here["gpus"])
    for card in machine.get("gpus") or []:
        for i, found in enumerate(spare):
            if found.get("name") == card.get("name") and (found.get("index") in (None, card.get("index"))):
                card.update({k: v for k, v in found.items() if k in ("vendor", "arch", "pcie_gen", "pcie_width")})
                for key in ("vram_mib", "power_cap_w"):
                    if card.get(key) is None and found.get(key) is not None:
                        card[key] = found[key]
                spare.pop(i)
                break
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "records"))
    import hardware as H
    if nodes:
        machine["nodes"] = [here] + [remote(t) for t in nodes]
    # The id follows the card details the system added, so a card the server named without its
    # memory is the same configuration in every record of the campaign.
    machine.pop("hardware_id", None)
    machine["hardware_id"] = H.hardware_id(machine)
    return record


def main(argv):
    if argv[:1] == ["describe"]:
        print(json.dumps(describe(), sort_keys=True, indent=2))
        return 0
    if argv[:1] == ["enrich"]:
        nodes, paths, rest = [], [], argv[1:]
        while rest:
            item = rest.pop(0)
            if item == "--node" and rest:
                nodes.append(rest.pop(0))
            else:
                paths.append(item)
        for path in map(pathlib.Path, paths):
            record = enrich(json.loads(path.read_text()), nodes)
            path.write_text(json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        return 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
