#!/usr/bin/env python3
"""Write the static site into `site/` from the records under `runs/`.

    scripts/site.py

The site is an index of hardware configurations, one page per hardware_id with the table the
loken report writes (bench_row.py), one table per backend loken answered on, each row with the
status of the record behind it, and a search page over `index.json`. Records in
records check.py refuses appear nowhere. Dates are UTC.
"""
import html, json, os, pathlib, re, sys, time

os.environ["TZ"] = "UTC"
time.tzset()

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "records"))
import check as K  # noqa: E402
import repository as R  # noqa: E402
import bench_row as B  # noqa: E402

# The report derives an unstated loken version from loken's git history, which this
# repository does not hold: such a row is labelled without a number.
B._dev_version_at = lambda epoch: None

OUT = R.ROOT / "site"
STATUS_COL = "Status"

CSS = """
:root { color-scheme: light dark; --bg: #ffffff; --fg: #1d1d1f; --muted: #5f6368; --line: #d9dce1; --head: #f3f4f6;
  --link: #0b57d0; --ok: #137333; --wait: #8a5a00; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #16181c; --fg: #e8eaed; --muted: #9aa0a6; --line: #3c4043; --head: #23262b;
    --link: #8ab4f8; --ok: #81c995; --wait: #fdd663; } }
body { background: var(--bg); color: var(--fg); margin: 0 auto; max-width: 1400px;
  padding: 16px; font: 15px/1.5 system-ui, sans-serif; }
a { color: var(--link); }
nav { margin-bottom: 16px; }
nav a { margin-right: 16px; }
p.note { color: var(--muted); }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; font-size: 13px; margin: 8px 0 24px; }
th, td { border: 1px solid var(--line); padding: 3px 8px; text-align: left; white-space: nowrap; }
th { background: var(--head); position: sticky; top: 0; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.confirmed { color: var(--ok); }
.submitted { color: var(--wait); }
form { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; align-items: end; }
form.controls label { display: flex; flex-direction: column; font-size: 13px; color: var(--muted); }
fieldset { border: 1px solid var(--line); padding: 2px 10px 6px; }
fieldset label { margin-right: 12px; }
button { background: var(--head); color: var(--fg); border: 1px solid var(--line); padding: 4px 10px; font: inherit; cursor: pointer; }
ul.legend { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 20px; font-size: 13px; }
svg text { fill: var(--fg); }
input, select { background: var(--bg); color: var(--fg); border: 1px solid var(--line);
  padding: 4px 6px; font: inherit; }
"""

NUMERIC = {"Ctx", "Prefill tok/s", "TTFT ms", "Decode tok/s", "Tokens", "E2E ms", "J/req", "J/token",
           "\u0394 prefill", "\u0394 TTFT", "\u0394 decode", "\u0394 energy"}


def backend_note(backend):
    """The line a page carries when no reference engine runs its backend."""
    if backend == "opencl":
        return ["No reference engine runs a language model through OpenCL on a GPU (ollama and "
                "vLLM do not), so this page holds loken alone."]
    return []


def esc(value):
    return html.escape(str(value))


def cell_html(value):
    """A table cell of bench_row: `**x**` marks a loken figure."""
    text = esc(value.strip())
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def plain(value):
    return value.replace("**", "").strip()


def figures(cell):
    """The numbers of a table cell: `120.5 / 118.2` is [120.5, 118.2]; a dash is None."""
    out = []
    for part in plain(cell).split("/"):
        try:
            out.append(float(part.replace(",", "").split()[0]))
        except (ValueError, IndexError):
            out.append(None)
    return out


def page(title, body, depth=0):
    up = "../" * depth
    return (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(title)}</title>\n<link rel=\"stylesheet\" href=\"{up}style.css\">\n"
            f"</head>\n<body>\n<nav><a href=\"{up}index.html\">Hardware</a>"
            f"<a href=\"{up}charts.html\">Charts</a><a href=\"{up}search.html\">Search</a></nav>\n{body}\n</body>\n</html>\n")


def table(head, rows, classes=None):
    out = ["<div class=\"scroll\"><table>", "<tr>" + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr>"]
    for i, r in enumerate(rows):
        tds = []
        for h, v in zip(head, r):
            cls = "num" if h in NUMERIC else (classes[i] if classes and h == STATUS_COL else "")
            tds.append(f"<td class=\"{cls}\">{v}</td>" if cls else f"<td>{v}</td>")
        out.append("<tr>" + "".join(tds) + "</tr>")
    out.append("</table></div>")
    return "\n".join(out)


def hardware_block(machine, docs, backends):
    rows = []
    nodes = machine.get("nodes") or [machine]
    for n, node in enumerate(nodes):
        tag = f"Node {n + 1} " if machine.get("nodes") else ""
        for i, g in enumerate(node.get("gpus", [])):
            cap = f", {g['power_cap_w']} W" if g.get("power_cap_w") else ""
            mem = f" - {g['vram_mib'] / 1024:.0f} GB" if g.get("vram_mib") else ""
            arch = f", {g['arch']}" if g.get("arch") else ""
            link = (f", PCIe {g['pcie_gen']}.0 x{g['pcie_width']}"
                    if g.get("pcie_gen") and g.get("pcie_width") else "")
            rows.append([f"{tag}GPU {i}", esc(f"{g.get('name') or '?'}{mem}{cap}{arch}{link}")])
        if not node.get("gpus"):
            rows.append([f"{tag}GPU", "none recorded"])
        threads = f" - {node['threads']} threads" if node.get("threads") else ""
        sockets = f", {node['sockets']} socket(s)" if node.get("sockets") else ""
        rows.append([f"{tag}CPU", esc(f"{node.get('cpu') or '?'}{threads}{sockets}")])
        if node.get("cpu_flags"):
            rows.append([f"{tag}Instruction sets", esc(", ".join(node["cpu_flags"]))])
        if node.get("ram_gib"):
            rows.append([f"{tag}RAM", esc(f"{node['ram_gib']} GB")])
    rows.append(["Backend", esc(", ".join(backends))])
    for key, name in (("driver", "Driver"), ("kernel", "Kernel")):
        seen = sorted({(d.get("machine") or {}).get(key) for d in docs} - {None})
        if seen:
            rows.append([name, esc(", ".join(seen))])
    note = ""
    if any((d.get("machine") or {}).get("attested") for d in docs):
        note = ("<p class=\"note\">Runs taken before the runner recorded its machine carry the "
                "hardware an operator attested for them; their driver and kernel are unknown.</p>")
    return table(["", ""], rows) + note


def span(docs):
    days = sorted((d.get("timestamp") or "")[:10] for d in docs if d.get("timestamp"))
    return (days[0], days[-1]) if days else ("?", "?")


def load():
    """(run_id, record, path) of every attributed record check.py accepts."""
    paths = R.all_paths()
    accepted, refused = K.check(paths)
    for path, why in refused:
        print(f"left out {K.show(path)}: " + "; ".join(why), file=sys.stderr)
    out = [(p.stem, R.read(p), p) for p in accepted]
    out.sort(key=lambda t: (t[1].get("timestamp") or "", t[0]))
    return out


def main():
    entries = load()
    status = R.statuses([(rid, rec) for rid, rec, _ in entries])
    short = {}
    for rid, rec, _ in entries:
        short.setdefault(rid[:8], []).append(rid)
    clash = [k for k, v in short.items() if len(v) > 1]
    if clash:
        sys.exit(f"run ids share their first 8 digits, a row cannot name its record: {clash}")
    record_of = {rid: rec for rid, rec, _ in entries}

    hardware = {}
    for rid, rec, path in entries:
        hardware.setdefault(path.parent.name, []).append((rid, rec, path))

    OUT.mkdir(exist_ok=True)
    (OUT / "hw").mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS.lstrip())
    head = [c if c != "Date" else "Date (UTC)" for c in B.COLS] + [STATUS_COL]
    search, index_rows, written = [], [], set()
    for hid, group in sorted(hardware.items(), key=lambda kv: -len(kv[1])):
        docs = [rec for _, rec, _ in group]
        machine = next(d["machine"] for d in reversed(docs) if d.get("machine"))
        label = R.H.label(machine)
        cards = sorted({g.get("name") or "?" for g in machine.get("gpus", [])}) or ["no card"]
        backends = {}
        for rid, rec, path in group:
            backends.setdefault(R.C.loken_backend(rec), []).append((rec, rec.get("converted_from") or path.name, rid))
        sections, tabled, row_count = [], [], 0
        for backend, triples in sorted(backends.items(), key=lambda kv: -len(kv[1])):
            tabled += [d for d, _, _ in triples]
            rows_ = [r[:17] + [str(r[17])[:10]] + r[18:] for r in B.cells(B.load_docs(triples))]
            row_count += len(rows_)
            first, last = span([d for d, _, _ in triples])
            builds = sorted({plain(r[5])[len("loken "):] for r in rows_
                             if plain(r[5]).startswith("loken ") and " + " not in r[5]})
            lines, classes = [], []
            for r in rows_:
                rid = short[r[18]][0]
                st = status[rid]
                lines.append([cell_html(v) for v in r] + [st])
                classes.append(st)
                search.append({"hw": hid, "label": label, "cards": cards, "backend": backend,
                               "model": plain(r[0]), "ctx": plain(r[1]), "prompt": plain(r[2]),
                               "mode": plain(r[3]), "device": plain(r[4]), "engine": plain(r[5]),
                               "prefill": plain(r[6]), "ttft": plain(r[7]), "decode": plain(r[8]),
                               "tokens": plain(r[9]), "e2e": plain(r[10]), "jreq": plain(r[11]),
                               "jtok": plain(r[12]), "dprefill": plain(r[13]), "dttft": plain(r[14]),
                               "ddecode": plain(r[15]), "denergy": plain(r[16]), "date": r[17],
                               "run": r[18], "status": st,
                               "m": {"prefill": figures(r[6]), "ttft": figures(r[7]), "decode": figures(r[8]),
                                     "tokens": figures(r[9]), "e2e": figures(r[10]), "jreq": figures(r[11]),
                                     "jtok": figures(r[12])}})
            notes = [f"{len(triples)} run(s), {first} to {last}."]
            if builds:
                notes.append(f"loken builds measured: {', '.join(builds)}.")
            notes += backend_note(backend)
            sections.append(f"<h2>Results, backend {esc(backend)}</h2>\n<p>{esc(' '.join(notes))}</p>\n"
                            + table(head, lines, classes))
        confirmed = sum(1 for rid, _, _ in group if status[rid] == R.CONFIRMED)
        hosts = {R.submitter(rec) for _, rec, _ in group}
        host_count = len({h for h in hosts if h})
        body = (f"<h1>{esc(label)}</h1>\n<p>hardware_id <code>{esc(hid)}</code>. "
                f"{len(group)} record(s), {confirmed} confirmed, from {host_count} host(s).</p>\n"
                + "<p>" + " ".join(f"<a href=\"../charts.html#view=models&amp;hw1={esc(hid)}/{esc(b)}\">Charts"
                                   f"{' (' + esc(b) + ')' if len(backends) > 1 else ''}</a>" for b in sorted(backends))
                + "</p>\n<h2>Hardware</h2>\n" + hardware_block(machine, docs, sorted(backends))
                + "\n<p class=\"note\">Columns as in loken's BENCHMARKS.md. A row's Date (UTC) and "
                "Run name the record behind it; Status is that record's.</p>\n"
                + "\n".join(sections))
        (OUT / "hw" / f"{hid}.html").write_text(page(label, body, depth=1))
        written.add(f"{hid}.html")
        first, last = span(tabled)
        index_rows.append([f"<a href=\"hw/{esc(hid)}.html\">{esc(label)}</a>", esc(", ".join(sorted(backends))),
                           f"<code>{esc(hid)}</code>", esc(f"{first} to {last}"), str(len(tabled)),
                           str(row_count), f"{confirmed} / {len(group)}", str(host_count)])
    for stale in (OUT / "hw").glob("*.html"):
        if stale.name not in written:
            stale.unlink()

    body = ("<h1>loken benchmarks</h1>\n<p>Runs of the loken bench campaign, one page per hardware "
            "configuration. A record is <span class=\"confirmed\">confirmed</span> when another record "
            "of the same equivalence class on the same hardware comes from another host; otherwise it is <span class=\"submitted\">submitted</span>.</p>\n"
            + table(["Hardware", "Backend", "Id", "Runs from", "Runs", "Rows", "Confirmed records",
                     "Hosts"], index_rows))
    (OUT / "index.html").write_text(page("loken benchmarks", body))
    (OUT / "index.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")))
    (OUT / "search.html").write_text(page("Search benchmarks", SEARCH))
    (OUT / "charts.html").write_text(page("Benchmark charts", CHARTS))
    for asset in (R.ROOT / "web").glob("*.js"):
        (OUT / asset.name).write_text(asset.read_text())
    print(f"wrote {len(written)} hardware page(s), {len(search)} row(s) in index.json, "
          f"{len(entries)} record(s)")
    return 0


SEARCH = """<h1>Search</h1>
<form onsubmit="return false">
<label>Words <input id="words" placeholder="model, card, engine..." size="28"></label>
<label>Hardware <select id="hardware"></select></label>
<label>Engine <select id="engine"></select></label>
<label>Device <select id="device"></select></label>
<label>Mode <select id="mode"></select></label>
<label>Prompt <select id="prompt"></select></label>
<label>Context <select id="ctx"></select></label>
<button id="csv" type="button">Download CSV</button>
</form>
<p id="count" class="note"></p>
<div class="scroll"><table id="out"></table></div>
<p><button id="more" type="button" style="display:none">Show every row</button></p>
<script src="search.js"></script>"""

CHARTS = """<h1>Charts</h1>
<form onsubmit="return false" class="controls">
<label>Chart <select id="view"></select></label>
<label>Metric <select id="metric"></select></label>
<label id="half-row">Figure <select id="half"></select></label>
<label>Prompt <select id="prompt"></select></label>
<label>Mode <select id="mode"></select></label>
<label>Device <select id="device"></select></label>
<fieldset><legend>Engines</legend><span id="engines"></span></fieldset>
</form>
<form onsubmit="return false" class="controls" id="ctx-only">
<label>Model <input id="model" list="models" size="40" placeholder="start typing a model"></label>
<label><input type="checkbox" id="log"> logarithmic scale</label>
<fieldset><legend>Hardware</legend><span id="hw"></span></fieldset>
</form>
<form onsubmit="return false" class="controls" id="models-only">
<label>Hardware <select id="hw1"></select></label>
<label>Context <select id="ctx"></select></label>
</form>
<form onsubmit="return false" class="controls" id="hw-only">
<label>Model <input id="model2" list="models" size="40" placeholder="start typing a model"></label>
<label>Context <select id="ctx2"></select></label>
</form>
<datalist id="models"></datalist>
<div id="chart"></div>
<p class="note">A point or a bar is the newest run of its cell; hover it for the engine build and the date. Rates are
the warm figure (median of the later requests) or the cold one (the first request).</p>
<script src="charts.js"></script>"""


if __name__ == "__main__":
    raise SystemExit(main())
