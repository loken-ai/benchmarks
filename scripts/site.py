#!/usr/bin/env python3
"""Write the static site into `site/` from the records under `runs/`.

    scripts/site.py

The site is an index of hardware configurations, one page per hardware_id with its architecture and
the table the loken report writes (bench_row.py), one table per backend loken answered on, each
row with the status of the record behind it, charts of the rates, and a search page over
`index.json`. Records check.py refuses appear nowhere. Dates are UTC. The layout is pages.py and
the files of web/.
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
import pages as P  # noqa: E402

# The report derives an unstated loken version from loken's git history, which this
# repository does not hold: such a row is labelled without a number.
B._dev_version_at = lambda epoch: None

OUT = R.ROOT / "site"
STATUS_COL = "Status"
COMPARISON = re.compile(r"^\*{0,2}([+-])")

def backend_note(backend):
    """The line a page carries when no reference engine runs its backend."""
    if backend == "opencl":
        return ["No reference engine runs a language model through OpenCL on a GPU (ollama and "
                "vLLM do not), so this page holds loken alone."]
    return []


def esc(value):
    return html.escape(str(value))


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


def backend_label(backend):
    return backend if backend != "unstated" else "backend not recorded"


def decode_verdicts(rows):
    """(faster, slower) counts of the warm decode delta of the compared rows."""
    wins = losses = 0
    for r in rows:
        half = r[15].split("/")[-1].strip()
        m = COMPARISON.match(half)
        if m:
            wins += m.group(1) == "+"
            losses += m.group(1) == "-"
    return wins, losses


def main():
    entries = load()
    status = R.statuses([(rid, rec) for rid, rec, _ in entries])
    short = {}
    for rid, rec, _ in entries:
        short.setdefault(rid[:8], []).append(rid)
    clash = [k for k, v in short.items() if len(v) > 1]
    if clash:
        sys.exit(f"run ids share their first 8 digits, a row cannot name its record: {clash}")

    hardware = {}
    for rid, rec, path in entries:
        hardware.setdefault(path.parent.name, []).append((rid, rec, path))

    OUT.mkdir(exist_ok=True)
    (OUT / "hw").mkdir(exist_ok=True)
    for asset in (R.ROOT / "web").iterdir():
        (OUT / asset.name).write_text(asset.read_text())
    head = [c if c != "Date" else "Date (UTC)" for c in B.COLS] + [STATUS_COL]
    search, infos, written = [], [], set()
    models, all_hosts, wins_all, losses_all = set(), set(), 0, 0
    for hid, group in sorted(hardware.items(), key=lambda kv: -len(kv[1])):
        docs = [rec for _, rec, _ in group]
        machine = next(d["machine"] for d in reversed(docs) if d.get("machine"))
        label = R.H.label(machine)
        nodes = machine.get("nodes") or [machine]
        cards = sorted({g.get("name") or "?" for n in nodes for g in n.get("gpus", [])}) or ["no card"]
        backends = {}
        for rid, rec, path in group:
            backends.setdefault(R.C.loken_backend(rec), []).append((rec, rec.get("converted_from") or path.name, rid))
        sections, tabled, row_count, wins, losses = [], [], 0, 0, 0
        for backend, triples in sorted(backends.items(), key=lambda kv: -len(kv[1])):
            tabled += [d for d, _, _ in triples]
            rows_ = [r[:17] + [str(r[17])[:10]] + r[18:] for r in B.cells(B.load_docs(triples))]
            row_count += len(rows_)
            w, l = decode_verdicts(rows_)
            wins, losses = wins + w, losses + l
            first, last = span([d for d, _, _ in triples])
            builds = sorted({plain(r[5])[len("loken "):] for r in rows_
                             if plain(r[5]).startswith("loken ") and " + " not in r[5]})
            statuses = []
            for r in rows_:
                rid = short[r[18]][0]
                st = status[rid]
                statuses.append(st)
                models.add(plain(r[0]))
                search.append({"hw": hid, "label": label, "title": P.cards_title(machine), "cards": cards, "backend": backend,
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
            tid = f"t-{len(sections)}"
            sections.append(
                f'<h2>Results {P.backend_chip(backend)}</h2>\n'
                f'<p class="note">{P.esc(" ".join(notes))}</p>\n'
                f'<div class="toolbar"><label>Filter this table <input type="search" data-filter="{tid}" '
                f'placeholder="model or engine" size="26"></label>'
                f'<a class="btn" href="../charts.html#view=models&amp;hw1={P.esc(hid)}/{P.esc(backend)}">Chart these rows</a></div>\n'
                + P.result_table(head, rows_, statuses).replace('<table class="results">', f'<table class="results" id="{tid}">', 1))
        confirmed = sum(1 for rid, _, _ in group if status[rid] == R.CONFIRMED)
        hosts = {h for h in (R.submitter(rec) for _, rec, _ in group) if h}
        all_hosts |= hosts
        wins_all, losses_all = wins_all + wins, losses_all + losses
        first, last = span(tabled)
        info = {"hid": hid, "title": P.cards_title(machine), "cpu": nodes[0].get("cpu") or "?",
                "backends": sorted(backends), "vram": P.vram_gb(machine),
                "archs": sorted({g["arch"] for n in nodes for g in n.get("gpus", []) if g.get("arch")}),
                "runs": len(tabled), "rows": row_count, "confirmed": confirmed, "hosts": len(hosts),
                "wins": wins, "losses": losses, "span": f"{first} to {last}"}
        infos.append(info)
        tiles = "".join(f'<div class="stat"><b>{P.esc(v)}</b><span>{P.esc(k)}</span></div>' for k, v in (
            ("runs", info["runs"]), ("rows", row_count), ("confirmed records", f"{confirmed} / {len(group)}"),
            ("hosts", len(hosts)), ("from", first), ("to", last)))
        chips = "".join(P.backend_chip(b) for b in info["backends"])
        body = (f'<div class="crumbs"><a href="../index.html">Hardware</a> / {P.esc(info["title"])}</div>\n'
                f'<h1>{P.esc(info["title"])}</h1>\n<p class="sub">{P.esc(info["cpu"])}</p>\n'
                f'<div class="chips">{chips}<span class="chip">hardware id {P.esc(hid)}</span></div>\n'
                f'<section class="stats">{tiles}</section>\n<h2>Architecture</h2>\n{P.specs(machine, docs)}\n'
                f'<p class="note">Columns as in the <a href="{P.REPO}/blob/main/docs/METHOD.md">method</a>. Each rate reads '
                f'cold / warm. A row\'s Date (UTC) and Run name the record behind it; Status is that record\'s.</p>\n'
                + "\n".join(sections) + '\n<script src="../table.js"></script>')
        (OUT / "hw" / f"{hid}.html").write_text(P.page(label, body, depth=1, active="index.html",
                                                        description=f"loken benchmarks on {P.cards_title(machine)}."))
        written.add(f"{hid}.html")
    for stale in (OUT / "hw").glob("*.html"):
        if stale.name not in written:
            stale.unlink()

    compared = wins_all + losses_all
    stats = [("hardware configurations", len(infos)), ("machines", len(all_hosts)), ("runs", len(entries)),
             ("models", len(models)), ("rows", len(search)),
             ("decode cells won by loken", f"{100 * wins_all // compared}%" if compared else "-")]
    cards = "".join(P.hardware_card(i) for i in infos)
    body = (P.hero(stats) + '\n<h2>Hardware</h2>\n<div class="cards">' + cards + "</div>\n"
            '<h2>Reading the numbers</h2>\n<div class="specs">'
            '<div class="spec"><h3>Cold and warm</h3><p>Every cell runs its prompt three times. The first request is '
            'cold; the later ones, served from a prompt cache by an engine that keeps one, give the warm median. Each '
            'rate shows both, cold first.</p></div>'
            '<div class="spec"><h3>Confirmed</h3><p>A record is confirmed when another host measured the same '
            'configuration on the same hardware. Until then it is submitted, and shown as such.</p></div>'
            '<div class="spec"><h3>Anonymous</h3><p>A record names no person and no machine: the day of the run '
            'without its hour, the architecture of the hardware, and two one-way hashes.</p></div></div>')
    (OUT / "index.html").write_text(P.page("loken benchmarks", body, active="index.html"))
    (OUT / "index.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")))
    (OUT / "search.html").write_text(P.page("Search benchmarks", SEARCH, active="search.html"))
    (OUT / "charts.html").write_text(P.page("Benchmark charts", CHARTS, active="charts.html"))
    print(f"wrote {len(written)} hardware page(s), {len(search)} row(s) in index.json, "
          f"{len(entries)} record(s)")
    return 0


SEARCH = """<h1>Search</h1>
<p class="sub">Every row of every machine. Type words, narrow by hardware, engine, device, mode, prompt or context size,
click a column to sort, and download what is shown.</p>
<form onsubmit="return false" class="panel">
<label>Words <input id="words" type="search" placeholder="model, card, engine..." size="28"></label>
<label>Hardware <select id="hardware"></select></label>
<label>Engine <select id="engine"></select></label>
<label>Device <select id="device"></select></label>
<label>Mode <select id="mode"></select></label>
<label>Prompt <select id="prompt"></select></label>
<label>Context <select id="ctx"></select></label>
<button id="csv" type="button">Download CSV</button>
</form>
<p id="count" class="note"></p>
<div class="scroll"><table id="out" class="results"></table></div>
<p><button id="more" type="button" style="display:none">Show every row</button></p>
<script src="search.js"></script>"""

CHARTS = """<h1>Charts</h1>
<p class="sub">A rate across context sizes, across models, or across hardware. Pick a chart, a metric and the
cells to compare; hover a point or a bar for the engine build and the date.</p>
<form onsubmit="return false" class="panel">
<label>Chart <select id="view"></select></label>
<label>Metric <select id="metric"></select></label>
<label id="half-row">Figure <select id="half"></select></label>
<label>Prompt <select id="prompt"></select></label>
<label>Mode <select id="mode"></select></label>
<label>Device <select id="device"></select></label>
<fieldset><legend>Engines</legend><span id="engines"></span></fieldset>
<span id="ctx-only" style="display:contents">
<label>Model <input id="model" list="models" size="38" placeholder="start typing a model"></label>
<label>Scale <span><input type="checkbox" id="log"> logarithmic</span></label>
<fieldset class="wide"><legend>Hardware</legend><span id="hw"></span></fieldset>
</span>
<span id="models-only" style="display:contents">
<label>Hardware <select id="hw1"></select></label>
<label>Context <select id="ctx"></select></label>
</span>
<span id="hw-only" style="display:contents">
<label>Model <input id="model2" list="models" size="38" placeholder="start typing a model"></label>
<label>Context <select id="ctx2"></select></label>
</span>
</form>
<datalist id="models"></datalist>
<div class="chartbox"><h2 id="title"></h2><div id="chart"></div></div>
<p class="note">A point or a bar is the newest run of its cell. A rate is the warm figure, the median of the requests
after the first, or the cold one, the first request.</p>
<script src="charts.js"></script>"""


if __name__ == "__main__":
    raise SystemExit(main())
