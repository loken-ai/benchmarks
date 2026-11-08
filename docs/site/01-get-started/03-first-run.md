# First run

Measure 1 model in the fast pass, check its record and see it on a local copy of the results site.

## Before you start

<!-- site: widget checklist id=benchmarks-first-run-prereq -->
- [ ] The repository is cloned and `lokend` and `lokprof` are built, see [Install](02-install.md).
- [ ] loken's configuration serves at least 1 model.
- [ ] The cards are idle: no engine holds memory on them.
<!-- site: end -->

## Run it

<!-- site: widget steps id=benchmarks-first-run-steps -->
1. Name the builds in `bench.toml`.
   A relative path follows [Settings](../03-reference/04-settings.md#benchtoml).

   ```toml
   [loken]
   binary = "loken/lokend"
   config_dir = "loken"

   [lokprof]
   binary = "lokprof/lokprof"
   ```

2. Print the plan.
   The driver asks loken for its catalogue, and starts the `lokend` of `bench.toml` when none answers.

   ```sh
   scripts/bench
   ```

3. Make the energy of the machine readable.
   The command asks for `sudo` once, then reports each domain.

   ```sh
   scripts/enable-energy.sh
   ```

4. Measure 1 model in the fast pass.
   The fast pass takes the first value of each axis: the GPU, the 4096 window, the 100 token prompt, streamed.

   ```sh
   BENCH_ONLY="qwen3:0.6b" scripts/bench run
   ```

5. Check the records the run filed.

   ```sh
   scripts/check.py runs/*/*.json
   ```

6. Build the site and serve it.
   The search page reads its rows over HTTP, which a `file://` page cannot.

   ```sh
   scripts/site.py
   python3 -m http.server -d site
   ```

7. Open `http://localhost:8000/`.
<!-- site: end -->

## Expected result

<!-- site: widget replay id=benchmarks-first-run-replay -->
```
$ scripts/bench
store (ollama):  <ollama store>
store (hf):      <none>
loken:           http://127.0.0.1:11435
models:          1 (from loken)

model                                     modality  format        engines           note
----------------------------------------  --------  ------------  ----------------  ----
qwen3:0.6b                                text      gguf          ollama loken

context sizes (FULL=1): 4096 131072
a context above a model's declared window is skipped
(plan only; run with: scripts/bench run)
$ BENCH_ONLY="qwen3:0.6b" scripts/bench run
engines (bench compartment):
  ollama:  <version>  [<ollama binary>]
  vLLM:    <version>  [<vLLM environment>]
thermal floor for this campaign: <temperature>C (idle, nothing resident)
########## GPU ctx=4096 prompts=100 stream=1
===== qwen3:0.6b ctx=4096 prompt=100 stream=1 device=gpu modality=text engines=[ollama loken]
<the last 4 lines of the measurement>
  goal cold: <won>/<compared> cells win on BOTH axes   (<counts>)
  goal warm: <won>/<compared> cells win on BOTH axes   (<counts>)
campaign done
$ scripts/check.py runs/*/*.json
<n> record(s) accepted, 0 refused
$ scripts/site.py
wrote <n> hardware page(s), <rows> row(s) in index.json, <n> record(s)
```
<!-- site: end -->

The first run installs vLLM and ollama into a directory of the campaign, and prints a `provisioning` line for each.
The record of the cell lands under `runs/<hardware_id>/<run_id>.json`, see [Record](../03-reference/02-record.md).

The local site holds every record of the clone.
The rows of the cell are on the page of the hardware id of the machine.
A model in the GGUF format gets a vLLM row marked `not run: paired with safetensors weights only`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `lokend did not answer at <url>` or `lokend stopped at start` | The `lokend` of `bench.toml` failed to start. | Read `results/lokend-catalogue.log`. |
| `loken returned no catalogue at <url>/api/tags` | loken serves no model. | Pull a model with loken, then plan again. |
| `cannot read the latest vLLM release` or `cannot read the latest ollama release` | PyPI or the GitHub API cannot be reached. | Restore the network access. A campaign measures the latest engines only. |
| `cards are still working (<n>% busy, <m> MiB held)` | An NVIDIA card is more than 5% busy or holds more than 600 MiB. | Stop what holds the card. |
| `an AMD card is still working` | An AMD card is more than 5% busy. | Stop what holds the card. |
| `warning: some energy domain of this machine is not measurable` | A counter is readable by root only. | `scripts/enable-energy.sh`, then run again. The records of this run hold no energy. |
| `cell interrupted after <n>s` | The cell ran longer than `CELL_CAP`. | Raise `CELL_CAP`, or leave the model out. The cell has no result. |
| `(the record of <model> was not filed: ...)` | The record failed a check. | Run the `scripts/add.py` command it prints to see the reasons. |
