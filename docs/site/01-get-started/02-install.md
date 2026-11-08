# Install

The campaign runs from a clone of the repository.
It measures with a `lokend` from loken and a `lokprof` from lokprof, both built from source.

loken and lokprof publish no prebuilt archive.
The repository holds no copy of either.

## Hardware and system

| Need | For |
|---|---|
| Linux on x86_64 | the ollama release the campaign installs is the Linux amd64 build |
| An NVIDIA card with `nvidia-smi`, an AMD card of 4 GiB or more, or both | the GPU sweeps |
| The host processor | the CPU sweeps of the whole matrix |
| `sudo`, once per machine | the rule that makes the processor energy readable |

An AMD display device with less than 4 GiB of its own memory is not measured, nor exposed to an engine.

## Before you start

<!-- site: widget checklist id=benchmarks-install-prereq -->
- [ ] Python 3.11 or later, with no package beyond the standard library.
- [ ] `git` and `curl`.
- [ ] `uv`, `tar` and `zstd`, which install vLLM and ollama at the start of a run.
- [ ] Network access to PyPI and to the GitHub API at the start of a run.
- [ ] A loken configuration directory whose `config.toml` sets `ollama_models_dir`.
- [ ] The models to measure, in the stores that configuration names.
<!-- site: end -->

## Get it

<!-- site: widget tabs group=benchmarks-use id=benchmarks-install-method -->
### Run a campaign

```sh
git clone https://github.com/loken-ai/benchmarks
cd benchmarks
cp bench.toml.example bench.toml
```

Build `lokend` as [loken's Install page](https://github.com/loken-ai/loken/blob/main/docs/start/install.md) says.
Build `lokprof` from its repository:

```sh
git clone https://github.com/loken-ai/lokprof
cd lokprof
cargo build --release
```

The binary is `target/release/lokprof`.
Name both binaries in `bench.toml`, see [Settings](../03-reference/04-settings.md).

### Check records and build the site

```sh
git clone https://github.com/loken-ai/benchmarks
cd benchmarks
```

Checking records and building the site need Python 3.11 and nothing else.
<!-- site: end -->

## Variants

| Variant | Also needs |
|---|---|
| `BACKEND=vulkan` | `vulkaninfo`. ollama is measured only when its release has a Vulkan backend |
| A cluster | `ssh` to each node, and Python 3 on each node |
| A memory limit for each engine | `systemd-run --user --scope`, used when it works |

## Verify

<!-- site: widget checklist id=benchmarks-install-verify -->
- [ ] `scripts/bench --help` prints the usage of the driver.
- [ ] `scripts/bench` prints the stores, the address of loken and the models it serves.
- [ ] `scripts/enable-energy.sh --check` reports which energy domains of the machine are measurable.
<!-- site: end -->

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `bench: python3 is required` or `bench: curl is required` | The tool is not on the `PATH`. | Install it. |
| `bench: no bench.toml at ...` | The settings file is missing. | `cp bench.toml.example bench.toml` and fill it in. |
| `loken.binary '...' is not an executable` | `bench.toml` names no `lokend`. | Set `binary` under `[loken]` to the `lokend` you built. |
| `lokprof.binary '...' is not an executable` | `bench.toml` names no `lokprof`. | Set `binary` under `[lokprof]`. |
| `loken.config_dir '...' holds no config.toml` | The configuration directory has no `config.toml`. | Point `config_dir` at the directory that holds it. |
| `... has no ollama_models_dir` | loken's configuration names no ollama store. | Set `ollama_models_dir` in that `config.toml`. |
| `uv is required`, `tar is required` or `zstd is required` | A tool that installs the engines is missing. | Install it. |
