# Changelog

All notable changes to Wavhost are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-09-16

### Added

- OpenAI-compatible `stream` on `POST /v1/audio/speech` for progressive download of `mp3` and `pcm` / `pcm_*` audio

## [0.2.0] - 2026-09-15

### Added

- Qwen3-TTS backend with CustomVoice and Base checkpoints (`qwen-0.6-*`, `qwen-1.7-*`)
- Chatterbox Nano (`chatterbox-nano`) and Multilingual (`chatterbox-multilingual`) models
- CLI/API `--language` support for multilingual synthesis
- PCM16 WAV output path for more reliable playback
- Website models page redesign with per-model `wavhost pull` commands

### Changed

- Lazy-load backends and simplify registry/storage paths
- Docs and README updated for new models and languages

## [0.1.1] - 2026-09-15

### Added

- Local voice library system with create, list, show, and delete operations
- CLI commands: `wavhost voice create`, `voice list`, `voice show`, `voice rm`
- HTTP API endpoints: `POST /v1/voices`, `GET /v1/voices`, `GET /v1/voices/{name}`, `DELETE /v1/voices/{name}`
- Content-addressed voice storage with SHA-256 deduplication under `~/.wavhost/voices/`
- Support for saved voice names in `--voice` CLI parameter and API `voice` field
- Backend `create_voice()` method and `voice_handle` parameter support
- Python-multipart dependency for file upload support in API

### Changed

- Extended `TTSBackend` protocol with voice creation capabilities
- Updated `ChatterboxBackend` to support both saved voice handles and direct audio paths
- Enhanced `/v1/audio/speech` endpoint to resolve voice names from local library

### Fixed

- Audio conversion optimization in server.py
- Numpy dependency properly declared in pyproject.toml

## [0.1.0] - 2026-09-14

### Added

- CLI: `pull`, `run`, `serve`, `list`, `rm`, and `uninstall`
- OpenAI-compatible `POST /v1/audio/speech` HTTP API
- Chatterbox backend with on-demand engine install
- Ollama-style content-addressed local model storage
