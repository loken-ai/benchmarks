// The search page: find rows by words, narrow them by hardware, engine, device, mode, prompt and
// context size, sort by any column and download what is shown as CSV.
(function () {
  "use strict";
  const COLS = [["Hardware", "label"], ["Model", "model"], ["Ctx", "ctx"], ["Prompt", "prompt"], ["Mode", "mode"],
    ["Device", "device"], ["Engine", "engine"], ["Prefill tok/s", "prefill"], ["TTFT ms", "ttft"], ["Decode tok/s", "decode"],
    ["Tokens", "tokens"], ["E2E ms", "e2e"], ["J/req", "jreq"], ["J/token", "jtok"], ["Δ prefill", "dprefill"],
    ["Δ TTFT", "dttft"], ["Δ decode", "ddecode"], ["Δ energy", "denergy"], ["Date (UTC)", "date"],
    ["Run", "run"], ["Status", "status"]];
  const NUM = new Set(["ctx", "prefill", "ttft", "decode", "tokens", "e2e", "jreq", "jtok", "dprefill", "dttft", "ddecode", "denergy"]);
  const SHOWN = 500;
  const family = e => /^loken \+ /.test(e) ? "loken+" : e.split(" ")[0];
  const $ = id => document.getElementById(id);
  const el = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
  let rows = [], sortKey = null, sortDir = 1, all = false;

  // The first number of a cell: "123.4 / 120.1" sorts by its cold half, "-18% / -13%" by -18.
  const numeric = s => { const m = /-?\d+(\.\d+)?/.exec(String(s)); return m ? parseFloat(m[0]) : null; };

  function fill(id, values, any) {
    const s = $(id);
    s.replaceChildren(...[any].concat(values).map(v => { const o = el("option", v); o.value = v === any ? "" : v; return o; }));
  }

  function matches() {
    const terms = $("words").value.toLowerCase().split(/\s+/).filter(Boolean);
    const hw = $("hardware").value, eng = $("engine").value, dev = $("device").value, mode = $("mode").value,
      prompt = $("prompt").value, ctx = $("ctx").value;
    return rows.filter(r =>
      (!hw || r.label + " " + r.backend === hw) && (!eng || family(r.engine) === eng) && (!dev || r.device === dev) &&
      (!mode || r.mode === mode) && (!prompt || r.prompt === prompt) && (!ctx || r.ctx === ctx) &&
      terms.every(t => (r.model + " " + r.label + " " + r.engine + " " + r.backend).toLowerCase().includes(t)));
  }

  function sorted(hits) {
    if (!sortKey) return hits;
    const num = NUM.has(sortKey);
    return hits.slice().sort((a, b) => {
      const x = num ? numeric(a[sortKey]) : a[sortKey], y = num ? numeric(b[sortKey]) : b[sortKey];
      if (x === null || x === undefined) return 1;
      if (y === null || y === undefined) return -1;
      return (x < y ? -1 : x > y ? 1 : 0) * sortDir;
    });
  }

  function render() {
    const hits = sorted(matches());
    const t = $("out"); t.replaceChildren();
    const h = t.insertRow();
    for (const [name, key] of COLS) {
      const th = el("th", name + (sortKey === key ? (sortDir > 0 ? " ▲" : " ▼") : ""));
      th.style.cursor = "pointer";
      th.addEventListener("click", () => { sortDir = sortKey === key ? -sortDir : 1; sortKey = key; render(); });
      h.appendChild(th);
    }
    for (const r of hits.slice(0, all ? hits.length : SHOWN)) {
      const tr = t.insertRow();
      for (const [, key] of COLS) {
        let td;
        if (key === "label") { td = document.createElement("td"); const a = el("a", r.label); a.href = "hw/" + r.hw + ".html"; td.appendChild(a); }
        else td = el("td", r[key], NUM.has(key) ? "num" : key === "status" ? r.status : "");
        tr.appendChild(td);
      }
    }
    $("count").textContent = hits.length + " row(s)" + (!all && hits.length > SHOWN ? ", the first " + SHOWN + " shown" : "");
    $("more").style.display = !all && hits.length > SHOWN ? "" : "none";
    $("csv").onclick = () => {
      const esc = v => '"' + String(v).replace(/"/g, '""') + '"';
      const text = [COLS.map(c => esc(c[0])).join(",")].concat(hits.map(r => COLS.map(c => esc(r[c[1]])).join(","))).join("\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" })); a.download = "benchmarks.csv"; a.click();
    };
  }

  fetch("index.json").then(r => r.json()).then(data => {
    rows = data;
    const uniq = key => [...new Set(rows.map(r => r[key]))].sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));
    fill("hardware", [...new Set(rows.map(r => r.label + " " + r.backend))].sort(), "any hardware");
    fill("engine", [...new Set(rows.map(r => family(r.engine)))].sort(), "any engine");
    fill("device", uniq("device"), "any device"); fill("mode", uniq("mode"), "any mode");
    fill("prompt", uniq("prompt"), "any prompt"); fill("ctx", uniq("ctx"), "any context");
    for (const id of ["words", "hardware", "engine", "device", "mode", "prompt", "ctx"]) $(id).addEventListener("input", () => { all = false; render(); });
    $("more").addEventListener("click", () => { all = true; render(); });
    render();
  });
})();
