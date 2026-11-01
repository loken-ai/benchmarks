# Settings

A campaign reads `bench.toml`, the configuration of loken it names, and environment variables.
`bench.toml` stays out of git.

## bench.toml

A relative path is read from the directory of `bench.toml`.

<!-- site: widget table id=benchmarks-settings-file -->
| Key | Holds | Default |
|---|---|---|
| `[loken] binary` | the `lokend` measured. Required, executable | none |
| `[loken] config_dir` | the directory whose `config.toml` `lokend` starts with. Required | none |
| `[loken] url` | the address `lokend` answers on | `http://127.0.0.1:11435` |
| `[lokprof] binary` | the `lokprof` that measures. Required, executable | none |
| `[cluster] nodes` | the `ssh` targets of the other nodes of a cluster | none |
<!-- site: end -->

## loken's configuration

The driver reads 2 keys of the `config.toml` in `config_dir`.

| Key | Use |
|---|---|
| `ollama_models_dir` | the store ollama reads, the same as loken's. Required |
| `huggingface_models_dir` | the store vLLM reads, the same as loken's |

## Environment

<!-- site: widget table id=benchmarks-settings-env -->
| Variable | Effect | Default |
|---|---|---|
| `FULL` | `1` sweeps the whole matrix. Otherwise the run is the fast pass | unset |
| `BENCH_ONLY` | measures only the models named, separated by spaces | every model |
| `CELL_CAP` | stops a cell after this many seconds, and reports it interrupted | 7200 |
| `BACKEND` | `native`, `vulkan` or `opencl`: the runtime the cards are measured through | `native` |
| `GPU_VENDOR` | `nvidia`, `amd` or `all`: whose cards every engine sees | detected: `all` on a machine with both |
| `VULKAN_CARD` | a part of the name of the Vulkan device to measure | `NVIDIA`, `AMD` or `Intel`, by `GPU_VENDOR` |
| `KEEP_EARLIER_BUILDS` | `1` keeps the complete cells of an earlier `lokend` and measures again the others | unset |
| `PIN` | the index of the only card the GPU cells may use | unset: every card |
| `GPU_IDLE_C` | the idle temperature of the cards, in degrees Celsius, the thermal gate waits for | read at the start of the run |
| `ASR_AUDIO` | the recording a speech recognition cell transcribes | the recording of the repository |
| `ASR_REFERENCE` | the transcript its word error rate is read against | the transcript of the repository |
| `MAXTOK` | the cap of generated tokens | 128 |
| `OLLAMA_PORT` | the port ollama serves on | 11434 |
<!-- site: end -->

A record measured with another `MAXTOK` fails the protocol check and cannot be shared.

## Commands

| Command | Does |
|---|---|
| `scripts/bench` or `scripts/bench --plan` | prints the stores, the models, the engines of each model and the windows, and changes nothing |
| `scripts/bench run` | installs the engines and measures the cells |
| `scripts/bench --help` | prints the usage |
| `scripts/add.py <file>...` | files records under `runs/`, without personal data, and prints the refused ones with their reasons |
| `scripts/check.py <file>...` | checks records, prints 1 line per refused record and exits 1 when one is refused |
| `scripts/site.py` | writes the results site into `site/` from the records that pass the checks |
| `scripts/enable-energy.sh` | makes the energy counters of the machine readable, with `sudo`, then reports |
| `scripts/enable-energy.sh --check` | reports which energy domains are measurable, without root. Exits 1 when one is not |
