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
    assert "qwen-0.6b" in models
    assert "qwen-1.7b" in models


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
    assert "qwen-0.6b" in all_models


def test_qwen_models_info():
    """Test Qwen model information."""
    registry = ModelRegistry()
    
    qwen_06b = registry.get_model_info("qwen-0.6b")
    assert qwen_06b.name == "qwen-0.6b"
    assert qwen_06b.backend == "qwen"
    assert qwen_06b.license == "Apache-2.0"
    assert qwen_06b.namespace == "qwen"
    assert qwen_06b.sample_rate == 24000
    assert len(qwen_06b.languages) == 10
    assert "en" in qwen_06b.languages
    assert "zh" in qwen_06b.languages
    
    qwen_17b = registry.get_model_info("qwen-1.7b")
    assert qwen_17b.name == "qwen-1.7b"
    assert qwen_17b.backend == "qwen"
    assert qwen_17b.vram_requirement == "~5GB"


def test_chatterbox_nano_model_info():
    """Test Chatterbox Nano model information."""
    registry = ModelRegistry()
    
    nano = registry.get_model_info("chatterbox-nano")
    assert nano.name == "chatterbox-nano"
    assert nano.backend == "chatterbox"
    assert nano.license == "MIT"
    assert nano.namespace == "resemble"
    assert nano.model_class == "ChatterboxTurboTTS"
    assert nano.model_kwargs == {"nano": True}
    assert nano.recommended_device == "cpu"
    assert nano.vram_requirement == "~1GB"
