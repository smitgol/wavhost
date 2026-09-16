"""Model registry with built-in model definitions."""

from dataclasses import dataclass, field
from typing import Any, Optional

from wavhost.exceptions import ModelNotFoundError


@dataclass(frozen=True)
class ModelLayer:
    """A downloadable model file (weight, tokenizer piece, etc.)."""

    filename: str
    url: str
    sha256: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        data: dict[str, Any] = {
            "filename": self.filename,
            "url": self.url,
        }
        if self.sha256 is not None:
            data["sha256"] = self.sha256
        return data


@dataclass(frozen=True)
class ModelInfo:
    """Immutable model information."""

    namespace: str
    name: str
    tag: str
    backend: str
    description: str
    license: str
    license_url: str
    model_class: str
    layers: tuple[ModelLayer, ...] = ()
    model_kwargs: dict[str, Any] = field(default_factory=dict)
    recommended_device: str = "cuda"
    vram_requirement: str = ""
    languages: list[str] = field(default_factory=lambda: ["en"])
    sample_rate: int = 24000
    # Kept for display / migration; download URLs live on layers.
    huggingface_repo: str = ""

    @property
    def full_name(self) -> str:
        """Get the full model name in namespace/name:tag format."""
        return f"{self.namespace}/{self.name}:{self.tag}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "namespace": self.namespace,
            "name": self.name,
            "tag": self.tag,
            "backend": self.backend,
            "description": self.description,
            "license": self.license,
            "license_url": self.license_url,
            "huggingface_repo": self.huggingface_repo,
            "model_class": self.model_class,
            "model_kwargs": self.model_kwargs,
            "recommended_device": self.recommended_device,
            "vram_requirement": self.vram_requirement,
            "languages": self.languages,
            "sample_rate": self.sample_rate,
            "layers": [layer.to_dict() for layer in self.layers],
        }

    def named_voices(self) -> tuple[str, ...]:
        """Built-in speaker names. Empty when the model clones from reference audio."""
        if self.backend == "kokoro":
            return KOKORO_VOICES
        if self.backend == "qwen" and self.model_kwargs.get("task") == "custom_voice":
            return tuple(QWEN_SPEAKERS.values())
        return ()

    def default_named_voice(self) -> Optional[str]:
        return self.model_kwargs.get("default_voice") or self.model_kwargs.get(
            "default_speaker"
        )


CHATTERBOX_LICENSE_URL = "https://github.com/resemble-ai/chatterbox/blob/main/LICENSE"
CHATTERBOX_NAMESPACE = "resemble"
CHATTERBOX_LICENSE = "MIT"

QWEN_LICENSE_URL = "https://github.com/QwenLM/Qwen3-TTS/blob/main/LICENSE"
QWEN_NAMESPACE = "qwen"
QWEN_LICENSE = "Apache-2.0"

KOKORO_LICENSE_URL = "https://github.com/hexgrad/kokoro/blob/main/LICENSE"
KOKORO_NAMESPACE = "hexgrad"
KOKORO_LICENSE = "Apache-2.0"


def _hf_resolve(repo: str, filename: str) -> str:
    """Build a plain HTTPS resolve URL for a Hugging Face file.

    These are ordinary HTTP downloads — Wavhost does not use the HF Hub client.
    The host can later be swapped to a CDN by changing the URL only.
    """
    return f"https://huggingface.co/{repo}/resolve/main/{filename}"


def _layers(repo: str, filenames: tuple[str, ...]) -> tuple[ModelLayer, ...]:
    return tuple(
        ModelLayer(filename=name, url=_hf_resolve(repo, name)) for name in filenames
    )


TURBO_REPO = "ResembleAI/chatterbox-turbo"
TURBO_FILES = (
    "ve.safetensors",
    "t3_turbo_v1.safetensors",
    "s3gen_meanflow.safetensors",
    "conds.pt",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "added_tokens.json",
    "special_tokens_map.json",
)

NANO_REPO = "ResembleAI/chatterbox-nano"
NANO_FILES = (
    "ve.safetensors",
    "t3_nano_v1.safetensors",
    "s3gen_meanflow.safetensors",
    "conds.pt",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "added_tokens.json",
    "special_tokens_map.json",
)

BASE_REPO = "ResembleAI/chatterbox"
BASE_FILES = (
    "ve.safetensors",
    "t3_cfg.safetensors",
    "s3gen.safetensors",
    "tokenizer.json",
    "conds.pt",
)

# Multilingual weights live in the same Hub repo as Base, different filenames.
# Installed chatterbox-tts loads V2 via ChatterboxMultilingualTTS.from_local.
MTL_REPO = BASE_REPO
MTL_FILES = (
    "ve.pt",
    "t3_mtl23ls_v2.safetensors",
    "s3gen.pt",
    "grapheme_mtl_merged_expanded_v1.json",
    "conds.pt",
    "Cangjie5_TC.json",
)

CHATTERBOX_MTL_LANGUAGES = [
    "ar",
    "da",
    "de",
    "el",
    "en",
    "es",
    "fi",
    "fr",
    "he",
    "hi",
    "it",
    "ja",
    "ko",
    "ms",
    "nl",
    "no",
    "pl",
    "pt",
    "ru",
    "sv",
    "sw",
    "tr",
    "zh",
]

QWEN_FILES = (
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "vocab.json",
    "speech_tokenizer/config.json",
    "speech_tokenizer/configuration.json",
    "speech_tokenizer/model.safetensors",
    "speech_tokenizer/preprocessor_config.json",
)

# Official Qwen3-TTS checkpoints (CustomVoice = named speakers; Base = cloning).
QWEN_0_6_CUSTOMVOICE_REPO = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
QWEN_1_7_CUSTOMVOICE_REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
QWEN_0_6_BASE_REPO = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
QWEN_1_7_BASE_REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

QWEN_LANGUAGES = ["en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"]
QWEN_DEFAULT_SPEAKER = "Ryan"
QWEN_SPEAKERS = {
    "vivian": "Vivian",
    "serena": "Serena",
    "uncle_fu": "Uncle_Fu",
    "dylan": "Dylan",
    "eric": "Eric",
    "ryan": "Ryan",
    "aiden": "Aiden",
    "ono_anna": "Ono_Anna",
    "sohee": "Sohee",
}
QWEN_CUSTOMVOICE_KWARGS = {
    "task": "custom_voice",
    "default_speaker": QWEN_DEFAULT_SPEAKER,
}
QWEN_BASE_KWARGS = {"task": "voice_clone"}


# Official Kokoro v1.0: StyleTTS 2 + ISTFTNet. Not a Transformers LM —
# there is no tokenizer.json / merges.txt / generation_config.json.
# Vocab is IPA phonemes inside config.json; G2P is the misaki package.
KOKORO_REPO = "hexgrad/Kokoro-82M"
KOKORO_DEFAULT_VOICE = "af_heart"
KOKORO_LANGUAGES = ["en", "ja", "zh", "es", "fr", "hi", "it", "pt"]
KOKORO_VOICE_GROUPS = (
    ("a", "American English"),
    ("b", "British English"),
    ("j", "Japanese"),
    ("z", "Mandarin Chinese"),
    ("e", "Spanish"),
    ("f", "French"),
    ("h", "Hindi"),
    ("i", "Italian"),
    ("p", "Brazilian Portuguese"),
)

# Voicepack stems from hexgrad/Kokoro-82M/voices. Prefix is language+gender:
# a=en-US, b=en-GB, j=ja, z=zh, e=es, f=fr, h=hi, i=it, p=pt-BR; f=female, m=male.
KOKORO_VOICES = (
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_bella",
    "af_jessica",
    "af_kore",
    "af_nicole",
    "af_nova",
    "af_river",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",
    "jf_alpha",
    "jf_gongitsune",
    "jf_nezumi",
    "jf_tebukuro",
    "jm_kumo",
    "zf_xiaobei",
    "zf_xiaoni",
    "zf_xiaoxiao",
    "zf_xiaoyi",
    "zm_yunjian",
    "zm_yunxi",
    "zm_yunxia",
    "zm_yunyang",
    "ef_dora",
    "em_alex",
    "em_santa",
    "ff_siwis",
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",
    "if_sara",
    "im_nicola",
    "pf_dora",
    "pm_alex",
    "pm_santa",
)

KOKORO_FILES = (
    "config.json",
    "kokoro-v1_0.pth",
    *(f"voices/{name}.pt" for name in KOKORO_VOICES),
)


def format_named_voices(info: ModelInfo) -> str:
    """Pretty-print built-in speakers for CLI ``show``."""
    voices = info.named_voices()
    if not voices:
        return ""
    default = info.default_named_voice()
    if info.backend == "kokoro":
        grouped: dict[str, list[str]] = {}
        for name in voices:
            grouped.setdefault(name[0], []).append(name)
        lines: list[str] = []
        for code, label in KOKORO_VOICE_GROUPS:
            names = grouped.get(code)
            if not names:
                continue
            pretty = [f"{n}*" if n == default else n for n in names]
            lines.append(f"  {label} ({code}): {', '.join(pretty)}")
        if default:
            lines.append(f"  * default ({default})")
        return "\n".join(lines)
    pretty = [f"{n}*" if n == default else n for n in voices]
    lines = [f"  {', '.join(pretty)}"]
    if default:
        lines.append(f"  * default ({default})")
    return "\n".join(lines)


def _qwen(
    name: str,
    repo: str,
    description: str,
    model_kwargs: dict[str, Any],
    vram: str,
) -> ModelInfo:
    return ModelInfo(
        namespace=QWEN_NAMESPACE,
        name=name,
        tag="latest",
        backend="qwen",
        description=description,
        license=QWEN_LICENSE,
        license_url=QWEN_LICENSE_URL,
        huggingface_repo=repo,
        model_class="Qwen3TTSModel",
        model_kwargs=dict(model_kwargs),
        layers=_layers(repo, QWEN_FILES),
        recommended_device="cuda",
        vram_requirement=vram,
        languages=list(QWEN_LANGUAGES),
        sample_rate=24000,
    )


BUILT_IN_MODELS = {
    "chatterbox-turbo": ModelInfo(
        namespace=CHATTERBOX_NAMESPACE,
        name="chatterbox-turbo",
        tag="latest",
        backend="chatterbox",
        description="Chatterbox Turbo - 350M parameter English TTS model (MIT License)",
        license=CHATTERBOX_LICENSE,
        license_url=CHATTERBOX_LICENSE_URL,
        huggingface_repo=TURBO_REPO,
        model_class="ChatterboxTurboTTS",
        layers=_layers(TURBO_REPO, TURBO_FILES),
        recommended_device="cuda",
        vram_requirement="~2GB",
    ),
    "chatterbox-nano": ModelInfo(
        namespace=CHATTERBOX_NAMESPACE,
        name="chatterbox-nano",
        tag="latest",
        backend="chatterbox",
        description="Chatterbox Nano - 110M parameter English TTS, CPU-optimized (MIT License)",
        license=CHATTERBOX_LICENSE,
        license_url=CHATTERBOX_LICENSE_URL,
        huggingface_repo=NANO_REPO,
        model_class="ChatterboxTurboTTS",
        model_kwargs={"nano": True},
        layers=_layers(NANO_REPO, NANO_FILES),
        recommended_device="cpu",
        vram_requirement="~1GB",
    ),
    "chatterbox-base": ModelInfo(
        namespace=CHATTERBOX_NAMESPACE,
        name="chatterbox-base",
        tag="latest",
        backend="chatterbox",
        description="Chatterbox Base - 500M parameter English TTS model (MIT License)",
        license=CHATTERBOX_LICENSE,
        license_url=CHATTERBOX_LICENSE_URL,
        huggingface_repo=BASE_REPO,
        model_class="ChatterboxTTS",
        layers=_layers(BASE_REPO, BASE_FILES),
        recommended_device="cuda",
        vram_requirement="~3GB",
    ),
    "chatterbox-multilingual": ModelInfo(
        namespace=CHATTERBOX_NAMESPACE,
        name="chatterbox-multilingual",
        tag="latest",
        backend="chatterbox",
        description=(
            "Chatterbox Multilingual - 500M, 23 languages, MIT License"
        ),
        license=CHATTERBOX_LICENSE,
        license_url=CHATTERBOX_LICENSE_URL,
        huggingface_repo=MTL_REPO,
        model_class="ChatterboxMultilingualTTS",
        model_kwargs={"default_language": "en"},
        layers=_layers(MTL_REPO, MTL_FILES),
        recommended_device="cuda",
        vram_requirement="~4GB",
        languages=list(CHATTERBOX_MTL_LANGUAGES),
    ),
    "qwen-0.6-customvoice": _qwen(
        "qwen-0.6-customvoice",
        QWEN_0_6_CUSTOMVOICE_REPO,
        "Qwen3-TTS 0.6B CustomVoice - 9 named speakers, default Ryan (Apache-2.0)",
        QWEN_CUSTOMVOICE_KWARGS,
        "~3GB",
    ),
    "qwen-0.6-base": _qwen(
        "qwen-0.6-base",
        QWEN_0_6_BASE_REPO,
        "Qwen3-TTS 0.6B Base - voice cloning from reference audio (Apache-2.0)",
        QWEN_BASE_KWARGS,
        "~3GB",
    ),
    "qwen-1.7-customvoice": _qwen(
        "qwen-1.7-customvoice",
        QWEN_1_7_CUSTOMVOICE_REPO,
        "Qwen3-TTS 1.7B CustomVoice - named speakers + style instruct, default Ryan (Apache-2.0)",
        QWEN_CUSTOMVOICE_KWARGS,
        "~5GB",
    ),
    "qwen-1.7-base": _qwen(
        "qwen-1.7-base",
        QWEN_1_7_BASE_REPO,
        "Qwen3-TTS 1.7B Base - higher-quality voice cloning (Apache-2.0)",
        QWEN_BASE_KWARGS,
        "~5GB",
    ),
    "kokoro": ModelInfo(
        namespace=KOKORO_NAMESPACE,
        name="kokoro",
        tag="latest",
        backend="kokoro",
        description="Kokoro-82M - lightweight multilingual TTS, 54 named voices (Apache-2.0)",
        license=KOKORO_LICENSE,
        license_url=KOKORO_LICENSE_URL,
        huggingface_repo=KOKORO_REPO,
        model_class="KPipeline",
        model_kwargs={"default_voice": KOKORO_DEFAULT_VOICE},
        layers=_layers(KOKORO_REPO, KOKORO_FILES),
        recommended_device="cpu",
        vram_requirement="~500MB",
        languages=list(KOKORO_LANGUAGES),
        sample_rate=24000,
    ),
}


class ModelRegistry:
    """Thin wrapper over BUILT_IN_MODELS."""

    def __init__(self):
        self._models = BUILT_IN_MODELS.copy()

    def get_model_info(self, model_name: str) -> ModelInfo:
        info = self._models.get(model_name)
        if info is None:
            raise ModelNotFoundError(model_name)
        return info

    def get_model_info_safe(self, model_name: str) -> Optional[ModelInfo]:
        return self._models.get(model_name)

    def list_models(self) -> list[str]:
        return sorted(self._models.keys())

    def get_all_models(self) -> dict[str, ModelInfo]:
        return self._models.copy()

    def format_license_display(self, model_name: str) -> str:
        info = self.get_model_info(model_name)
        bar = "=" * 80
        return f"""
{bar}
MODEL: {info.name}
DESCRIPTION: {info.description}
{bar}

LICENSE: {info.license}

By using this model, you agree to the terms of the {info.license} license.

License details: {info.license_url}

Third-party model weights are subject to their respective licenses.
Wavhost (this software) is licensed under Apache-2.0.

{bar}
        """.strip()
