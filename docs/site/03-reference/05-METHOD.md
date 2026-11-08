# Method

Every engine of a cell is measured by the same tool, on the same prompt, with the same clock.
[Read a results table](03-results-table.md) gives each column.

## The cell

[lokprof](https://github.com/loken-ai/lokprof) measures a cell, see [Concepts](../01-get-started/04-concepts.md#cell), in 3 iterations, greedy, with a cap of 128 generated tokens.

## Engines run alone

Each engine runs alone.
The processes of the other engines are stopped, and the cards come back to their idle temperature before it starts.
A peer process left running changes where a model lands.

On the native backend, ollama runs with its Vulkan backend off.
A CPU row runs ollama with `num_gpu` 0.

## Context window

`Ctx` is the window each engine was asked to reserve, not a window the prompt fills.
The longest prompt is 10 000 tokens.

Ollama allocates the whole window up front.
At 131072, that sends layers of the larger models to the host.
loken plans its quantised cache at 4096 tokens and grows it on demand, so it reserves less.
The 131072 column compares these 2 allocation policies on prompts far below the window.
It is not a comparison of 2 engines at a full context.

## Prompts

The prompts are 3 sizes of 1 text, and every engine gets the same bytes.
Only the prefill differs between sizes.
The cap of 128 tokens keeps the decode column comparable.
A prompt is named by its size in tokens, and the repository holds its text.

| Prompt | Tokens | Characters | Words |
|---|---|---|---|
| `100` | 100 | 451 | 85 |
| `1000` | 1 000 | 4 384 | 794 |
| `10000` | 10 000 | 42 295 | 7 736 |

The text is the opening of a public domain novel, in plain ASCII.
Each prompt is the start of the next one.
Each is cut where the Qwen3 tokenizer counts exactly its size, at a word or a punctuation mark.
The 100 token prompt ends inside a word.
Another tokenizer counts a few percent more or less, so the size is nominal for the model under test.

A window that cannot hold the prompt and its answer is not measured, so the `10000` prompt runs at the 131072 window only.
A record names its prompt by its size and states the number of characters sent.
A record whose prompt is not one of these 3, or whose text has another length, is refused.

A vision row sends the same prompt beside its image.

## Prompts reach every engine unwrapped

A text prompt reaches every engine without a chat template.
lokprof sends it to `/api/generate` in raw mode, and to vLLM on `/v1/completions`, which applies no template.
A vision prompt goes to `/api/generate` with its image, through the chat template.

Rows before 2026-08-14 08:00 had 2 engines answering a story opening as a question while the third continued it.

## Cards

A campaign gives every engine every card of the machine.
ollama is told to spread a model over the cards it sees.

A run restricted to 1 card keeps ollama on it only while the weights fit that card.
Above that, ollama would get 1 card plus host spill while the other engines get the machine, so every engine gets every card.
Rows before 2026-08-14 04:00 on models larger than 1 card were taken under an older rule, and read as wins that were not.

## Weights

An ollama row measures a GGUF file, and the loken row of its cell measures the same file.
A vLLM row measures a safetensors checkpoint, and the loken row of its cell measures the same checkpoint.
A model published in both formats is 2 catalogue entries, with 2 sets of cells.

Before this pairing, a vLLM row read an AWQ 4-bit checkpoint against the GGUF Q4_K_M of the other 2 engines, and collected no prefill.
Every vLLM comparison of that time carries this caveat.

## Delta

A Delta compares loken with the best other engine of the cell.
[Read a results table](03-results-table.md#delta) gives its sign, its blank cases and the version of each other engine that counts.

The share of decode cells loken wins, on the results site, reads the same warm Deltas.

## Cells that publish no rate

An `incoherent` answer is excluded both ways.
As a reference it would flatter loken, and as a loken row it would publish a Delta against work nobody did.

The `incoherent` gemma4 cells are a tracked defect of loken, not a verdict on the models.
The same weights answer correctly under ollama on several of those rows.

[Read a results table](03-results-table.md#cells-that-publish-no-rate) lists every mark.

## Read Tokens before the rate

A model that stops early averages its rate over a few tens of steps, and carries the fixed cost of the request.
The same engine measured 398 tok/s over 30 tokens and 417 over 128.
Short rows are published, and their Delta is blank.

## Cold and warm

Every cell runs 3 times.
Each iteration gets a prompt that no engine has seen: the text of the cell with a counter in front of it.
An engine that keeps a prefix cache then cannot answer from it.
Replaying 1 prompt would measure that cache, and report a prefill of hundreds of thousands of tokens per second.
That figure is a cache hit in the units of a rate.

Cold is the first iteration of the cell: the first request after the engine started.
It pays what a first request pays: loading, compiling, filling caches.
Warm is the median of the following iterations, on an engine that has served a request.

The columns that split are Prefill, TTFT and Decode, and their 3 Delta columns, each printed `cold / warm`.
A Delta is blank for a half that cannot be compared.
Joules, E2E and the token count are taken over all the iterations.

During a campaign, the driver prints 1 line for each half: `N/M cells win on BOTH axes`.
A cell wins when the decode Delta of that half and the energy Delta are both positive.

## The rate columns

Prefill is the prompt tokens over the time to first token, measured by lokprof the same way for every engine.
TTFT is that time, in milliseconds.

Prefill used to be each engine's own `prompt_tok_s`.
That figure is the engine's timer minus what it does not count, and the engines do not leave out the same things.
On a 15 token prompt, ollama reported 652 tok/s where its own time to first token implied 35, and loken 49 373 where its own implied 728.
Side by side, those figures reversed the verdict on 3 cells of 4.
At the long prompt the exaggeration was worse.

Decode is the span the client observes from the first generated token to the last, the same for every engine.
vLLM publishes no split of prefill and decode.
Scoring 2 engines by their own bookkeeping and the third by the clock would compare the bookkeeping.

Cells measured from 2026-09-02 also carry `server_decode_tok_s` in the record, the rate the server reports of itself.
It shows where the 2 disagree.
At 2 ms a token, the read loop of the client costs about what the token does.

## Energy

Energy sums the draw of the cards with the RAPL package and DRAM domains of the processor.
An NVIDIA card is read through NVML, an AMD card through the power reading of the amdgpu driver.
A total over the cards alone is compared only with another total over the cards alone.

The joules are a median over all the iterations of a cell.
The first iteration of a cell is a cold load.
Prefill took the median for that reason from the start.
Decode and energy took the mean, on the assumption that they did not carry the outlier.

On a mixture too large to hold, they do.
qwen3next measured 3.8, 15.2 and 15.2 tok/s, and the mean published 11.4 for a model that decodes at 15.2.
Energy was worse, and flattered loken.
The joules of the first iteration include loading the weights, and the engines inflate by different factors.
qwen3:0.6b published +383.6% where the steady state is +149.9%.
The median leaves a cell with flat iterations unchanged, which is every cell but the large mixtures.

## Model families

The family of a model is the architecture its checkpoint declares under `general.architecture`, not the name it is published as.
`deepseek-r1:70b` is a llama and `deepseek-r1:32b` a qwen2, both distils.
What the kernels run is the architecture, not the brand.
