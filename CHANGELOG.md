# Changelog

All notable changes to the benchmarks. The format follows [Keep a Changelog](https://keepachangelog.com/1.1.0/).

## [Unreleased]

### Added

- Campaign: resume with a new loken release on the failed cells only.
- Campaign: measure the embedding models.
- Records: refuse a record whose seal does not match.
- Records: name the version of lokprof that measured the run.
- Records: refuse a record that sampled other than greedily with neutral penalties.
- Table: compare a cell over the iterations no engine flagged.

### Fixed

- Records: accept a run of a host whose set of cards changed.
- Campaign: measure ollama on the Hugging Face GGUF models too.
- Campaign: import a GGUF model split in several files into ollama.
- Campaign: let a request take as long as its cell.
- Campaign: stop an engine that asks for more memory than there is.
- Campaign: select the host-only and Vulkan runs with the backends option.
- Campaign: read the window of a safetensors model from its configuration.
- Campaign: start vLLM with the window of the cell.
- Campaign: measure loken on OpenCL with the backends option.
- Campaign: keep measuring the next models after a cell without a result.
- Campaign: stop a backend sweep that the measured loken was not built for.
- Campaign: end a cell that fails after an engine started instead of waiting on it.
- Table: keep a measured image, audio or speech cell out of the failed ones.
- Campaign: count each blank cell of the score line under its own reason.
