"""Model registry with built-in model definitions."""

from dataclasses import dataclass, field
from typing import Any, Optional

from wavhost.exceptions import ModelNotFoundError
from wavhost.logging_config import get_logger

logger = get_logger(__name__)


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


CHATTERBOX_LICENSE_URL = "https://github.com/resemble-ai/chatterbox/blob/main/LICENSE"
CHATTERBOX_NAMESPACE = "resemble"
CHATTERBOX_LICENSE = "MIT"

QWEN_LICENSE_URL = "https://github.com/QwenLM/Qwen3-TTS/blob/main/LICENSE"
QWEN_NAMESPACE = "qwen"
QWEN_LICENSE = "Apache-2.0"


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

BASE_REPO = "ResembleAI/chatterbox"
BASE_FILES = (
    "ve.safetensors",
    "t3_cfg.safetensors",
    "s3gen.safetensors",
    "tokenizer.json",
    "conds.pt",
)

QWEN_0_6B_REPO = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
QWEN_0_6B_FILES = (
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

QWEN_1_7B_REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
QWEN_1_7B_FILES = (
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
    "qwen-0.6b": ModelInfo(
        namespace=QWEN_NAMESPACE,
        name="qwen-0.6b",
        tag="latest",
        backend="qwen",
        description="Qwen3-TTS 0.6B - Multilingual voice cloning model (Apache-2.0 License)",
        license=QWEN_LICENSE,
        license_url=QWEN_LICENSE_URL,
        huggingface_repo=QWEN_0_6B_REPO,
        model_class="Qwen3TTSModel",
        layers=_layers(QWEN_0_6B_REPO, QWEN_0_6B_FILES),
        recommended_device="cuda",
        vram_requirement="~3GB",
        languages=["en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"],
        sample_rate=24000,
    ),
    "qwen-1.7b": ModelInfo(
        namespace=QWEN_NAMESPACE,
        name="qwen-1.7b",
        tag="latest",
        backend="qwen",
        description="Qwen3-TTS 1.7B - Multilingual voice cloning model (Apache-2.0 License)",
        license=QWEN_LICENSE,
        license_url=QWEN_LICENSE_URL,
        huggingface_repo=QWEN_1_7B_REPO,
        model_class="Qwen3TTSModel",
        layers=_layers(QWEN_1_7B_REPO, QWEN_1_7B_FILES),
        recommended_device="cuda",
        vram_requirement="~5GB",
        languages=["en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"],
        sample_rate=24000,
    ),
}


class ModelRegistry:
    """Registry for available TTS models."""

    def __init__(self):
        """Initialize model registry with built-in models."""
        self._models = BUILT_IN_MODELS.copy()
        logger.debug(f"Registry initialized with {len(self._models)} models")

    def get_model_info(self, model_name: str) -> ModelInfo:
        """Get information about a model.

        Args:
            model_name: Name of the model (e.g., 'chatterbox-turbo')

        Returns:
            Model information object

        Raises:
            ModelNotFoundError: If model is not in registry
        """
        model_info = self._models.get(model_name)
        if model_info is None:
            raise ModelNotFoundError(model_name)
        return model_info

    def get_model_info_safe(self, model_name: str) -> Optional[ModelInfo]:
        """Get model information without raising an exception.

        Args:
            model_name: Name of the model

        Returns:
            Model information or None if not found
        """
        return self._models.get(model_name)

    def list_models(self) -> list[str]:
        """List all available model names in alphabetical order.

        Returns:
            Sorted list of model names
        """
        return sorted(self._models.keys())

    def get_all_models(self) -> dict[str, ModelInfo]:
        """Get all available models.

        Returns:
            Dictionary mapping model names to ModelInfo objects
        """
        return self._models.copy()

    def format_license_display(self, model_name: str) -> str:
        """Get formatted license information for a model.

        Args:
            model_name: Name of the model

        Returns:
            Formatted license text

        Raises:
            ModelNotFoundError: If model is not in registry
        """
        model_info = self.get_model_info(model_name)

        separator = "=" * 80

        return f"""
{separator}
MODEL: {model_info.name}
DESCRIPTION: {model_info.description}
{separator}

LICENSE: {model_info.license}

By using this model, you agree to the terms of the {model_info.license} license.

License details: {model_info.license_url}

Third-party model weights are subject to their respective licenses.
Wavhost (this software) is licensed under Apache-2.0.

{separator}
        """.strip()
