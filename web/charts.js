// Charts over the rows of index.json: the rate of a model across context sizes, across models
// and across hardware. The functions are pure (rows in, SVG text out) so that the tests run them
// without a browser; the page wiring at the bottom runs only in one.
(function (root) {
  "use strict";

  const METRICS = {
    decode: { label: "Decode tok/s", half: true },
    prefill: { label: "Prefill tok/s", half: true },
    ttft: { label: "Time to first token, ms", half: true },
    e2e: { label: "End to end, ms", half: false },
    jtok: { label: "Joules per token", half: false },
    jreq: { label: "Joules per request", half: false },
  };
  const COLORS = { loken: "#1b873f", Ollama: "#c77700", vLLM: "#7b3ac2", "loken+": "#0b7285" };
  const FALLBACK = ["#c2255c", "#1971c2", "#5c940d", "#e8590c"];
  const DASHES = ["", "6 3", "2 3", "8 3 2 3"];

  // The engine family of a row: loken, Ollama or vLLM; "loken+" for loken with a drafter named.
  function family(engine) {
    if (/^loken \+ /.test(engine)) return "loken+";
    return engine.split(" ")[0];
  }

  function colorOf(fam, seen) {
    if (COLORS[fam]) return COLORS[fam];
    if (!(fam in seen)) seen[fam] = FALLBACK[Object.keys(seen).length % FALLBACK.length];
    return seen[fam];
  }

  // The value of a row for a metric: cold or warm for the metrics that split, else the one figure.
  function value(row, metric, half) {
    const m = row.m && row.m[metric];
    if (!m) return null;
    const v = METRICS[metric].half ? m[half === "cold" ? 0 : 1] : m[0];
    return v === undefined || v === null ? null : v;
  }

  function hardwareLabel(row) {
    const cards = row.cards.length ? row.cards.join(" + ") : "CPU only";
    return row.backend && row.backend !== "unstated" ? cards + " (" + row.backend + ")" : cards;
  }

  // The rows that match the filters; a filter left out matches everything.
  function select(rows, f) {
    return rows.filter(r =>
      (!f.model || r.model === f.model) &&
      (!f.ctx || r.ctx === String(f.ctx)) &&
      (!f.prompt || r.prompt === f.prompt) &&
      (!f.mode || r.mode === f.mode) &&
      (!f.device || r.device === f.device) &&
      (!f.hw || f.hw.has(r.hw + "/" + r.backend)) &&
      (!f.engines || f.engines.has(family(r.engine))));
  }

  // The newest row of each key wins, as on the hardware pages.
  function newest(rows, keyOf) {
    const best = new Map();
    for (const r of rows) {
      const k = keyOf(r);
      const held = best.get(k);
      if (!held || (r.date + r.run) > (held.date + held.run)) best.set(k, r);
    }
    return [...best.values()];
  }

  // One line per hardware and engine: the metric against the context size.
  function contextSeries(rows, f, metric, half) {
    const picked = newest(select(rows, f), r => [r.hw, r.backend, r.engine, r.ctx, r.prompt, r.mode, r.device].join("|"));
    const seen = {}, hwIndex = new Map(), series = new Map();
    for (const r of picked) {
      const v = value(r, metric, half);
      if (v === null) continue;
      const hwKey = r.hw + "/" + r.backend;
      if (!hwIndex.has(hwKey)) hwIndex.set(hwKey, hwIndex.size);
      const key = hwKey + "|" + r.engine;
      if (!series.has(key)) {
        series.set(key, {
          label: hardwareLabel(r) + " - " + r.engine,
          color: colorOf(family(r.engine), seen),
          dash: DASHES[hwIndex.get(hwKey) % DASHES.length],
          points: [],
        });
      }
      series.get(key).points.push([Number(r.ctx), v, r.date]);
    }
    const out = [...series.values()];
    for (const s of out) s.points.sort((a, b) => a[0] - b[0]);
    return out.sort((a, b) => a.label.localeCompare(b.label));
  }

  // Bars grouped by `groupOf(row)`, one bar per engine family.
  function barGroups(rows, f, metric, half, groupOf, limit) {
    const picked = newest(select(rows, f), r => [r.hw, r.backend, r.engine, r.model, r.ctx, r.prompt, r.mode, r.device].join("|"));
    const groups = new Map(), seen = {};
    for (const r of picked) {
      const v = value(r, metric, half);
      if (v === null) continue;
      const g = groupOf(r), fam = family(r.engine);
      if (!groups.has(g)) groups.set(g, new Map());
      groups.get(g).set(fam, { v, color: colorOf(fam, seen), engine: r.engine, date: r.date });
    }
    const list = [...groups.entries()].map(([label, bars]) => ({
      label, bars: [...bars.entries()].map(([fam, b]) => ({ fam, ...b })).sort((a, b) => a.fam.localeCompare(b.fam)),
    }));
    const score = g => Math.max(...g.bars.map(b => b.v));
    list.sort((a, b) => score(b) - score(a));
    return limit ? list.slice(0, limit) : list;
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function format(v) {
    if (v >= 1000) return v.toFixed(0);
    if (v >= 100) return v.toFixed(1);
    if (v >= 10) return v.toFixed(1);
    return v.toFixed(2);
  }

  // Round tick values spanning [lo, hi] on a linear axis.
  function ticks(lo, hi, count) {
    if (hi <= lo) hi = lo + 1;
    const raw = (hi - lo) / count, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || raw;
    const out = [];
    for (let t = Math.ceil(lo / step) * step; t <= hi + step * 1e-9; t += step) out.push(+t.toPrecision(12));
    return out;
  }

  // Powers of ten inside [lo, hi] for a log axis, with 2 and 5 times them when the span is short.
  function logTicks(lo, hi) {
    const out = [], first = Math.floor(Math.log10(lo)), last = Math.ceil(Math.log10(hi));
    for (let e = first; e <= last; e++) for (const m of [1, 2, 5]) {
      const t = m * Math.pow(10, e);
      if (t >= lo * 0.999 && t <= hi * 1.001) out.push(t);
    }
    return out.length > 12 ? out.filter(t => /^1e/.test(t.toExponential().replace(/^1(\.0+)?e/, "1e"))) : out;
  }

  const W = 960, FONT = 'font-family="system-ui,sans-serif"';

  // Lines: x is the position of the context size among those present, y the metric.
  function lineChart(series, metricLabel, log) {
    const xs = [...new Set(series.flatMap(s => s.points.map(p => p[0])))].sort((a, b) => a - b);
    if (!xs.length) return '<p class="note">No row matches these filters.</p>';
    const ys = series.flatMap(s => s.points.map(p => p[1]));
    const useLog = log && Math.min(...ys) > 0;
    const left = 70, right = 20, top = 16, bottom = 44, h = 380;
    const lo = useLog ? Math.min(...ys) * 0.8 : 0, hi = Math.max(...ys) * 1.08;
    const sy = v => useLog
      ? top + (h - top - bottom) * (1 - (Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo)))
      : top + (h - top - bottom) * (1 - (v - lo) / (hi - lo));
    const sx = x => left + (W - left - right) * (xs.length === 1 ? 0.5 : xs.indexOf(x) / (xs.length - 1));
    const out = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${h}" width="100%" role="img" ${FONT} font-size="12">`];
    for (const t of useLog ? logTicks(lo, hi) : ticks(lo, hi, 6)) {
      out.push(`<line x1="${left}" x2="${W - right}" y1="${sy(t)}" y2="${sy(t)}" stroke="var(--line)"/>`,
        `<text x="${left - 8}" y="${sy(t) + 4}" text-anchor="end" fill="var(--muted)">${format(t)}</text>`);
    }
    for (const x of xs) {
      out.push(`<text x="${sx(x)}" y="${h - bottom + 20}" text-anchor="middle" fill="var(--muted)">${x >= 1024 ? x / 1024 + "K" : x}</text>`);
    }
    out.push(`<text x="${(left + W - right) / 2}" y="${h - 6}" text-anchor="middle" fill="var(--fg)">context size, tokens</text>`,
      `<text transform="translate(14 ${(top + h - bottom) / 2}) rotate(-90)" text-anchor="middle" fill="var(--fg)">${esc(metricLabel)}</text>`);
    for (const s of series) {
      const d = s.points.map((p, i) => (i ? "L" : "M") + sx(p[0]).toFixed(1) + " " + sy(p[1]).toFixed(1)).join(" ");
      out.push(`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""}/>`);
      for (const p of s.points) {
        out.push(`<circle cx="${sx(p[0]).toFixed(1)}" cy="${sy(p[1]).toFixed(1)}" r="4" fill="${s.color}"><title>${esc(s.label)}, ctx ${p[0]}: ${format(p[1])} (${esc(p[2])})</title></circle>`);
      }
    }
    out.push("</svg>");
    return out.join("\n") + legend(series.map(s => ({ label: s.label, color: s.color, dash: s.dash })));
  }

  function legend(items) {
    return '<ul class="legend">' + items.map(i =>
      `<li><svg width="26" height="10" aria-hidden="true"><line x1="0" x2="26" y1="5" y2="5" stroke="${i.color}" stroke-width="3"${i.dash ? ` stroke-dasharray="${i.dash}"` : ""}/></svg> ${esc(i.label)}</li>`).join("") + "</ul>";
  }

  // Horizontal bars: one group per label, one bar per engine family.
  function barChart(groups, metricLabel) {
    if (!groups.length) return '<p class="note">No row matches these filters.</p>';
    const left = 300, right = 70, top = 10, bar = 14, gap = 3, pad = 12;
    const hi = Math.max(...groups.flatMap(g => g.bars.map(b => b.v))) * 1.02;
    const rowH = g => g.bars.length * (bar + gap) + pad;
    const h = top + groups.reduce((n, g) => n + rowH(g), 0) + 28;
    const out = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${h}" width="100%" role="img" ${FONT} font-size="12">`];
    let y = top;
    const fams = new Map();
    for (const g of groups) {
      const label = g.label.length > 44 ? g.label.slice(0, 43) + "..." : g.label;
      out.push(`<text x="${left - 8}" y="${y + bar}" text-anchor="end" fill="var(--fg)"><title>${esc(g.label)}</title>${esc(label)}</text>`);
      for (const b of g.bars) {
        const w = (W - left - right) * b.v / hi;
        fams.set(b.fam, b.color);
        out.push(`<rect x="${left}" y="${y}" width="${Math.max(w, 1).toFixed(1)}" height="${bar}" fill="${b.color}"><title>${esc(b.engine)}: ${format(b.v)} (${esc(b.date)})</title></rect>`,
          `<text x="${left + w + 5}" y="${y + bar - 3}" fill="var(--muted)">${format(b.v)}</text>`);
        y += bar + gap;
      }
      y += pad;
    }
    out.push(`<text x="${left}" y="${h - 6}" fill="var(--muted)">${esc(metricLabel)}</text></svg>`);
    return out.join("\n") + legend([...fams.entries()].map(([label, color]) => ({ label, color })));
  }

  const api = { METRICS, family, value, hardwareLabel, select, newest, contextSeries, barGroups, ticks, logTicks, lineChart, barChart, format };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Charts = api;

  // ---- the page ----------------------------------------------------------------------------
  if (typeof document === "undefined") return;
  const $ = id => document.getElementById(id);
  const el = (tag, text, attrs) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; for (const k in (attrs || {})) n.setAttribute(k, attrs[k]); return n; };
  let rows = [];

  function options(id, values, keep) {
    const sel = $(id), was = keep ? sel.value : "";
    sel.replaceChildren(...values.map(v => { const o = el("option", v.label || v); o.value = v.value !== undefined ? v.value : v; return o; }));
    if (was && values.some(v => (v.value !== undefined ? v.value : v) === was)) sel.value = was;
  }

  function checks(id, items, on) {
    const box = $(id);
    box.replaceChildren(...items.map(it => {
      const lab = el("label"), cb = el("input", undefined, { type: "checkbox", value: it.value });
      cb.checked = on(it); cb.addEventListener("change", draw);
      lab.append(cb, " " + it.label); return lab;
    }));
  }
  const checked = id => new Set([...$(id).querySelectorAll("input:checked")].map(c => c.value));

  function draw() {
    const view = $("view").value, metric = $("metric").value, half = $("half").value;
    $("half-row").style.display = METRICS[metric].half ? "" : "none";
    for (const g of ["ctx-only", "models-only", "hw-only"]) $(g).style.display = "none";
    const f = { prompt: $("prompt").value, mode: $("mode").value, device: $("device").value, engines: checked("engines") };
    let html;
    if (view === "ctx") {
      $("ctx-only").style.display = "";
      f.model = $("model").value.trim(); f.hw = checked("hw");
      html = f.model ? lineChart(contextSeries(rows, f, metric, half), METRICS[metric].label, $("log").checked)
                     : '<p class="note">Pick a model.</p>';
    } else if (view === "models") {
      $("models-only").style.display = "";
      f.hw = new Set([$("hw1").value]); f.ctx = $("ctx").value;
      html = barChart(barGroups(rows, f, metric, half, r => r.model, 40), METRICS[metric].label);
    } else {
      $("hw-only").style.display = "";
      f.model = $("model2").value.trim(); f.ctx = $("ctx2").value;
      html = f.model ? barChart(barGroups(rows, f, metric, half, hardwareLabel, 40), METRICS[metric].label)
                     : '<p class="note">Pick a model.</p>';
    }
    $("chart").innerHTML = html;
    location.hash = new URLSearchParams({ view, metric, half, prompt: f.prompt, mode: f.mode, device: f.device,
      model: view === "hw" ? $("model2").value : $("model").value, hw1: $("hw1").value, ctx: $("ctx").value }).toString();
  }

  fetch("index.json").then(r => r.json()).then(data => {
    rows = data;
    const uniq = key => [...new Set(rows.map(r => r[key]))].sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));
    const hws = [...new Map(rows.map(r => [r.hw + "/" + r.backend, hardwareLabel(r)])).entries()]
      .map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
    options("view", [{ value: "ctx", label: "One model across context sizes" }, { value: "models", label: "All models on one hardware" }, { value: "hw", label: "One model across hardware" }]);
    options("metric", Object.entries(METRICS).map(([value, m]) => ({ value, label: m.label })));
    options("half", [{ value: "warm", label: "warm (median of later requests)" }, { value: "cold", label: "cold (first request)" }]);
    options("prompt", uniq("prompt")); options("mode", uniq("mode")); options("device", uniq("device"));
    options("ctx", uniq("ctx")); options("ctx2", uniq("ctx"));
    options("hw1", hws);
    checks("engines", [...new Set(rows.map(r => family(r.engine)))].sort().map(v => ({ value: v, label: v })), () => true);
    checks("hw", hws, () => true);
    $("models").replaceChildren(...uniq("model").map(m => { const o = el("option"); o.value = m; return o; }));
    const p = new URLSearchParams(location.hash.slice(1));
    for (const [id, key] of [["view", "view"], ["metric", "metric"], ["half", "half"], ["prompt", "prompt"], ["mode", "mode"], ["device", "device"], ["hw1", "hw1"], ["ctx", "ctx"]]) {
      if (p.get(key)) $(id).value = p.get(key);
    }
    if (p.get("model")) { $("model").value = p.get("model"); $("model2").value = p.get("model"); }
    else { const first = rows.find(r => family(r.engine) === "loken" && r.m && r.m.decode); if (first) { $("model").value = first.model; $("model2").value = first.model; } }
    for (const id of ["view", "metric", "half", "prompt", "mode", "device", "ctx", "ctx2", "hw1", "model", "model2", "log"]) $(id).addEventListener("input", draw);
    draw();
  });
})(typeof window !== "undefined" ? window : globalThis);
