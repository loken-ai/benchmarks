"""The look of the site: the page shell, the hero, the hardware cards and the result tables.

site.py reads the records and decides what a page says; this file decides how it is laid out.
The brand (mark, written word, banner) is the one of the organisation's .github repository and is
linked from there, never copied.
"""
import html, re

BRAND = "https://raw.githubusercontent.com/loken-ai/.github/main/brand"
REPO = "https://github.com/loken-ai/benchmarks"
NAV = [("index.html", "Hardware"), ("charts.html", "Charts"), ("search.html", "Search")]

NUMERIC = {"Ctx", "Prefill tok/s", "TTFT ms", "Decode tok/s", "Tokens", "E2E ms", "J/req", "J/token",
           "\u0394 prefill", "\u0394 TTFT", "\u0394 decode", "\u0394 energy"}
RATES = {"Prefill tok/s", "TTFT ms", "Decode tok/s"}
DELTAS = {"\u0394 prefill", "\u0394 TTFT", "\u0394 decode", "\u0394 energy"}


def esc(value):
    return html.escape(str(value))


def page(title, body, depth=0, active="", description=""):
    up = "../" * depth
    nav = "".join(f'<a href="{up}{href}"{" aria-current=\"page\"" if href == active else ""}>{label}</a>'
                  for href, label in NAV)
    desc = esc(description or "The loken bench campaign: every run of every machine, with charts and a search.")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{BRAND}/png/banner.png">
<link rel="icon" type="image/svg+xml" href="{BRAND}/favicon.svg">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="top"><div class="wrap">
<a class="brand" href="{up}index.html"><img src="{BRAND}/icon.svg" alt="" width="34" height="34"><span><b>loken</b> benchmarks</span></a>
<nav>{nav}</nav>
<a class="gh" href="{REPO}">GitHub</a>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<span>Runs are published under <a href="{REPO}/blob/main/LICENSE-DATA">CC BY 4.0</a>, the code under MIT or Apache-2.0.</span>
<a href="{REPO}">Run the campaign and share your runs</a>
<a href="{REPO}/blob/main/docs/METHOD.md">How a cell is measured</a>
<a href="https://github.com/loken-ai/loken">loken</a>
</div></footer>
</body>
</html>
"""


def hero(stats):
    tiles = "".join(f'<div class="stat"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v in stats)
    return f"""<section class="hero">
<div>
<h1>Measured, not claimed.</h1>
<p class="lead">Every run of the loken bench campaign, from every machine that ran it: loken against ollama
and vLLM on the same prompts and the same clock, the cells where loken loses published with the rest.</p>
<div class="cta"><a class="btn primary" href="charts.html">Open the charts</a>
<a class="btn" href="search.html">Search the rows</a>
<a class="btn" href="{REPO}">Run it on your machine</a></div>
</div>
<img src="{BRAND}/banner.svg" alt="loken, self-hosted multimodal inference" width="1280" height="420">
</section>
<section class="stats">{tiles}</section>"""


def short_card(name):
    return re.sub(r"^(NVIDIA GeForce|NVIDIA|AMD Radeon|AMD|Intel\(R\)|Intel)\s+", "", name or "?")


def cards_title(machine):
    nodes = machine.get("nodes") or [machine]
    names = [short_card(g.get("name")) for n in nodes for g in n.get("gpus", [])]
    if not names:
        return "CPU only"
    counts = {}
    for n in names:
        counts[n] = counts.get(n, 0) + 1
    return " + ".join(f"{c} x {n}" if c > 1 else n for n, c in sorted(counts.items()))


def vram_gb(machine):
    nodes = machine.get("nodes") or [machine]
    total = sum(g.get("vram_mib") or 0 for n in nodes for g in n.get("gpus", []))
    return f"{total / 1024:.0f} GB" if total else ""


def backend_chip(backend):
    if backend == "unstated":
        return '<span class="chip plain">backend not recorded</span>'
    return f'<span class="chip backend">{esc(backend)}</span>'


def hardware_card(info):
    chips = "".join(backend_chip(b) for b in info["backends"])
    if info["vram"]:
        chips += f'<span class="chip">{esc(info["vram"])} VRAM</span>'
    for arch in info["archs"]:
        chips += f'<span class="chip">{esc(arch)}</span>'
    win = ""
    if info["wins"] + info["losses"]:
        total = info["wins"] + info["losses"]
        win = (f'<div class="win"><div class="bar"><i style="width:{100 * info["wins"] / total:.1f}%"></i>'
               f'<i style="width:{100 * info["losses"] / total:.1f}%"></i></div>'
               f'<p><span class="item"><span class="key green"></span>loken decodes faster in {info["wins"]} of {total} compared cells</span> '
               f'<span class="item"><span class="key red"></span>slower in {info["losses"]}</span></p></div>')
    return f"""<a class="card" href="hw/{esc(info["hid"])}.html">
<h3>{esc(info["title"])}</h3>
<div class="cpu">{esc(info["cpu"])}</div>
<div class="chips">{chips}</div>
<div class="facts">
<div><b>{info["runs"]}</b><span>runs</span></div>
<div><b>{info["rows"]}</b><span>rows</span></div>
<div><b>{info["confirmed"]}</b><span>confirmed</span></div>
<div><b>{info["hosts"]}</b><span>host(s)</span></div>
</div>
{win}
<div class="muted note">{esc(info["span"])}</div>
</a>"""


def _dl(pairs):
    return "<dl>" + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in pairs if v) + "</dl>"


def specs(machine, docs):
    """The architecture of the machine, or of each node of a cluster."""
    nodes = machine.get("nodes") or [machine]
    blocks = []
    for n, node in enumerate(nodes):
        tag = f"Node {n + 1}: " if machine.get("nodes") else ""
        gpus = "".join(
            f'<div class="gpu"><b>{esc(g.get("name") or "?")}</b><span>'
            + esc(", ".join(x for x in (
                g.get("arch"), f"{g['vram_mib'] / 1024:.0f} GB" if g.get("vram_mib") else "",
                f"{g['power_cap_w']} W cap" if g.get("power_cap_w") else "",
                f"PCIe {g['pcie_gen']}.0 x{g['pcie_width']}" if g.get("pcie_gen") and g.get("pcie_width") else "") if x))
            + "</span></div>" for g in node.get("gpus", [])) or '<span class="muted">no card recorded</span>'
        blocks.append(f'<div class="spec"><h3>{esc(tag)}Cards</h3>{gpus}</div>')
        cpu = [("Processor", node.get("cpu")), ("Threads", node.get("threads")), ("Sockets", node.get("sockets")),
               ("Memory", f"{node['ram_gib']} GB" if node.get("ram_gib") else ""),
               ("Instruction sets", ", ".join(node.get("cpu_flags") or []))]
        blocks.append(f'<div class="spec"><h3>{esc(tag)}Host</h3>{_dl(cpu)}</div>')
        soft = []
        for key, name in (("os", "System"), ("kernel", "Kernel"), ("driver", "NVIDIA driver")):
            seen = sorted({(d.get("machine") or {}).get(key) for d in docs} - {None}) if not machine.get("nodes") \
                else [node.get(key)] if node.get(key) else []
            if seen:
                soft.append((name, ", ".join(str(s) for s in seen)))
        if soft:
            blocks.append(f'<div class="spec"><h3>{esc(tag)}Software</h3>{_dl(soft)}</div>')
    return '<div class="specs">' + "".join(blocks) + "</div>"


def _delta(value):
    parts = value.split("/")
    out = []
    for p in parts:
        p = p.strip()
        cls = "pos" if p.startswith(("+", "**+")) else "neg" if p.startswith(("-", "**-")) else ""
        out.append(f'<span class="{cls}">{esc(p.replace("**", ""))}</span>' if cls else esc(p.replace("**", "")))
    return " / ".join(out)


def _rate(value):
    text = value.strip()
    bold = "**" in text
    parts = [p.strip().replace("**", "") for p in text.split("/")]
    if len(parts) == 2:
        warm = f"<strong>{esc(parts[1])}</strong>" if bold else esc(parts[1])
        return f'<span class="cold">{esc(parts[0])}</span> / {warm}'
    return f"<strong>{esc(text.replace('**', ''))}</strong>" if bold else esc(text)


def result_table(head, rows, statuses):
    """`rows` are lists of raw cells of bench_row; the first column is the model."""
    out = ['<div class="scroll"><table class="results"><thead><tr>']
    for h in head:
        out.append(f'<th{" class=num" if h in NUMERIC else ""}>{esc(h)}</th>')
    out.append("</tr></thead><tbody>")
    alt, last = False, None
    for row, status in zip(rows, statuses):
        if row[0] != last:
            alt, last = not alt, row[0]
        engine = row[5].replace("**", "").strip().split(" ")[0].lower()
        out.append(f'<tr{" class=alt" if alt else ""}>')
        for h, v in zip(head[:-1], row):
            if h in DELTAS:
                out.append(f'<td class="num">{_delta(v)}</td>')
            elif h in RATES:
                out.append(f'<td class="num">{_rate(v)}</td>')
            elif h == "Engine":
                out.append(f'<td class="eng {esc(engine)}">{esc(v.replace("**", ""))}</td>')
            elif h in NUMERIC:
                out.append(f'<td class="num">{esc(v.replace("**", ""))}</td>')
            else:
                out.append(f"<td>{esc(v.replace('**', ''))}</td>")
        out.append(f'<td><span class="badge {esc(status)}">{esc(status)}</span></td></tr>')
    out.append("</tbody></table></div>")
    return "".join(out)
