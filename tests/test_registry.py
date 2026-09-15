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


def test_chatterbox_multilingual_registered():
    registry = ModelRegistry()
    mtl = registry.get_model_info("chatterbox-multilingual")
    assert mtl.backend == "chatterbox"
    assert mtl.model_class == "ChatterboxMultilingualTTS"
    assert mtl.model_kwargs.get("default_language") == "en"
    assert "fr" in mtl.languages and "zh" in mtl.languages
    assert any(layer.filename == "t3_mtl23ls_v2.safetensors" for layer in mtl.layers)
