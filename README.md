# benchmarks

The measurement campaign of [loken](https://github.com/loken-ai/loken).
It measures loken, ollama and vLLM on the same machine, the same prompts and the same clock, and keeps every run a machine shares.
The results site at <https://loken-ai.github.io/benchmarks/results/> shows them: 1 page per hardware configuration, charts of a rate and a search over every row.

## Quick start

```sh
cp bench.toml.example bench.toml   # name the lokend and the lokprof you built
scripts/bench                      # print the cells a campaign would measure
scripts/bench run                  # measure them and file 1 record per cell
```

The campaign needs Linux, Python 3.11, `curl`, a `lokend` built from [loken](https://github.com/loken-ai/loken) and a `lokprof` built from [lokprof](https://github.com/loken-ai/lokprof).

## State

The campaign runs on NVIDIA and AMD cards, through CUDA, ROCm, Vulkan and OpenCL, and on the host.
It measures text and vision against ollama and vLLM, and image generation, speech synthesis, audio generation and speech recognition.

## Documents

| Document | Holds |
|---|---|
| [Overview](docs/start/overview.md) | how to read the results site, and what the campaign claims |
| [Install](docs/start/install.md) and [First run](docs/start/first-run.md) | from a clone to a first record |
| [Concepts](docs/start/concepts.md) | cell, protocol, record, equivalence class, status |
| [Run the campaign](docs/guides/run-the-campaign.md) and [Share your runs](docs/guides/share-your-runs.md) | the 2 tasks |
| [Method](docs/METHOD.md) | how a cell is measured and compared |
| [Results table](docs/reference/results-table.md), [Record](docs/reference/record.md), [Matrix](docs/reference/matrix.md), [Settings](docs/reference/settings.md) | what is looked up |

## Contributing

Share your runs through a pull request, see [Share your runs](docs/guides/share-your-runs.md).
[CONTRIBUTING.md](CONTRIBUTING.md) covers the code, the tests and the layout of the repository.

## Licence

The code is MIT OR Apache-2.0: see [LICENSE-MIT](LICENSE-MIT) and [LICENSE-APACHE](LICENSE-APACHE).
The records under `runs/` are published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): see [LICENSE-DATA](LICENSE-DATA).
A contributor who opens a pull request agrees to publish their records under it.
The recordings of the speech recognition cells are credited in [NOTICE.md](NOTICE.md).
