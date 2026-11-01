# Record

A record is a JSON object of the loken schema, written by lokprof and filed by the campaign.
It holds the cells of 1 run, the protocol, the engines and the machine.

## Where it is filed

```
runs/<hardware_id>/<run_id>.json
```

| Part | Value |
|---|---|
| `hardware_id` | the hardware id of the `machine` block, 16 hexadecimal digits |
| `run_id` | the first 16 hexadecimal digits of the SHA-256 of the record, serialised with sorted keys, no spaces and UTF-8 text |

A rerun is a new file.
The same record filed twice is 1 file.
An edited record no longer matches its name.

## Top level

<!-- site: widget table id=benchmarks-record-top -->
| Field | Holds |
|---|---|
| `schema` | `loken/2`. The checks accept the major version 2 |
| `timestamp` | the day of the run in UTC, as `YYYY-MM-DD` |
| `engine_build` | the modification time of the `lokend` measured, in seconds since the epoch |
| `config` | the options lokprof ran with: `iterations`, `warmup`, `max_tokens`, `streaming`, `unique_prompt`, `num_ctx`, `num_gpu`, `prompts`, `models` and the energy options |
| `protocol` | the protocol of the run, see below |
| `machine` | the description of the machine, see below |
| `subjects` | for each engine, what it said of itself under `says` (`version`, `commit`), the devices it reported under `devices`, and its address |
| `results` | the cells, 1 object per engine and cell |
| `ollama_version`, `vllm_version` | the version of each peer engine that produced a cell of the record |
| `idle_energy_baseline` | the draw of the machine at rest, or null |
<!-- site: end -->

A run with `num_gpu` 0 in `config` is a CPU run: the engines had the host alone.

## Protocol

<!-- site: widget table id=benchmarks-record-protocol -->
| Field | The campaign's value |
|---|---|
| `iterations` | 3 |
| `warmup` | 0 |
| `max_tokens` | 128 |
| `unique_prompt` | true: each iteration gets a prompt no engine has seen |
| `streaming` | true or false |
| `replayed_prompt_removed` | true on a record that replayed 1 prompt and dropped what the prompt cache changes from its later iterations |
| `engines_seen`, `gpu_temps_c_at_start`, `cards_by_uuid`, `prefix_reuse_offered` | what lokprof saw at the start of the run |
<!-- site: end -->

A record whose iterations replayed 1 prompt passes the `unique_prompt` check only when `replayed_prompt_removed` is true.
Its later iterations then hold no `prompt_tok_s`, `ttft_ms`, `e2e_latency_ms` or `wall_clock_ms`.

## Machine

<!-- site: widget table id=benchmarks-record-machine -->
| Field | Holds |
|---|---|
| `host_id` | a one-way hash of the machine id of the operating system |
| `hardware_id` | a one-way hash of the cards, the processor, its threads and the memory |
| `cpu`, `threads`, `sockets` | the processor, its hardware threads and its sockets |
| `cpu_flags` | the instruction sets host kernels choose a path by, among AVX2, FMA, BMI2, F16C, AVX-512 and AMX |
| `ram_gib` | the memory, in GiB |
| `os`, `kernel` | the distribution and the kernel |
| `driver` | the NVIDIA driver |
| `gpus` | 1 object per card |
| `nodes` | for a cluster, 1 object per node, this machine first |
| `attested` | on a converted old report, who vouched for the machine block |
<!-- site: end -->

| Card field | Holds |
|---|---|
| `index` | the place of the card |
| `name`, `vendor` | the name and the maker. `name` is required |
| `arch` | the architecture, such as `sm_89` or `gfx1201` |
| `vram_mib` | the memory, in MiB. Required |
| `power_cap_w` | the power cap, in watts |
| `pcie_gen`, `pcie_width` | the generation and the width of the PCIe link |

A node holds `cpu`, `threads`, `sockets`, `cpu_flags`, `ram_gib`, `os`, `kernel`, `driver` and `gpus`.
A fact the run could not read is left out.
A CPU run lists no card and no driver.

### Hardware id

The hardware id hashes, with SHA-256, each card as name, memory and power cap, the cards sorted, then the processor, the threads and the memory.
It keeps 16 hexadecimal digits.
The serials, the driver and the system stay out of it, so 2 machines built alike share it.

A cluster's hardware id hashes the sorted ids of its nodes.
The same machines in another order are the same cluster, and 1 node changed is another.

## Cell

<!-- site: widget table id=benchmarks-record-cell -->
| Field | Holds |
|---|---|
| `target` | the engine: `LOKEN`, `Ollama` or `vLLM` |
| `model` | the model name |
| `num_ctx` | the context window asked for, in tokens |
| `prompt` | the prompt, named by its size in tokens |
| `prompt_chars` | the characters of the prompt sent |
| `iterations` | 1 object per iteration |
| `iteration_errors` | the error of each iteration that failed |
| `stats` | the aggregates of the iterations, each with `count`, `mean`, `min`, `max`, `p50`, `p95`, `stddev` and `unit` |
| `coherence_pass` | whether lokprof found the answer coherent |
| `first_response_preview` | the start of the first answer |
| `load_time_ms` | the load time of the model |
| `model_fingerprint` | the size, the quantisation and the day of the model file |
| `load_error` | the reason a cell has no measurement, or null |
<!-- site: end -->

An error cell holds a `load_error` and no iteration.

| Iteration field | Holds |
|---|---|
| `prompt_tokens`, `ttft_ms` | the prompt tokens and the time to first token, measured by lokprof |
| `completion_tok_s` | the decode rate seen by the client |
| `server_decode_tok_s` | the decode rate the server reports of itself |
| `tokens_generated` | the tokens of the answer |
| `e2e_latency_ms`, `wall_clock_ms` | the duration of the request |
| `prompt_tok_s` | the prefill rate the engine reports of itself |
| `energy` | the energy of the request, see below |
| `inter_token_latencies_ms` | the gap between consecutive tokens |
| `gpu_samples`, `host_sample` | the draw and the load of the cards and the host during the request |
| `degenerate`, `response_preview` | whether the answer loops, and its start |

## Energy

An `energy` block states `complete`, `domains_counted` and `missing_domains`.

| `complete` | Rule |
|---|---|
| true | `domains_counted` includes `cpu_pkg`, and `missing_domains` is empty |
| false | every figure is null: `energy_j`, `gpu_energy_j`, `cpu_pkg_energy_j`, `dram_energy_j`, `j_per_tok`, `wh_per_tok`, `gco2_per_tok`, `gpu_decode_j`, `cpu_pkg_decode_j`, `dram_decode_j`, `decode_energy_j`, `j_per_decode_tok` |

A domain that could not be measured is a missing value, never a partial total.

## Checks

`scripts/check.py` and every pull request refuse a record for each of these reasons.

<!-- site: widget table id=benchmarks-record-checks -->
| Check | Refused when |
|---|---|
| readable | the file is not a JSON object |
| schema | the `schema` major is not 2 |
| cells | `results` is empty |
| machine | the record has no `machine` block |
| name | the file name is not the `run_id` of the content |
| hardware | the folder is not the hardware id of the `machine` block, or the block states another one |
| cards | a card states no `name` or no `vram_mib` |
| anonymity | a date has a time of day, a CPU run names a card, the machine block holds a field outside the list, or a string names a path, a private address or a mailbox |
| energy | an energy block does not say whether it is complete, calls itself complete without the processor or a card, or stores figures while incomplete |
| prompt | a cell names a prompt other than `100`, `1000` and `10000`, or its `prompt_chars` differs from the length of that prompt |
| protocol | a field of the protocol differs from the campaign's value. A record without a protocol must hold only error cells |
| duplicate | the same `run_id` already sits elsewhere under `runs/` |
<!-- site: end -->

A string names a path when it holds `/home/`, `/Users/`, `/mnt/` or a drive letter.
It names a private address when it holds an address of one of the 3 private ranges of IPv4.

## Status

| Status | Meaning |
|---|---|
| `submitted` | the record passed the checks |
| `confirmed` | another host measured the same equivalence class on the same hardware id |

The equivalence class is the schema major, the protocol profile and the flags `streaming`, `max_tokens`, `iterations`, `warmup` and `engines_alone`, the machine with its kernel and its driver, and each engine with its commit or version and its backend.
A record without a `host_id` confirms nothing.
