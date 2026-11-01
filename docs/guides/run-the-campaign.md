# Run the campaign

Measure every model loken serves across the whole matrix, and file a record for each cell.

## Before you start

<!-- site: widget checklist id=benchmarks-run-prereq -->
- [ ] [First run](../start/first-run.md) works on this machine.
- [ ] `scripts/enable-energy.sh --check` reports every domain measurable.
- [ ] Nothing else uses the cards or the processor for the hours the campaign takes.
- [ ] Disk space for the vLLM environment, and for any safetensors checkpoint missing from the Hugging Face store.
  vLLM reads the store loken reads, and downloads a checkpoint it lacks.
<!-- site: end -->

## Smallest configuration

```toml
[loken]
binary = "loken/lokend"
config_dir = "loken"

[lokprof]
binary = "lokprof/lokprof"
```

The models come from loken's catalogue, and the axes from [the matrix](../reference/matrix.md).
The store paths come from the `config.toml` in `config_dir`: `ollama_models_dir` and `huggingface_models_dir`.

## Run it

<!-- site: widget steps id=benchmarks-run-steps -->
1. Print the plan and read the engines of each model.
   A GGUF model runs on loken and ollama, a safetensors model on loken and vLLM.

   ```sh
   scripts/bench
   ```

2. Sweep the whole matrix.
   The driver takes each device, window, prompt and mode in that order, and every model once in each.

   ```sh
   FULL=1 scripts/bench run
   ```

3. Check the records the run filed.

   ```sh
   scripts/check.py runs/*/*.json
   ```
<!-- site: end -->

A stopped campaign resumes where it was.
The driver keeps a cell measured by the same `lokend` and the same engine versions, and measures the others.

## Expected result

Each sweep of the matrix starts with a `##########` line that names its device, window, prompt and mode.

```
########## GPU ctx=4096 prompts=100 stream=1
ERROR cell: <model> (<capability>) - <reason>
===== <model> ctx=4096 prompt=100 stream=1 device=gpu modality=text engines=[ollama loken]
<the last 4 lines of the measurement>
  goal cold: <won>/<compared> cells win on BOTH axes   (<counts>)
  goal warm: <won>/<compared> cells win on BOTH axes   (<counts>)
kept <model> ctx=4096 100 stream=1 gpu (already measured, versions current)
...
########## GPU ctx=4096 prompts=10000 stream=1
skipped <model> ctx=4096: a prompt of 10000 tokens does not fit
...
########## GPU ctx=131072 prompts=100 stream=1
skipped <model> ctx=131072: the model declares a window of <window>
...
campaign incomplete: <n> cell(s) without a result
campaign done
```

Each cell prints a line `=====` with its model, window, prompt, mode, device and engines.
After each cell, 2 lines `goal cold` and `goal warm` count the compared cells where loken is faster and uses less energy.
A model the campaign cannot measure prints `ERROR cell:` with the reason, once.
A window that cannot hold the prompt, or that is larger than the window the model declares, prints a `skipped` line.
A cell already measured by the same `lokend` and engine versions prints a `kept` line.

The run ends with `campaign done`.
`campaign incomplete: <n> cell(s) without a result` comes before it when a cell produced nothing.

## Variants

<!-- site: widget tabs group=benchmarks-scope id=benchmarks-run-variants -->
### Some models

```sh
BENCH_ONLY="qwen3:8b Qwen/Qwen3-8B" FULL=1 scripts/bench run
```

`BENCH_ONLY` takes model names separated by spaces.

### Another backend

```sh
BACKEND=vulkan scripts/bench run
BACKEND=opencl scripts/bench run
```

A backend run measures the GPU sweep only.
Vulkan measures loken and ollama on the Vulkan device of the card, with the vendor runtimes hidden from both, so neither falls back to CUDA, ROCm or the host.
loken gets the card through `vulkan_devices` in a copy of its configuration, and ollama through `OLLAMA_VULKAN=1`.
An ollama release without a Vulkan backend is not run, and the run says so.

OpenCL measures loken alone, since no reference engine runs a language model through OpenCL.
vLLM runs on neither backend.
The site makes 1 table per backend on the hardware page.

### One vendor

```sh
GPU_VENDOR=nvidia scripts/bench run
```

A machine with NVIDIA and AMD cards runs with `GPU_VENDOR=all` by default, every card exposed to every engine.
`nvidia` or `amd` hides the cards of the other vendor from every engine.
An engine that drives 1 vendor only, such as vLLM, uses the cards of that vendor.

The record lists the cards loken saw, so a machine with both vendors is a hardware id of its own.
ollama gets its ROCm libraries whenever an AMD card is present.

### A cluster

```toml
[cluster]
nodes = ["user@node2", "user@node3"]
```

The driver describes each node over `ssh`.
The record lists every node, this machine first, and its hardware id is the hash of the sorted node ids.

### A corrective build

```sh
KEEP_EARLIER_BUILDS=1 FULL=1 scripts/bench run
```

The run keeps the complete cells of an earlier `lokend`.
It measures again the cells that failed, lost an iteration or are missing.
<!-- site: end -->

[Settings](../reference/settings.md) lists every variable.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `skipped <model> ctx=<n>: the model declares a window of <m>` | The model declares a smaller window than the cell. | None. The cell is outside the model. |
| `skipped <model> ctx=<n>: a prompt of <p> tokens does not fit` | The window cannot hold the prompt and its answer. | None. |
| `ollama left out of <model>: it could not import the model` | ollama could not import the GGUF file of a Hugging Face model. | The cell runs without ollama. The import error is printed above. |
| `ERROR cell: <model> (<capability>)` | No engine of this build serves the model, or lokprof has no clock for its capability. | None. The record keeps the reason. |
| `cell interrupted after <n>s` | The cell ran longer than `CELL_CAP`. | Raise `CELL_CAP`. |
| `BACKEND must be native, vulkan or opencl` | `BACKEND` has another value. | Use 1 of the 3. |
| `no Vulkan GPU matches '<name>'` | `VULKAN_CARD` matches no Vulkan device. | Set `VULKAN_CARD` to a part of the card name. |
| `matrix.toml names the prompt '<p>' and prompts/<p>.txt is missing` | The matrix names a prompt the repository lacks. | Restore the prompt file. |
