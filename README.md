# benchmarks

The bench campaign of [loken](https://github.com/loken-ai/loken): the driver, the matrix, the
protocol that makes a comparison fair, and the runs that every machine which ran it has shared. You
run the campaign with the released builds of loken and
[lokprof](https://github.com/loken-ai/lokprof), file your runs here, and the site shows the
results of every machine, one page per hardware configuration.

## Run the campaign

You need Linux, `python3` and `curl`, a loken release serving the models you want measured, and a
lokprof release. Then:

```sh
cp bench.toml.example bench.toml   # name the lokend and the lokprof of your releases
scripts/bench                      # plan: print the cells a campaign would run
scripts/bench run                  # run it
```

`docs/BENCHMARKING.md` is the procedure: the engines the campaign installs for comparison, the
matrix of context sizes, prompts and devices, the backends (CUDA, ROCm, Vulkan, OpenCL, host) and
the modalities.

## Share your runs

`scripts/bench run` files each cell under `runs/<hardware_id>/<run_id>.json`. To share them:

1. Fork this repository and commit the new files under `runs/`.
2. Open a pull request. The checks below run on every record it adds.

Do not edit a record: its name is the hash of its content. Records taken by other means go through
`scripts/add.py results/*.json`, which files the accepted ones and prints why it refused the others.

## What a record says about your machine

Enough to know what was measured, and nothing that names you or your machine:

- the processor, its threads and sockets, the instruction sets host kernels use, the memory;
- for each card, its name, maker, architecture (such as `sm_89` or `gfx1201`), memory, power cap and
  PCIe link; the kernel, the distribution and the driver;
- for a cluster, the same for every node;
- the day of the run, in UTC, without the time of day;
- two one-way hashes: `host_id` groups the runs of one machine, and `hardware_id` names a
  configuration shared by every machine built the same way.

A card's serial, a host name, a path, a private address and a mailbox never enter a record.
`scripts/add.py` removes what is outside this list and `scripts/check.py` refuses a record that keeps
any of it.

## What CI checks

For each record a pull request adds or changes:

| check | refused when |
|---|---|
| readable | the file is not a JSON object |
| schema | the `schema` major is not one lokprof writes (`loken/2`) |
| cells | `results` is empty |
| machine | the record has no `machine` block |
| name | the file name is not the `run_id` computed from the content |
| hardware | the folder is not the `hardware_id` hashed from the `machine` block, or the block states another one |
| anonymity | a date has a time of day, the machine block holds a field outside the list, or a string names a path, a private address or a mailbox |
| protocol | not the campaign's: 3 iterations, no warm-up, 128 tokens, streaming true or false; a record without a protocol must hold only error cells |
| duplicate | the same `run_id` already sits elsewhere in `runs/` |

Each refused record gets one line naming every reason. Run the same checks locally:

```sh
scripts/check.py runs/<hardware_id>/<run_id>.json
python3 -m unittest discover tests
```

## Statuses

| status | meaning |
|---|---|
| submitted | the record is checked and stands alone |
| confirmed | another host measured the same equivalence class on the same `hardware_id` |

The equivalence class (`scripts/records/classes.py`) is the schema major, the protocol flags, the
machine with its kernel and driver, and each engine with its build and backend. A record without a
`host_id` confirms nothing.

## Build the site

```sh
scripts/site.py
python3 -m http.server -d site
```

Then open `http://localhost:8000/`. The search page reads `index.json`, which a browser does not load
from a `file://` page. When the repository is public, CI publishes `site/` to GitHub Pages on every
push to `main`. Dates are UTC days; a record holds no time of day. A loken row whose record does not
state the loken version is labelled `loken` without a number.

## Layout

| path | what it holds |
|---|---|
| `scripts/bench` | the campaign driver |
| `scripts/engines/` | the isolation protocol (`fair-run.sh`), the card policy and the vLLM launchers |
| `scripts/records/` | the record store, the hardware identity, the equivalence classes and the archive converters |
| `scripts/architecture.py` | describes the machine and its cluster |
| `scripts/add.py`, `scripts/check.py`, `scripts/site.py` | file a run, check it, build the site |
| `scripts/bench_row.py`, `scripts/scoreboard.py`, `scripts/plot-bench.py` | the table rows, the win count and the plot |
| `matrix.toml`, `fixtures/` | the matrix axes and the speech recognition fixtures |
| `bench.toml.example` | the settings a campaign reads |
| `runs/` | the shared runs, one folder per hardware |
| `tests/` | the tests |

## Licence

The code is MIT OR Apache-2.0, like loken and lokprof: see `LICENSE-MIT` and `LICENSE-APACHE`. The
records under `runs/` are published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/):
see `LICENSE-DATA`. A contributor who opens a pull request agrees to publish their records under it.
