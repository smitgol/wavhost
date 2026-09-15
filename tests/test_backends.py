"""Tests for TTS backends."""

import inspect

import pytest
import torch

from wavhost import dependencies
from wavhost.backends import BACKEND_NAME, ChatterboxBackend, create_backend
from wavhost.config import CPU_DEVICE, DEFAULT_SAMPLE_RATE
from wavhost.exceptions import BackendError
from wavhost.registry import ModelRegistry

requires_engine = pytest.mark.skipif(
    not dependencies.is_installed(BACKEND_NAME),
    reason="Requires the chatterbox engine"
)


@pytest.fixture
def checkpoint(tmp_path):
    """Empty local checkpoint directory for backend construction."""
    path = tmp_path / "ckpt"
    path.mkdir()
    return path


@requires_engine
def test_registry_models_have_from_local_loaders():
    """Every Chatterbox model class must expose from_local(ckpt_dir, device)."""
    from chatterbox.tts import ChatterboxTTS
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    loaders = {
        "ChatterboxTTS": ChatterboxTTS.from_local,
        "ChatterboxTurboTTS": ChatterboxTurboTTS.from_local,
    }

    registry = ModelRegistry()

    for name in registry.list_models():
        model_info = registry.get_model_info(name)
        if model_info.backend != BACKEND_NAME:
            continue

        assert model_info.model_class in loaders
        signature = inspect.signature(loaders[model_info.model_class])
        params = list(signature.parameters)
        assert params[:2] == ["ckpt_dir", "device"], (
            f"{model_info.model_class}.from_local signature changed: {params}"
        )


@requires_engine
def test_registry_model_classes_exist():
    """Each model names a class the installed engine actually provides."""
    import chatterbox.tts
    import chatterbox.tts_turbo

    registry = ModelRegistry()

    for name in registry.list_models():
        model_info = registry.get_model_info(name)
        if model_info.backend != BACKEND_NAME:
            continue

        assert (
            hasattr(chatterbox.tts, model_info.model_class)
            or hasattr(chatterbox.tts_turbo, model_info.model_class)
        ), f"Model '{name}' names unknown class '{model_info.model_class}'"


def test_registry_models_declare_layers():
    """Every built-in model must list downloadable layers."""
    registry = ModelRegistry()
    for name in registry.list_models():
        info = registry.get_model_info(name)
        assert len(info.layers) > 0
        for layer in info.layers:
            assert layer.filename
            assert layer.url.startswith("https://")


def test_backend_creation(checkpoint):
    """Test backend factory function."""
    registry = ModelRegistry()
    model_info = registry.get_model_info("chatterbox-turbo")

    backend = create_backend(
        model_info, device=CPU_DEVICE, checkpoint_path=checkpoint
    )
    assert isinstance(backend, ChatterboxBackend)
    assert backend.sample_rate == DEFAULT_SAMPLE_RATE


def test_backend_creation_requires_checkpoint():
    """create_backend refuses to call from_pretrained / HF Hub."""
    registry = ModelRegistry()
    model_info = registry.get_model_info("chatterbox-turbo")

    with pytest.raises(BackendError, match="checkpoint_path"):
        create_backend(model_info, device=CPU_DEVICE)


def test_backend_creation_with_device_override(checkpoint):
    """Test backend creation with device override."""
    registry = ModelRegistry()
    model_info = registry.get_model_info("chatterbox-base")

    backend = create_backend(
        model_info, device=CPU_DEVICE, checkpoint_path=checkpoint
    )
    assert backend._device == CPU_DEVICE


def test_invalid_backend_type(checkpoint):
    """Test invalid backend type raises error."""
    from wavhost.registry import ModelInfo

    invalid_model = ModelInfo(
        namespace="test",
        name="test",
        tag="latest",
        backend="invalid_backend",
        description="Test",
        license="MIT",
        license_url="http://example.com",
        model_class="Test",
    )

    with pytest.raises(BackendError, match="Unsupported backend type"):
        create_backend(invalid_model, checkpoint_path=checkpoint)


def test_chatterbox_backend_initialization(checkpoint):
    """Test Chatterbox backend initialization."""
    backend = ChatterboxBackend(
        model_class="ChatterboxTurboTTS",
        checkpoint_path=checkpoint,
        device=CPU_DEVICE,
    )

    assert backend._device == CPU_DEVICE
    assert backend.sample_rate == DEFAULT_SAMPLE_RATE
    assert backend._model is None


def test_chatterbox_backend_invalid_model_class(checkpoint):
    """Test Chatterbox backend with invalid model class."""
    with pytest.raises(BackendError, match="Invalid model class"):
        ChatterboxBackend(
            model_class="InvalidClass",
            checkpoint_path=checkpoint,
            device=CPU_DEVICE,
        )


def test_chatterbox_backend_missing_checkpoint(tmp_path):
    """A missing checkpoint directory fails at construction."""
    with pytest.raises(BackendError, match="Checkpoint directory not found"):
        ChatterboxBackend(
            model_class="ChatterboxTurboTTS",
            checkpoint_path=tmp_path / "missing",
            device=CPU_DEVICE,
        )


def test_chatterbox_backend_device_detection(checkpoint):
    """Test automatic device detection."""
    backend = ChatterboxBackend(
        model_class="ChatterboxTurboTTS",
        checkpoint_path=checkpoint,
        device=None,
    )

    assert backend._device in ["cuda", "cpu", "mps"]


class _FakeModel:
    """Stand-in for a Chatterbox model that records how it was called."""

    sr = DEFAULT_SAMPLE_RATE

    def __init__(self):
        self.generate_kwargs = None

    def generate(self, text, **kwargs):
        self.generate_kwargs = kwargs
        return torch.zeros(1, 16)


def _backend_with_fake_model(monkeypatch, checkpoint):
    """Build a backend whose model is already loaded with a fake."""
    monkeypatch.setattr(
        "wavhost.backends.dependencies.is_installed",
        lambda backend: True,
    )

    backend = ChatterboxBackend(
        model_class="ChatterboxTurboTTS",
        checkpoint_path=checkpoint,
        device=CPU_DEVICE,
    )
    backend._model = _FakeModel()
    return backend


@requires_engine
def test_load_model_calls_from_local(monkeypatch, checkpoint):
    """Loading uses from_local with the checkpoint path — never HF Hub."""
    import chatterbox.tts_turbo

    recorded = {}

    def fake_from_local(ckpt_dir, device):
        recorded["ckpt_dir"] = str(ckpt_dir)
        recorded["device"] = device
        return _FakeModel()

    monkeypatch.setattr(
        chatterbox.tts_turbo.ChatterboxTurboTTS,
        "from_local",
        fake_from_local,
    )

    registry = ModelRegistry()
    backend = create_backend(
        registry.get_model_info("chatterbox-turbo"),
        device=CPU_DEVICE,
        checkpoint_path=checkpoint,
    )
    backend._load_model()

    assert recorded == {
        "ckpt_dir": str(checkpoint),
        "device": CPU_DEVICE,
    }


def test_generate_forwards_voice_as_audio_prompt_path(monkeypatch, checkpoint, tmp_path):
    """Voice cloning uses the audio_prompt_path argument Chatterbox exposes."""
    voice_file = tmp_path / "reference.wav"
    voice_file.write_bytes(b"")

    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    backend.generate("Hello world", voice=str(voice_file))

    assert backend._model.generate_kwargs == {"audio_prompt_path": str(voice_file)}


def test_generate_without_voice_passes_no_prompt(monkeypatch, checkpoint):
    """Omitting a voice leaves the model's built-in voice in place."""
    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    backend.generate("Hello world")

    assert backend._model.generate_kwargs == {}


def test_generate_with_voice_handle(monkeypatch, checkpoint, tmp_path):
    """Voice handle with ref_audio_path is used for generation."""
    voice_file = tmp_path / "voice.wav"
    voice_file.write_bytes(b"")
    
    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    voice_handle = {"ref_audio_path": str(voice_file)}
    backend.generate("Hello world", voice_handle=voice_handle)
    
    assert backend._model.generate_kwargs == {"audio_prompt_path": str(voice_file)}


def test_generate_voice_handle_overrides_voice_param(monkeypatch, checkpoint, tmp_path):
    """Voice handle takes precedence over voice parameter."""
    voice_file = tmp_path / "voice.wav"
    other_file = tmp_path / "other.wav"
    voice_file.write_bytes(b"")
    other_file.write_bytes(b"")
    
    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    voice_handle = {"ref_audio_path": str(voice_file)}
    backend.generate("Hello world", voice=str(other_file), voice_handle=voice_handle)
    
    # Should use voice_handle, not voice
    assert backend._model.generate_kwargs == {"audio_prompt_path": str(voice_file)}


def test_generate_invalid_voice_handle_raises_error(monkeypatch, checkpoint):
    """Invalid voice handle raises clear error."""
    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    
    with pytest.raises(BackendError, match="Invalid voice handle"):
        backend.generate("Hello world", voice_handle={"invalid": "data"})


def test_generate_voice_handle_missing_file_raises_error(monkeypatch, checkpoint, tmp_path):
    """Voice handle with missing file raises error."""
    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    voice_handle = {"ref_audio_path": str(tmp_path / "missing.wav")}
    
    with pytest.raises(BackendError, match="Voice reference audio not found"):
        backend.generate("Hello world", voice_handle=voice_handle)


def test_create_voice_returns_handle(monkeypatch, checkpoint, tmp_path):
    """create_voice returns a voice handle dict."""
    voice_file = tmp_path / "voice.wav"
    voice_file.write_bytes(b"")
    
    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    handle = backend.create_voice(str(voice_file))
    
    assert handle == {"ref_audio_path": str(voice_file)}


def test_create_voice_missing_file_raises_error(monkeypatch, checkpoint, tmp_path):
    """create_voice with missing file raises error."""
    backend = _backend_with_fake_model(monkeypatch, checkpoint)
    
    with pytest.raises(BackendError, match="Reference audio not found"):
        backend.create_voice(str(tmp_path / "missing.wav"))


def test_generate_rejects_missing_voice_file(monkeypatch, checkpoint):
    """A reference voice that isn't on disk fails loudly rather than silently."""
    backend = _backend_with_fake_model(monkeypatch, checkpoint)

    with pytest.raises(BackendError, match="Reference voice audio not found"):
        backend.generate("Hello world", voice="no-such-file.wav")


def test_chatterbox_backend_reports_missing_engine(monkeypatch, checkpoint):
    """Generating without the engine installed points at `wavhost pull`."""
    monkeypatch.setattr(
        "wavhost.backends.dependencies.is_installed",
        lambda backend: False,
    )

    backend = ChatterboxBackend(
        model_class="ChatterboxTurboTTS",
        checkpoint_path=checkpoint,
        device=CPU_DEVICE,
    )

    with pytest.raises(BackendError, match="wavhost pull"):
        backend.generate("Hello world")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires CUDA")
def test_chatterbox_backend_cuda(checkpoint):
    """Test Chatterbox backend with CUDA."""
    backend = ChatterboxBackend(
        model_class="ChatterboxTurboTTS",
        checkpoint_path=checkpoint,
        device="cuda",
    )

    assert backend._device == "cuda"
