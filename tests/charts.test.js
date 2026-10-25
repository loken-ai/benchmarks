// The chart functions of web/charts.js, on a few rows shaped like the ones of index.json.
//   node --test tests/*.test.js
const test = require("node:test");
const assert = require("node:assert");
const C = require("../web/charts.js");

function row(over) {
  return Object.assign({
    hw: "h1", backend: "cuda", cards: ["Card A"], model: "m1", ctx: "4096", prompt: "short", mode: "stream",
    device: "GPU", engine: "loken", date: "2026-10-20", run: "aaaa",
    m: { decode: [100, 110], prefill: [900, 950], ttft: [20, 15], e2e: [1000], jtok: [0.5], jreq: [64], tokens: [128] },
  }, over);
}

test("the family of an engine is its first word, and a drafter arm is its own", () => {
  assert.strictEqual(C.family("Ollama 0.35.1"), "Ollama");
  assert.strictEqual(C.family("vLLM 0.32.0"), "vLLM");
  assert.strictEqual(C.family("loken"), "loken");
  assert.strictEqual(C.family("loken + llama3.2:1b"), "loken+");
});

test("a metric reads its cold or warm half, or its single figure", () => {
  const r = row({});
  assert.strictEqual(C.value(r, "decode", "warm"), 110);
  assert.strictEqual(C.value(r, "decode", "cold"), 100);
  assert.strictEqual(C.value(r, "jtok", "warm"), 0.5);
  assert.strictEqual(C.value(row({ m: { decode: [100, null] } }), "decode", "warm"), null);
  assert.strictEqual(C.value(row({ m: {} }), "decode", "warm"), null);
});

test("a series has one point per context size, the newest run winning", () => {
  const rows = [
    row({ ctx: "4096" }), row({ ctx: "8192", m: { decode: [90, 95] } }),
    row({ ctx: "4096", date: "2026-10-22", run: "bbbb", m: { decode: [120, 130] } }),
    row({ ctx: "16384", m: { decode: [null, null] } }),
  ];
  const series = C.contextSeries(rows, { model: "m1" }, "decode", "warm");
  assert.strictEqual(series.length, 1);
  assert.deepStrictEqual(series[0].points.map(p => [p[0], p[1]]), [[4096, 130], [8192, 95]]);
});

test("one line per hardware and engine, and the engine filter applies", () => {
  const rows = [row({}), row({ engine: "Ollama 0.35.1" }), row({ hw: "h2", cards: ["Card B"] })];
  assert.strictEqual(C.contextSeries(rows, { model: "m1" }, "decode", "warm").length, 3);
  assert.strictEqual(C.contextSeries(rows, { model: "m1", engines: new Set(["loken"]) }, "decode", "warm").length, 2);
  assert.strictEqual(C.contextSeries(rows, { model: "m1", hw: new Set(["h2/cuda"]) }, "decode", "warm").length, 1);
});

test("bars are grouped, ordered by their best figure and limited", () => {
  const rows = [
    row({ model: "slow", m: { decode: [10, 10] } }), row({ model: "slow", engine: "Ollama 0.35.1", m: { decode: [8, 8] } }),
    row({ model: "fast", m: { decode: [200, 210] } }),
  ];
  const groups = C.barGroups(rows, { ctx: "4096" }, "decode", "warm", r => r.model, 0);
  assert.deepStrictEqual(groups.map(g => g.label), ["fast", "slow"]);
  assert.deepStrictEqual(groups[1].bars.map(b => b.fam), ["loken", "Ollama"]);
  assert.strictEqual(C.barGroups(rows, { ctx: "4096" }, "decode", "warm", r => r.model, 1).length, 1);
});

test("ticks are round and span the range", () => {
  const t = C.ticks(0, 137, 6);
  assert.strictEqual(t[0], 0);
  assert.ok(t[t.length - 1] <= 137 && t[t.length - 1] >= 100);
  assert.ok(t.every(v => Number.isFinite(v)));
  const l = C.logTicks(3, 700);
  assert.deepStrictEqual(l, [5, 10, 20, 50, 100, 200, 500]);
});

test("a line chart draws a path and a point per figure and escapes the labels", () => {
  const series = C.contextSeries([row({ ctx: "4096" }), row({ ctx: "8192" }), row({ cards: ["A <b> & B"] , hw: "h3" })], { model: "m1" }, "decode", "warm");
  const svg = C.lineChart(series, "Decode tok/s", false);
  assert.ok(svg.startsWith("<svg"));
  assert.strictEqual((svg.match(/<path /g) || []).length, 2);
  assert.ok(!svg.includes("<b>"));
  assert.ok(svg.includes("&lt;b&gt;"));
});

test("an empty selection says so instead of drawing", () => {
  assert.match(C.lineChart([], "x", false), /No row matches/);
  assert.match(C.barChart([], "x"), /No row matches/);
});

test("a bar chart has a bar per engine and a legend", () => {
  const groups = C.barGroups([row({}), row({ engine: "Ollama 0.35.1" })], {}, "decode", "warm", r => r.model, 0);
  const svg = C.barChart(groups, "Decode tok/s");
  assert.strictEqual((svg.match(/<rect /g) || []).length, 2);
  assert.ok(svg.includes('class="legend"'));
});
