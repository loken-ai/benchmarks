# Matrix

The matrix is the set of axes a campaign sweeps.
The repository holds it in `matrix.toml`, the only curated data a campaign reads.
The models come from loken's catalogue, and the store paths from loken's configuration.

## Axes

| Axis | Values | Fast pass |
|---|---|---|
| `context` | 4096, 131072 | 4096 |
| `prompts` | `100`, `1000`, `10000` | `100` |
| `stream` | true, false | true |
| `device` | `gpu`, `cpu` | `gpu` |

The fast pass, `scripts/bench run`, takes the first value of each axis.
`FULL=1` sweeps every combination.

`context` is the window each engine is asked to reserve.
`prompts` are 3 sizes of 1 text, in tokens counted with the Qwen3 tokenizer.
[Method](../METHOD.md#prompts) gives their characters and words.

## Order

The driver loops over the device, then the window, then the prompt, then the mode.
Inside each combination it measures every model once, 1 cell per model.
The engines start afresh for every cell.

## Cells left out

| Cell | Rule |
|---|---|
| A window that cannot hold the prompt and its answer | skipped when the window is smaller than the prompt size, plus a tenth of it, plus 128 tokens. The `10000` prompt runs at 131072 only |
| A window larger than the one the model declares | skipped, with a line that says so. The declared window is read from the metadata loken shows for the model |
| `cpu` and `stream` false | not measured: the CPU sweeps are streamed only |
| vLLM on `cpu` | not measured: vLLM serves on cards only |
| A generated-media model | measured once, in the first sweep, with the first prompt |
| A model the campaign cannot measure | an error cell, written once, in the first sweep |
| `BACKEND` other than `native` | the `gpu` device only |

## Cells of a text or vision model

`FULL=1` on the native backend gives a text or vision model the cells below, when the model declares no window or one of 131072 or more.
A model that declares a smaller window loses the rows above it.

| Window | Prompt | GPU, stream | GPU, non-stream | CPU, stream | CPU, non-stream |
|---|---|---|---|---|---|
| 4096 | `100` | measured, the fast pass | measured | measured | not measured |
| 4096 | `1000` | measured | measured | measured | not measured |
| 4096 | `10000` | skipped: the prompt does not fit | skipped | skipped | not measured |
| 131072 | `100` | measured | measured | measured | not measured |
| 131072 | `1000` | measured | measured | measured | not measured |
| 131072 | `10000` | measured | measured | measured | not measured |

The model gets 15 measured combinations: 10 on the GPU and 5 on the CPU.
Each measured combination gives 1 row to loken and 1 row to the peer engine.
A vLLM peer has rows in the 10 GPU combinations only.

## Engines of a model

The format loken declares for a model decides its peer engine.
The capability loken declares decides the clock of lokprof.

<!-- site: widget table id=benchmarks-matrix-engines -->
| Capability | Format | Engines | lokprof clock |
|---|---|---|---|
| text | `gguf` | loken, ollama | decode tok/s |
| text | `safetensors` | loken, vLLM | decode tok/s |
| vision | `gguf` | loken, ollama | decode tok/s, the prompt beside an image |
| vision | `safetensors` | loken, vLLM | decode tok/s, the prompt beside an image |
| image | any | loken | megapixels per second, on `/v1/images/generations` |
| tts | any | loken | real-time factor, on `/v1/audio/speech` |
| music, sfx | any | loken | real-time factor, on `/v1/audio/generations` |
| asr | `safetensors` | loken, vLLM | word error rate, on `/v1/audio/transcriptions` |
| asr | other | loken | word error rate, on `/v1/audio/transcriptions` |
| text or vision | neither | none | an error cell: unknown format |
| no capability | any | none | an error cell: no engine of this build serves the model |
| embedding | `gguf` | loken, ollama | input tok/s and latency, on `/v1/embeddings` |
| embedding | `safetensors` | loken, vLLM | input tok/s and latency, on `/v1/embeddings` |
| video, midi | any | none | an error cell: lokprof has no clock for it |
<!-- site: end -->

A model in both formats is 2 catalogue entries.
The GGUF entry is measured against ollama, the safetensors entry against vLLM, each on its own weights.

A speech recognition cell transcribes a recording of 11 seconds from the repository and reads its word error rate against its transcript.
vLLM transcribes the same checkpoint, its context held to the decoder length the checkpoint declares.

## Gates

| Capability | A cell passes when |
|---|---|
| text, vision | the answer is not degenerate |
| image | the pipeline is deterministic at a fixed seed |
| tts | it produced audio, not silence |
| embedding | every vector is finite and not all zeros |
| asr | it produced a transcript |
