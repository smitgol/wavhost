# Wavhost

[![PyPI](https://img.shields.io/pypi/v/wavhost.svg)](https://pypi.org/project/wavhost/)
[![Python](https://img.shields.io/pypi/pyversions/wavhost.svg)](https://pypi.org/project/wavhost/)
[![License](https://img.shields.io/pypi/l/wavhost.svg)](https://github.com/smitgol/wavhost/blob/master/LICENSE)

**Local-first TTS runtime with OpenAI-compatible API**

Wavhost is a local text-to-speech (TTS) runtime that brings high-quality voice synthesis to your machine. Run TTS models locally with a simple CLI and OpenAI-compatible HTTP API—no API keys, no per-character billing, complete privacy.

## Features

- 🚀 **Local-first**: All processing happens on your machine—no API keys, no cloud calls, complete privacy
- 🔌 **OpenAI-compatible API**: Drop-in replacement for OpenAI's `/v1/audio/speech` endpoint
- 🎤 **Voice library**: Create, save, and manage unlimited custom voices from reference audio
- 📦 **Ollama-style storage**: Content-addressed storage with SHA-256 deduplication
- 🎯 **Simple CLI & API**: Full CLI commands and RESTful HTTP API for voice management
- 🔓 **Open source**: MIT/Apache-2.0 licensed runtime, using open TTS models
- ⚡ **GPU accelerated**: Optimized for NVIDIA GPUs (CPU fallback available)
- 🔒 **Privacy-focused**: Your voices and audio never leave your machine

## Quick Start

### Installation

```bash
pip install wavhost
```

This installs the runtime and PyTorch. TTS engines such as Chatterbox are **not** included, since each one is large and Wavhost supports several — the engine a model needs is installed for you when you pull that model.

**GPU users:** engines pin an exact PyTorch version, and PyPI's wheel for that pin is CPU-only on Windows. `wavhost pull` detects an NVIDIA GPU paired with a CPU-only PyTorch and prints the one command that swaps in the CUDA build while keeping the engine's pin, e.g.:

```bash
pip install "torch==2.6.0+cu124" "torchaudio==2.6.0+cu124" --index-url https://download.pytorch.org/whl/cu124
```

Run it *after* the pull (the engine install would otherwise replace it), and note the `+cu124` tag is required — pip considers `2.6.0+cpu` to already satisfy `torch==2.6.0`. The same hint appears if `wavhost run` ever has to fall back to the CPU.

### Pull a Model

```bash
wavhost pull chatterbox-turbo
```

This displays the license, installs the model's backend engine if needed, and **downloads weight layers** into `~/.wavhost` (content-addressed blobs + a local checkpoint). Runtime loads from that local checkpoint — it does not call the Hugging Face Hub client.

Layer URLs currently point at Hugging Face resolve endpoints as plain HTTPS. Swapping to your own CDN later only requires changing those URLs in the registry.

If you'd rather manage engine packages yourself, install the matching extra ahead of time and skip the prompt:

```bash
pip install "wavhost[chatterbox]"
wavhost pull chatterbox-turbo --skip-deps
```

### Generate Speech

```bash
wavhost run chatterbox-turbo "Hello world, this is Wavhost!" -o output.wav
```

### Manage Voices

Create and save custom voices from reference audio:

```bash
# Create a voice from reference audio
wavhost voice create my-voice --ref reference.wav --desc "My custom voice"

# List saved voices
wavhost voice list

# Use a saved voice
wavhost run chatterbox-turbo "Hello from my voice!" --voice my-voice -o output.wav
```

### Start the Server

```bash
wavhost serve
```

The server starts on `http://127.0.0.1:11435` with an OpenAI-compatible endpoint.

### Use the API

```bash
curl http://127.0.0.1:11435/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello from Wavhost!",
    "voice": "my-voice"
  }' \
  --output speech.mp3
```

Use `"voice": "default"` for the built-in voice, or specify a saved voice name.

## Complete Workflow Example

Here's a complete example showing the full voice management workflow:

```bash
# 1. Install Wavhost
pip install wavhost

# 2. Pull a TTS model
wavhost pull chatterbox-turbo

# 3. Create a custom voice from your audio
wavhost voice create my-narrator --ref ~/audio/sample.wav --desc "My narrator voice"

# 4. Generate speech using your custom voice (CLI)
wavhost run chatterbox-turbo "Welcome to Wavhost!" --voice my-narrator -o welcome.wav

# 5. Start the API server
wavhost serve &

# 6. Create voices via API
curl -X POST http://localhost:11435/v1/voices \
  -F "name=assistant" \
  -F "file=@assistant-sample.wav" \
  -F "description=AI assistant voice"

# 7. List all voices
curl http://localhost:11435/v1/voices

# 8. Generate speech via API with custom voice
curl http://localhost:11435/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello! This is my custom voice.",
    "voice": "assistant",
    "response_format": "mp3"
  }' \
  --output output.mp3

# 9. Clean up - remove a voice when done
wavhost voice rm my-narrator
```

## Available Models

| Model | Size | Device | Description |
|-------|------|--------|-------------|
| `chatterbox-turbo` | 350M | GPU | Fast, high-quality English TTS (MIT) |
| `chatterbox-base` | 500M | GPU | Original high-quality model (MIT) |

All models are licensed under MIT and developed by Resemble AI.

## CLI Reference

### `wavhost pull <model_name>`

Download weight layers into local storage and register the model, installing its backend engine if needed.

**Options:**
- `--force`: Pull even if the model is already installed (still resumes existing blobs)
- `--skip-deps`: Don't install the backend engine (assume it's already available)

**Example:**
```bash
wavhost pull chatterbox-base
```

### `wavhost run <model_name> <text>`

Generate speech from text using a local model.

**Options:**
- `-o, --output PATH`: Output WAV file path (default: `output.wav`)
- `--voice NAME_OR_PATH`: Saved voice name from local library, or path to reference audio
- `--device DEVICE`: Device to use (`cuda`, `cpu`, or `mps`)

**Example:**
```bash
wavhost run chatterbox-turbo "Welcome to Wavhost" -o welcome.wav

# Use a saved voice
wavhost run chatterbox-turbo "Hello" --voice my-voice -o hello.wav

# Use reference audio directly
wavhost run chatterbox-turbo "Hello" --voice /path/to/audio.wav -o hello.wav
```

### `wavhost voice`

Manage local voice library.

#### `wavhost voice create <name> --ref <audio>`

Create and save a voice from reference audio.

**Options:**
- `--ref PATH` (required): Path to reference audio file
- `--desc TEXT`: Voice description

**Example:**
```bash
wavhost voice create narrator --ref voice.wav --desc "Professional narrator voice"
```

#### `wavhost voice list`

List all saved voices.

**Example:**
```bash
wavhost voice list
```

#### `wavhost voice show <name>`

Show details about a saved voice.

**Example:**
```bash
wavhost voice show narrator
```

#### `wavhost voice rm <name>`

Remove a saved voice.

**Options:**
- `-y, --yes`: Skip confirmation prompt

**Example:**
```bash
wavhost voice rm narrator
```

### `wavhost serve`

Start the OpenAI-compatible TTS server.

**Options:**
- `--host HOST`: Host to bind to (default: `127.0.0.1`)
- `--port PORT`: Port to bind to (default: `11435`)
- `--reload`: Enable auto-reload for development

**Example:**
```bash
wavhost serve --host 0.0.0.0 --port 8000
```

### `wavhost list`

List installed models and available models in the registry.

**Example:**
```bash
wavhost list
```

### `wavhost rm <model_name>`

Remove a pulled model and free its disk space (manifest, checkpoint, and any blobs no other model still uses).

**Options:**
- `-y, --yes`: Skip the confirmation prompt

**Example:**
```bash
wavhost rm chatterbox-turbo
```

### `wavhost uninstall`

Wipe local Wavhost data under `~/.wavhost` and print how to remove the Python package.

**Options:**
- `--purge-data` / `--keep-data`: Delete or keep local storage (default: purge)
- `-y, --yes`: Skip the confirmation prompt

**Example:**
```bash
wavhost uninstall
# then, if you also want the package gone:
pip uninstall wavhost
```

## API Reference

### Voice Management

#### `POST /v1/voices`

Create a new voice from reference audio.

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `name` (string, required): Voice name
  - `file` (file, required): Reference audio file
  - `description` (string, optional): Voice description

**Example:**
```bash
curl -X POST http://localhost:11435/v1/voices \
  -F "name=narrator" \
  -F "file=@reference.wav" \
  -F "description=Professional narrator voice"
```

**Response:**
```json
{
  "name": "narrator",
  "message": "Voice 'narrator' created successfully"
}
```

#### `GET /v1/voices`

List all saved voices.

**Example:**
```bash
curl http://localhost:11435/v1/voices
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "name": "narrator",
      "description": "Professional narrator voice",
      "backend": "chatterbox",
      "ref_audio": {
        "digest": "sha256-...",
        "original_filename": "reference.wav",
        "size": 1024000
      }
    }
  ]
}
```

#### `GET /v1/voices/{name}`

Get details about a specific voice.

**Example:**
```bash
curl http://localhost:11435/v1/voices/narrator
```

**Response:**
```json
{
  "name": "narrator",
  "description": "Professional narrator voice",
  "backend": "chatterbox",
  "ref_audio": {
    "digest": "sha256-...",
    "original_filename": "reference.wav",
    "size": 1024000
  }
}
```

#### `DELETE /v1/voices/{name}`

Delete a saved voice.

**Example:**
```bash
curl -X DELETE http://localhost:11435/v1/voices/narrator
```

**Response:**
```json
{
  "name": "narrator",
  "deleted": true
}
```

### Speech Generation

### `POST /v1/audio/speech`

Generate speech from text (OpenAI-compatible).

**Request body:**
```json
{
  "model": "chatterbox-turbo",
  "input": "Text to synthesize",
  "voice": "default",
  "response_format": "mp3",
  "speed": 1.0
}
```

**Parameters:**
- `model` (string, required): Model to use
- `input` (string, required): Text to synthesize (max 4096 chars)
- `voice` (string, optional): Voice name from local library, or `"default"` for built-in voice
- `response_format` (string, optional): Audio format. Defaults to `mp3`.
  - Encoded: `mp3`, `wav`, `opus`, `flac`, `aac`
  - Raw PCM (signed 16-bit little-endian): `pcm` (model native rate), `pcm_16000`, `pcm_22050`, `pcm_24000`, `pcm_44100`
- `speed` (float, optional): Speed multiplier 0.25-4.0 (currently not implemented)

**Response:**
Binary audio file in the requested format.

**Error Responses:**
- `400 Bad Request`: Unknown voice or invalid parameters
- `404 Not Found`: Model not found
- `500 Internal Server Error`: Generation failed

### `GET /v1/models`

List available models (OpenAI-compatible).

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "chatterbox-turbo",
      "object": "model",
      "created": 0,
      "owned_by": "resemble",
      "installed": true,
      "description": "Chatterbox Turbo - 350M parameter English TTS model (MIT License)"
    }
  ]
}
```

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

## Integration Examples

### Python

```python
import requests

# Create a voice
with open("reference.wav", "rb") as f:
    response = requests.post(
        "http://localhost:11435/v1/voices",
        data={"name": "my-voice", "description": "Custom voice"},
        files={"file": f}
    )
print(response.json())

# Generate speech with custom voice
response = requests.post(
    "http://localhost:11435/v1/audio/speech",
    json={
        "model": "chatterbox-turbo",
        "input": "Hello world!",
        "voice": "my-voice",
        "response_format": "mp3"
    }
)

with open("output.mp3", "wb") as f:
    f.write(response.content)
```

### JavaScript (Node.js)

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

// Create a voice
const form = new FormData();
form.append('name', 'my-voice');
form.append('description', 'Custom voice');
form.append('file', fs.createReadStream('reference.wav'));

await axios.post('http://localhost:11435/v1/voices', form, {
  headers: form.getHeaders()
});

// Generate speech
const response = await axios.post(
  'http://localhost:11435/v1/audio/speech',
  {
    model: 'chatterbox-turbo',
    input: 'Hello world!',
    voice: 'my-voice',
    response_format: 'mp3'
  },
  { responseType: 'arraybuffer' }
);

fs.writeFileSync('output.mp3', Buffer.from(response.data));
```

### cURL

```bash
# Complete workflow
# 1. Create voice
curl -X POST http://localhost:11435/v1/voices \
  -F "name=narrator" \
  -F "file=@voice.wav" \
  -F "description=Narrator voice"

# 2. Generate speech
curl http://localhost:11435/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"chatterbox-turbo","input":"Hello!","voice":"narrator"}' \
  --output speech.mp3

# 3. List voices
curl http://localhost:11435/v1/voices

# 4. Delete voice
curl -X DELETE http://localhost:11435/v1/voices/narrator
```

## Architecture

### Storage

Wavhost uses Ollama-style content-addressed storage:

```
~/.wavhost/
  models/
    manifests/
      registry/
        resemble/
          chatterbox-turbo/
            latest
    blobs/
      sha256-<hash>
    checkpoints/
      resemble/
        chatterbox-turbo/
          latest/
            ve.safetensors
            ...
  voices/
    manifests/
      <voice_name>.json
    blobs/
      sha256-<hash>
```

- **Manifests**: Model metadata and layer digests
- **Blobs**: Content-addressed file storage with SHA-256 deduplication
- **Checkpoints**: Materialized directories (hardlinks/copies of blobs) loaded by `from_local`
- **Voices**: Saved voice library with reference audio and metadata

### Backends

The `TTSBackend` protocol enables pluggable TTS engines:

- **Chatterbox**: MIT-licensed models by Resemble AI (currently implemented)
- Supports voice creation and cloning from reference audio
- Future backends can be added by implementing the `TTSBackend` protocol

**Voice Handles:** Each backend implements voice creation differently:
- Chatterbox stores reference audio paths for on-the-fly cloning
- Future backends may use embeddings or other voice representations
- The voice storage layer is backend-agnostic

## Hardware Requirements

### Recommended (GPU)
- NVIDIA GPU with 4GB+ VRAM (RTX 2060 or better)
- 16GB+ system RAM
- CUDA 11.8 or newer

### Minimum (CPU)
- Modern CPU with 8+ cores
- 8GB+ system RAM
- Generation falls back to CPU automatically, but runs considerably slower than real-time

### Storage
- ~2GB per TTS model (varies by model)
- Voice audio files (typically a few MB per voice)
- Total: Plan for 5-10GB for comfortable usage

## FAQ

### General

**Q: Is my data sent to any cloud service?**  
A: No. Everything runs locally. Models, voices, and generated audio never leave your machine.

**Q: Can I use this commercially?**  
A: Yes. Wavhost runtime is Apache-2.0. Each model has its own license—Chatterbox models are MIT.

**Q: How does voice cloning work?**  
A: Provide 3-10 seconds of clean reference audio. The model clones the voice characteristics for new text.

**Q: What audio formats are supported for reference audio?**  
A: Common formats like WAV, MP3, FLAC work. Best results with WAV files at 16kHz or higher.

### Voice Management

**Q: How many voices can I create?**  
A: Unlimited. Each voice uses minimal storage (just the reference audio, deduplicated).

**Q: Can I share voices with others?**  
A: Currently, voices are stored locally. Voice export/import is planned for future releases.

**Q: What makes a good reference audio sample?**  
A: Clear speech, minimal background noise, 3-10 seconds, natural speaking pace.

**Q: Can I update a voice after creating it?**  
A: Delete the old voice and create a new one with the same name using updated audio.

### API & Development

**Q: Is this compatible with OpenAI's API?**  
A: Yes. The `/v1/audio/speech` endpoint matches OpenAI's specification. Just change the base URL.

**Q: Can I run multiple instances?**  
A: Yes. Run on different ports or machines. Each instance has its own voice library.

**Q: What about rate limiting?**  
A: No rate limits. You control the hardware and throughput.

**Q: Can I use this in Docker?**  
A: Yes. Mount `~/.wavhost` as a volume to persist models and voices across containers.

## Development

```bash
git clone https://github.com/smitgol/wavhost.git
cd wavhost
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black wavhost tests

# Lint
ruff check wavhost tests

# Type checking
mypy wavhost
```

## Roadmap

### v0.1 (Current)
- ✅ Ollama-style storage
- ✅ Chatterbox backend
- ✅ CLI (pull, run, serve)
- ✅ OpenAI-compatible API
- ✅ Local voice library (create, save, manage via CLI and API)

### Future
- Additional backends (Qwen3-TTS, etc.)
- Streaming audio generation
- Model quantization
- Multi-language models

## Use Cases

### Content Creation
- **Audiobooks**: Create consistent narrator voices for long-form content
- **Podcasts**: Generate intro/outro segments with custom voices
- **Videos**: Add voiceovers with different character voices
- **Marketing**: Produce audio ads with brand-specific voices

### Development
- **Voice Assistants**: Build local voice assistants with custom personalities
- **Accessibility**: Add text-to-speech to applications without API dependencies
- **Games**: Create character voices without royalty fees
- **Prototyping**: Test voice UX without cloud service costs

### Business
- **Call Centers**: Generate hold messages and IVR prompts
- **E-learning**: Create course narration with consistent voices
- **Documentation**: Convert docs to audio with professional narration
- **Customer Support**: Build voice bots that run on-premise

## License

**Wavhost (this runtime):** Apache-2.0

**Third-party models:** Each model is subject to its own license:
- Chatterbox models: MIT License (see [Resemble AI's license](https://github.com/resemble-ai/chatterbox/blob/main/LICENSE))

Model licenses are displayed before download with `wavhost pull`.

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

## Acknowledgments

- [Resemble AI](https://resemble.ai) for the excellent Chatterbox TTS models
- [Ollama](https://ollama.ai) for storage architecture inspiration
- [OpenAI](https://openai.com) for the audio API specification

## Support

- 📖 [Documentation](https://github.com/smitgol/wavhost)
- 🐛 [Issue Tracker](https://github.com/smitgol/wavhost/issues)
- 💬 [Discussions](https://github.com/smitgol/wavhost/discussions)

---

**Built for developers who want local, private, high-quality TTS.**
