"""Tests for model registry."""

import pytest

from wavhost.exceptions import ModelNotFoundError
from wavhost.registry import ModelInfo, ModelRegistry


def test_registry_list_models():
    """Test listing available models."""
    registry = ModelRegistry()
    models = registry.list_models()
    
    assert len(models) >= 5
    assert "chatterbox-turbo" in models
    assert "chatterbox-nano" in models
    assert "chatterbox-base" in models
    assert "chatterbox-multilingual" in models
    assert "qwen-0.6-customvoice" in models
    assert "qwen-0.6-base" in models
    assert "qwen-1.7-customvoice" in models
    assert "qwen-1.7-base" in models
    assert "kokoro" in models
    assert "qwen-0.6b" not in models
    assert "qwen-1.7b" not in models


def test_get_model_info():
    """Test getting model information."""
    registry = ModelRegistry()
    
    info = registry.get_model_info("chatterbox-turbo")
    assert isinstance(info, ModelInfo)
    assert info.name == "chatterbox-turbo"
    assert info.backend == "chatterbox"
    assert info.license == "MIT"
    assert info.namespace == "resemble"


def test_get_model_info_not_found():
    """Test getting nonexistent model raises error."""
    registry = ModelRegistry()
    
    with pytest.raises(ModelNotFoundError, match="nonexistent"):
        registry.get_model_info("nonexistent")


def test_get_model_info_safe():
    """Test safe model info retrieval."""
    registry = ModelRegistry()
    
    info = registry.get_model_info_safe("chatterbox-turbo")
    assert info is not None
    assert info.name == "chatterbox-turbo"
    
    info = registry.get_model_info_safe("nonexistent")
    assert info is None


def test_format_license_display():
    """Test license display formatting."""
    registry = ModelRegistry()
    
    license_text = registry.format_license_display("chatterbox-turbo")
    assert "MIT" in license_text
    assert "chatterbox-turbo" in license_text
    assert "Apache-2.0" in license_text


def test_format_license_display_not_found():
    """Test license display for nonexistent model."""
    registry = ModelRegistry()
    
    with pytest.raises(ModelNotFoundError):
        registry.format_license_display("nonexistent")


def test_model_info_full_name():
    """Test ModelInfo full name property."""
    registry = ModelRegistry()
    
    info = registry.get_model_info("chatterbox-turbo")
    assert info.full_name == "resemble/chatterbox-turbo:latest"


def test_model_info_to_dict():
    """Test ModelInfo to_dict conversion."""
    registry = ModelRegistry()
    
    info = registry.get_model_info("chatterbox-turbo")
    data = info.to_dict()
    
    assert isinstance(data, dict)
    assert data["name"] == "chatterbox-turbo"
    assert data["backend"] == "chatterbox"
    assert data["license"] == "MIT"
    assert isinstance(data["layers"], list)
    assert len(data["layers"]) > 0
    assert "filename" in data["layers"][0]
    assert "url" in data["layers"][0]


def test_model_layers_are_https_urls():
    """Layer URLs are plain HTTPS so hosts can be swapped without code changes."""
    registry = ModelRegistry()
    info = registry.get_model_info("chatterbox-turbo")
    assert all(layer.url.startswith("https://") for layer in info.layers)


def test_get_all_models():
    """Test getting all models."""
    registry = ModelRegistry()
    
    all_models = registry.get_all_models()
    assert isinstance(all_models, dict)
    assert len(all_models) >= 5
    assert "chatterbox-turbo" in all_models
    assert "chatterbox-nano" in all_models
    assert "qwen-0.6-customvoice" in all_models


def test_qwen_models_registered():
    """CustomVoice and Base Qwen variants are registered separately."""
    registry = ModelRegistry()

    custom = registry.get_model_info("qwen-0.6-customvoice")
    assert custom.backend == "qwen"
    assert custom.huggingface_repo.endswith("CustomVoice")
    assert custom.model_kwargs["task"] == "custom_voice"
    assert custom.model_kwargs["default_speaker"] == "Ryan"

    assert (
        registry.get_model_info("qwen-1.7-customvoice").model_kwargs["task"]
        == "custom_voice"
    )

    base = registry.get_model_info("qwen-0.6-base")
    assert base.huggingface_repo.endswith("Base")
    assert base.model_kwargs["task"] == "voice_clone"
    assert registry.get_model_info("qwen-1.7-base").model_kwargs["task"] == "voice_clone"



def test_chatterbox_nano_model_kwargs():
    """Test Chatterbox Nano uses nano=True via model_kwargs."""
    registry = ModelRegistry()
    nano = registry.get_model_info("chatterbox-nano")
    
    assert nano.backend == "chatterbox"
    assert nano.model_kwargs == {"nano": True}


def test_kokoro_registered():
    """Kokoro ships StyleTTS2 weights + voicepacks, not a Transformers tokenizer."""
    from wavhost.registry import KOKORO_DEFAULT_VOICE, KOKORO_VOICES

    registry = ModelRegistry()
    info = registry.get_model_info("kokoro")

    assert info.backend == "kokoro"
    assert info.namespace == "hexgrad"
    assert info.model_class == "KPipeline"
    assert info.huggingface_repo == "hexgrad/Kokoro-82M"
    assert info.model_kwargs["default_voice"] == KOKORO_DEFAULT_VOICE
    assert info.full_name == "hexgrad/kokoro:latest"
    assert info.sample_rate == 24000

    filenames = {layer.filename for layer in info.layers}
    assert "config.json" in filenames
    assert "kokoro-v1_0.pth" in filenames
    assert f"voices/{KOKORO_DEFAULT_VOICE}.pt" in filenames
    assert "model.safetensors" not in filenames
    assert "tokenizer.json" not in filenames
    assert len(info.layers) == 2 + len(KOKORO_VOICES)
    assert all(layer.url.startswith("https://huggingface.co/hexgrad/Kokoro-82M/") for layer in info.layers)


def test_chatterbox_multilingual_registered():
    registry = ModelRegistry()
    mtl = registry.get_model_info("chatterbox-multilingual")
    assert mtl.backend == "chatterbox"
    assert mtl.model_class == "ChatterboxMultilingualTTS"
    assert mtl.model_kwargs.get("default_language") == "en"
    assert "fr" in mtl.languages and "zh" in mtl.languages
    assert any(layer.filename == "t3_mtl23ls_v2.safetensors" for layer in mtl.layers)


def test_named_voices_by_backend():
    registry = ModelRegistry()

    kokoro = registry.get_model_info("kokoro")
    assert kokoro.default_named_voice() == "af_heart"
    assert "af_heart" in kokoro.named_voices()
    assert "bm_george" in kokoro.named_voices()
    assert len(kokoro.named_voices()) == 54

    qwen = registry.get_model_info("qwen-0.6-customvoice")
    assert qwen.default_named_voice() == "Ryan"
    assert "Aiden" in qwen.named_voices()

    clone = registry.get_model_info("qwen-0.6-base")
    assert clone.named_voices() == ()

    turbo = registry.get_model_info("chatterbox-turbo")
    assert turbo.named_voices() == ()
    assert turbo.default_named_voice() is None


def test_format_named_voices_groups_kokoro():
    from wavhost.registry import format_named_voices

    registry = ModelRegistry()
    text = format_named_voices(registry.get_model_info("kokoro"))
    assert "American English (a):" in text
    assert "af_heart*" in text
    assert "bm_george" in text
    assert "* default (af_heart)" in text
