# benchmarks

The measurement campaign of loken.
It measures loken, ollama and vLLM on the same machine, the same prompts and the same clock, and publishes every run that a machine shares.

> [!NOTE]
> A row of the results site comes from a record that passed every check of the campaign.
> A record names no person and no machine.
> The cells where loken is slower are published with the others.

[Open the results](https://loken-ai.github.io/benchmarks/results/): 1 page per hardware configuration, charts of a rate and a search over every row.

## Run it

```sh
git clone https://github.com/loken-ai/benchmarks && cd benchmarks
cp bench.toml.example bench.toml
scripts/bench
scripts/bench run
```

`scripts/bench` prints the cells a campaign would measure and changes nothing.
`scripts/bench run` measures them and files 1 record per cell.

## What the campaign claims

A Delta compares loken with the best other engine of the same cell, on the same machine, the same prompt and the same number of generated tokens.
Each claim holds inside 1 cell, under the protocol of [the method](../METHOD.md).

The campaign claims no more than that:

- The 131072 window is a reservation, and no prompt fills it.
  That column compares 2 policies of memory allocation, not 2 engines at a full context.
- `GPU` separates the cards from the host, not 1 card from 2.
- A row of an engine that answered in a loop publishes no rate, whichever engine it is.
- A rate over fewer generated tokens than its peer gets no Delta.
- 2 records compare only inside 1 [equivalence class](concepts.md#equivalence-class).

## How to read the site

The results site is at <https://loken-ai.github.io/benchmarks/results/>.
CI rebuilds it from the records on every push to `main`.

| Page | Shows |
|---|---|
| [Hardware](https://loken-ai.github.io/benchmarks/results/) | 1 card per hardware configuration, with its backends, its card memory, the runs, the rows, the confirmed records and the hosts. A bar counts the compared cells where loken decodes faster in green, and slower in red |
| A hardware page | the cards, the host and the software of the configuration, then 1 table of results for each backend loken answered on |
| [Charts](https://loken-ai.github.io/benchmarks/results/charts.html) | 1 rate of 1 model across context sizes, of every model on 1 hardware, or of 1 model across hardware |
| [Search](https://loken-ai.github.io/benchmarks/results/search.html) | every row of every hardware, filtered by words, hardware, engine, device, mode, prompt and context, with a CSV download |

[Read a results table](../reference/results-table.md) gives each column and each mark.

## What it does

<!-- site: widget table id=benchmarks-overview-capabilities -->
| Capability | Interface | State |
|---|---|---|
| Plan a campaign without side effect | `scripts/bench` | Runs |
| Measure text and vision against ollama and vLLM | `scripts/bench run` | Runs |
| Measure image generation, speech synthesis and audio generation | `scripts/bench run`, loken alone | Runs, figures kept in the records |
| Measure speech recognition, against vLLM on a safetensors checkpoint | `scripts/bench run` | Runs, figures kept in the records |
| Sweep the whole matrix of windows, prompts, modes and devices | `FULL=1` | Runs |
| Measure through Vulkan or OpenCL | `BACKEND` | Runs |
| Measure every card of a machine with NVIDIA and AMD cards | `GPU_VENDOR` | Runs |
| Measure a cluster | `[cluster]` in `bench.toml` | Runs |
| Energy of each request, cards and processor | `scripts/enable-energy.sh` | Runs where the counters are readable |
| File records without personal data | `scripts/add.py` | Runs |
| Check records | `scripts/check.py`, and on every pull request | Runs |
| Confirm a record by a second host | automatic | Runs |
| Build the results site | `scripts/site.py`, and on every push to `main` | Runs |
<!-- site: end -->
