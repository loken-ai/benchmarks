# Changelog

All notable changes to the benchmarks. The format follows [Keep a Changelog](https://keepachangelog.com/1.1.0/).

## [Unreleased]

### Added

- Campaign: resume with a new loken release on the failed cells only.
- Campaign: measure the embedding models.
- Records: refuse a record whose seal does not match.

### Fixed

- Records: accept a run of a host whose set of cards changed.
- Campaign: measure ollama on the Hugging Face GGUF models too.
- Campaign: import a GGUF model split in several files into ollama.
- Campaign: let a request take as long as its cell.
- Campaign: stop an engine that asks for more memory than there is.
- Campaign: select the host-only and Vulkan runs with the backends option.
- Campaign: read the window of a safetensors model from its configuration.
