# Product Requirements Document: Wavhost
### Local-first TTS runtime (working title)

**Status:** Draft v2 (revised)
**Owner:** Smit
**Last updated:** September 2026

---

## 1. Summary

Wavhost (working title — rename before public launch) is an open-source, local-first runtime for text-to-speech models. It gives developers a single CLI and an OpenAI-compatible API to `pull`, cache, and `run` TTS models locally.

**v0 focus:** be the simplest local TTS drop-in for app developers — not a cloning platform, not a shareable-voice network, and not a general speech stack.

**Later (post-v0, feedback-driven):** voice cloning, fine-tuning, shareable voice artifacts ("Voicefile"), community registry, Kokoro and additional backends, watermarking, streaming, Docker, and web UI.

---

## 2. Positioning

**Working statement:** *"Local TTS models. One CLI. An OpenAI-compatible speech API."*

| Priority | Direction |
|---|---|
| Now | Local TTS runtime: model pull, run, OpenAI-compatible `/v1/audio/speech` |
| Later | Cloning, fine-tuning, Voicefile sharing / community registry |

**Competitive stance:** Do **not** frame v0 against Vocal (vocal-ai) or other voice runtimes. Position as a complementary, TTS-focused local runtime for developers who want a clean speech API and model management. Avoid "Ollama for voices" / clone-and-share messaging at launch.

---

## 3. Problem Statement

- TTS backends (Chatterbox, Qwen3-TTS, Kokoro, others) each have different install paths, CLIs, and inference code.
- App developers want a **local** OpenAI-compatible TTS endpoint without per-character cloud cost or sending audio text to a host.
- Existing tools are either model-level repos (high friction), cloud APIs (cost/privacy), or broader voice platforms — Wavhost v0 stays narrow: **TTS run + model management done well**.

---

## 4. Goals (v0)

1. Let an indie/app developer go from install → `pull` → first WAV in **under 5 minutes on GPU**.
2. One Python CLI and one OpenAI-compatible API (`/v1/audio/speech`) across supported backends.
3. Ollama-style local storage (manifests + content-addressed blobs) so pulls are cacheable, verifiable, and deduped.
4. Show each model's license clearly before download/use.
5. Ship a **thin** public v0 ASAP and iterate in public based on feedback.

---

## 5. Non-Goals (v0)

| Out of v0 | Notes |
|---|---|
| Speech-to-text (STT) | TTS only |
| Streaming synthesis | Chunked/low-latency later |
| Voice cloning | Deferred; no clone UX in v0 |
| Fine-tuning | Deferred |
| Voicefile + community registry | Sharing later |
| Docker one-liner | Deferred |
| Local web UI | CLI + API only |
| Real-time voice agents | Out of scope for v0 |
| Hosted/cloud SaaS | Local-first, self-hosted only |

---

## 6. Target Users

| Persona | Role in v0 |
|---|---|
| **Indie / app developer** (primary) | Needs local OpenAI-compatible TTS for an app without cloud TTS cost |
| Voice agent builder | Secondary; same API drop-in, no streaming yet |
| Content creator / hobbyist | Not primary for v0 (no clone, no UI) |
| OSS tinkerer | Welcome, but v0 docs optimize for the app-developer path |

---

## 7. Feature Scope

### 7.1 Thin v0 — ship first (ASAP)

| Feature | Description | Priority |
|---|---|---|
| `wavhost pull <model>` | Download and cache a base model from Hugging Face into local storage | P0 |
| `wavhost run <model> "text"` | Synthesize speech to an audio file | P0 |
| `wavhost serve` | Local HTTP server (default port **11435**) | P0 |
| `POST /v1/audio/speech` | OpenAI-compatible request/response shape (base-URL swap) | P0 |
| Content-addressed local storage | Manifest + blob design (SHA-256, dedup) under `~/.wavhost` | P0 |
| License display | Show underlying model license before pull/use | P0 |
| First backend | Whichever of **Chatterbox** or **Qwen3-TTS** packages cleaner | P0 |

### 7.2 Immediately after thin v0

| Feature | Description | Priority |
|---|---|---|
| Second backend | The other of Chatterbox / Qwen3-TTS | P0/P1 |
| Polish | Docs, install path, failure modes, license UX | P1 |

### 7.3 Post-v0 (decide after launch feedback)

Candidates (order **not** locked):

- Voice cloning (`clone` + consent flow)
- Kokoro (fast/small path)
- Voicefile spec + community registry
- Fine-tuning (LoRA-style)
- Audio watermarking
- Streaming synthesis
- Docker one-liner
- Minimal local web UI
- Integrations (Open WebUI, etc.)

---

## 8. Models

| Model | Role | When |
|---|---|---|
| Chatterbox | v0 backend | First or second (whichever packages easier) |
| Qwen3-TTS | v0 backend | First or second (whichever packages easier) |
| Kokoro | Fast/small path | After v0 (feedback-driven) |

**Pull source (v0):** cloud, defaulting to **Hugging Face** repos declared in a built-in model registry (YAML/JSON). No custom registry backend in v0.

**Hardware:** GPU **recommended**; CPU **best-effort** and documented per model.

---

## 9. Technical Architecture

### 9.1 Language & components

| Layer | Choice | Rationale |
|---|---|---|
| CLI + server | **Python** (e.g. Typer/Click + FastAPI) | Fastest path for v0; both target backends are Python/PyTorch |
| Inference | Python backends behind a common protocol (`TTSBackend`) | Plug Chatterbox / Qwen3-TTS without rewriting the CLI/API |
| Packaging | `pyproject.toml`, installable as `wavhost` | Simple `pip install` developer path |

Go rewrite / static binary is explicitly **out of v0** (revisit later if distribution becomes the bottleneck).

### 9.2 Storage (Ollama-style)

```
~/.wavhost/
  models/
    manifests/.../<model>/<tag>
    blobs/sha256-<digest>
```

- Manifests: small JSON listing layers (weights, config, license metadata) by SHA-256 digest.
- Blobs: content-addressed; identical layers stored once (dedup).
- On `pull`: fetch manifest → resolve layers → download missing blobs from HF → verify hash → ready to run.

Voice-specific storage (`voices/`) is reserved for post-v0 cloning/Voicefile work — not required for thin v0.

### 9.3 API

- `POST /v1/audio/speech` — OpenAI-compatible enough for existing clients with a base-URL swap.
- Default listen port: **11435** (avoids clashing with Ollama's `11434`).
- No streaming audio in v0.

---

## 10. Trust & Safety (v0)

- **In v0:** clear license display for every model before `pull` / use.
- **Deferred:** mandatory watermarking, clone consent attestation, registry moderation/takedown (needed when cloning/sharing land).

README should still include a short responsible-use note, without blocking the core install → audio loop.

---

## 11. Success Metrics

| Metric | Target |
|---|---|
| **Primary:** time to first audio | Install → `pull` → first WAV **under 5 minutes on GPU** |
| Secondary | OpenAI TTS clients work with base-URL → `http://localhost:11435/v1` |
| Secondary | Launch reception (GitHub interest, forums) — directional, not a gate |

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| Chatterbox / Qwen3-TTS packaging friction | Ship whichever is easier first; keep backend interface thin |
| Overlap with existing local voice tools | Stay TTS-narrow; don't pitch as a Vocal rival |
| Model license complexity | Surface license on pull; document third-party licenses separately from our code license |
| Name / trademark (working title echoes "Ollama") | **Rename before public launch** |
| Underestimating inference deps | Thin v0 = one backend + API + storage; expand only after the loop is solid |
| CPU path disappointing | Document GPU as recommended; CPU as best-effort |

---

## 13. Milestones (suggested)

1. **Week 0–1:** Scaffold Python CLI + `~/.wavhost` storage + HF pull for one model.
2. **Week 1–2:** `run` + `serve` + `/v1/audio/speech`; license-on-pull; README quickstart.
3. **Public thin v0:** Ship with one backend; announce and gather feedback.
4. **Next:** Add the second of Chatterbox / Qwen3-TTS; polish based on issues.
5. **After feedback:** Prioritize clone vs Kokoro vs Voicefile vs streaming vs Docker/UI.

Exact dates are flexible — bias to **shipping thin and iterating**.

---

## 14. Open Questions

- Final public name (replace Wavhost before launch).
- Which of Chatterbox vs Qwen3-TTS packages cleaner for day-one (decide via short spike).
- Our code license (recommend Apache-2.0 or MIT — default TBD at repo init).
- Exact OpenAI `/v1/audio/speech` field coverage for v0 (minimal viable vs fuller parity).
- Post-v0 priority order (locked as: **decide after launch feedback**).

---

## 15. Decision log (Draft v1 → v2)

| Topic | v1 | v2 (locked) |
|---|---|---|
| Positioning | Clone/fine-tune/share like Ollama | Local TTS runtime first; sharing later |
| vs Vocal | Differentiator = cloning + Voicefile | Complementary; don't frame as competitor |
| v0 features | pull, run, clone, API, consent | pull, run, API only |
| Models | Kokoro + Fish Speech / XTTS | Chatterbox + Qwen3-TTS; Kokoro later |
| Stack | Go or Python | Python CLI + server |
| Name | Wavhost | Working title; rename before launch |
| Storage | Ollama-style | Keep Ollama-style |
| Trust | License + consent + watermark | License on pull only (v0) |
| Primary user | Mixed | Indie/app developer |
| Timeline | Multi-phase weeks 1–15+ | Thin v0 ASAP; iterate in public |
| Post-v0 | Prescribed Voicefile → fine-tune… | Decide after launch feedback |
| Pull source | HF / GitHub Releases | HF (cloud) default |
| Port | 11435 suggested | **11435** |
| Hardware | Implicit | GPU recommended; CPU best-effort |
| Success metric | <2 min to cloned audio | <5 min to first audio on GPU |

---

*End of Draft v2*
