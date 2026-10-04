"""Tests for /v1/audio/speech streaming and non-stream paths."""

from unittest.mock import MagicMock

import pytest
import torch
from fastapi.testclient import TestClient

from wavhost.server import (
    STREAM_CHUNK_SIZE,
    STREAMABLE_FORMATS,
    AudioConverter,
    AudioFormat,
    app,
    clear_backend_cache,
    iter_audio_chunks,
)
from wavhost.voices import VoiceStorage


@pytest.fixture(autouse=True)
def isolate_backend_cache():
    """Speech API tests must not share process-global model backends."""
    clear_backend_cache()
    yield
    clear_backend_cache()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with voice storage on a temp path."""
    monkeypatch.setattr(
        "wavhost.server.VoiceStorage",
        lambda: VoiceStorage(base_path=tmp_path),
    )
    return TestClient(app)


@pytest.fixture
def mock_speech(tmp_path, monkeypatch):
    """Stub checkpoint + backend so speech tests never load a real model."""
    sample_rate = 24000
    # ~0.05s mono sine-ish noise so PCM is a few thousand bytes
    n = sample_rate // 20
    audio = (0.25 * torch.randn(1, n)).clamp(-1.0, 1.0)
    generate = MagicMock(return_value=(audio, sample_rate))
    backend = MagicMock()
    backend.generate = generate

    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()
    monkeypatch.setattr(
        "wavhost.server.WavhostStorage.ensure_checkpoint",
        lambda self, model_info: ckpt,
    )
    create_backend = MagicMock(return_value=backend)
    monkeypatch.setattr("wavhost.server.create_backend", create_backend)
    return {
        "generate": generate,
        "create_backend": create_backend,
        "audio": audio,
        "sample_rate": sample_rate,
    }


def test_speech_reuses_warm_backend(client, mock_speech):
    payload = {
        "model": "chatterbox-turbo",
        "input": "Hello",
        "response_format": "pcm",
    }
    first = client.post("/v1/audio/speech", json=payload)
    second = client.post("/v1/audio/speech", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    mock_speech["create_backend"].assert_called_once()
    assert mock_speech["generate"].call_count == 2


def test_backend_cache_can_be_disabled(client, mock_speech, monkeypatch):
    monkeypatch.setenv("WAVHOST_BACKEND_CACHE_SIZE", "0")
    payload = {
        "model": "chatterbox-turbo",
        "input": "Hello",
        "response_format": "pcm",
    }
    first = client.post("/v1/audio/speech", json=payload)
    second = client.post("/v1/audio/speech", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert mock_speech["create_backend"].call_count == 2


def test_backend_cache_lru_limit(client, mock_speech, monkeypatch):
    monkeypatch.setenv("WAVHOST_BACKEND_CACHE_SIZE", "1")
    base = {"input": "Hello", "response_format": "pcm"}

    first = client.post(
        "/v1/audio/speech", json={**base, "model": "chatterbox-turbo"}
    )
    second = client.post(
        "/v1/audio/speech", json={**base, "model": "qwen-0.6-customvoice"}
    )
    third = client.post(
        "/v1/audio/speech", json={**base, "model": "chatterbox-turbo"}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert mock_speech["create_backend"].call_count == 3


def test_server_device_override_puts_kokoro_on_cuda(client, mock_speech, monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setenv("WAVHOST_DEVICE", "cuda")
    response = client.post(
        "/v1/audio/speech",
        json={"model": "kokoro", "input": "Hello", "response_format": "pcm"},
    )

    assert response.status_code == 200
    assert mock_speech["create_backend"].call_args.kwargs["device"] == "cuda"


def test_explicit_cuda_does_not_silently_fall_back(client, mock_speech, monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setenv("WAVHOST_DEVICE", "cuda")
    response = client.post(
        "/v1/audio/speech",
        json={"model": "kokoro", "input": "Hello", "response_format": "pcm"},
    )

    assert response.status_code == 500
    assert "CUDA is not available" in response.json()["detail"]


def test_backend_cache_separates_server_devices(client, mock_speech, monkeypatch):
    payload = {"model": "chatterbox-turbo", "input": "Hello", "response_format": "pcm"}
    monkeypatch.setenv("WAVHOST_DEVICE", "cpu")
    assert client.post("/v1/audio/speech", json=payload).status_code == 200
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setenv("WAVHOST_DEVICE", "cuda")
    assert client.post("/v1/audio/speech", json=payload).status_code == 200

    assert mock_speech["create_backend"].call_count == 2
    assert [
        call.kwargs["device"] for call in mock_speech["create_backend"].call_args_list
    ] == ["cpu", "cuda"]


def test_invalid_server_device_fails_request(client, mock_speech, monkeypatch):
    monkeypatch.setenv("WAVHOST_DEVICE", "banana")
    response = client.post(
        "/v1/audio/speech",
        json={"model": "chatterbox-turbo", "input": "Hello", "response_format": "pcm"},
    )

    assert response.status_code == 500
    assert "WAVHOST_DEVICE" in response.json()["detail"]


def test_iter_audio_chunks_empty():
    assert list(iter_audio_chunks(b"")) == []


def test_iter_audio_chunks_short():
    data = b"abc"
    assert list(iter_audio_chunks(data, chunk_size=8)) == [b"abc"]


def test_iter_audio_chunks_multi():
    data = bytes(range(20))
    chunks = list(iter_audio_chunks(data, chunk_size=8))
    assert chunks == [data[0:8], data[8:16], data[16:20]]
    assert b"".join(chunks) == data


def test_streamable_formats_exclude_containers():
    assert AudioFormat.MP3 in STREAMABLE_FORMATS
    assert AudioFormat.PCM in STREAMABLE_FORMATS
    assert AudioFormat.PCM_24000 in STREAMABLE_FORMATS
    assert AudioFormat.WAV not in STREAMABLE_FORMATS
    assert AudioFormat.OPUS not in STREAMABLE_FORMATS
    assert AudioFormat.AAC not in STREAMABLE_FORMATS
    assert AudioFormat.FLAC not in STREAMABLE_FORMATS


def test_non_stream_pcm(client, mock_speech):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "voice": "default",
            "response_format": "pcm",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/pcm")
    expected = AudioConverter.convert(
        mock_speech["audio"], mock_speech["sample_rate"], AudioFormat.PCM
    )
    assert response.content == expected
    mock_speech["generate"].assert_called_once()


def test_non_stream_wav(client, mock_speech):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "response_format": "wav",
            "stream": False,
        },
    )
    assert response.status_code == 200
    assert "audio/wav" in response.headers["content-type"]
    expected = AudioConverter.convert(
        mock_speech["audio"], mock_speech["sample_rate"], AudioFormat.WAV
    )
    assert response.content == expected
    assert response.content[:4] == b"RIFF"


def test_stream_pcm(client, mock_speech):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "voice": "default",
            "stream": True,
            "response_format": "pcm",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/pcm")
    expected = AudioConverter.convert(
        mock_speech["audio"], mock_speech["sample_rate"], AudioFormat.PCM
    )
    assert response.content == expected
    chunks = list(iter_audio_chunks(expected, STREAM_CHUNK_SIZE))
    assert b"".join(chunks) == expected
    if len(expected) > STREAM_CHUNK_SIZE:
        assert len(chunks) > 1
        assert all(len(c) == STREAM_CHUNK_SIZE for c in chunks[:-1])


def test_stream_pcm_24000(client, mock_speech):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "stream": True,
            "response_format": "pcm_24000",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/pcm")
    expected = AudioConverter.convert(
        mock_speech["audio"], mock_speech["sample_rate"], AudioFormat.PCM_24000
    )
    assert response.content == expected


def test_stream_mp3_or_default(client, mock_speech, monkeypatch):
    """stream=true with mp3 (or default format) returns audio/mpeg."""
    fake_mp3 = b"ID3fake-mp3-payload" + b"\x00" * 100

    monkeypatch.setattr(
        "wavhost.server.AudioConverter.convert",
        staticmethod(
            lambda audio, sr, fmt: fake_mp3 if fmt == AudioFormat.MP3 else b"x"
        ),
    )

    streamed = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "stream": True,
            "response_format": "mp3",
        },
    )
    assert streamed.status_code == 200
    assert "audio/mpeg" in streamed.headers["content-type"]
    assert streamed.content == fake_mp3

    default_stream = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "stream": True,
        },
    )
    assert default_stream.status_code == 200
    assert "audio/mpeg" in default_stream.headers["content-type"]
    assert default_stream.content == fake_mp3

    non_stream = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "response_format": "mp3",
        },
    )
    assert non_stream.status_code == 200
    assert non_stream.content == fake_mp3


@pytest.mark.parametrize("fmt", ["wav", "opus", "aac", "flac"])
def test_stream_rejects_unsupported_formats(client, mock_speech, fmt):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "chatterbox-turbo",
            "input": "Hello",
            "stream": True,
            "response_format": fmt,
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "stream=true" in detail
    assert fmt in detail
    mock_speech["generate"].assert_not_called()


def test_models_list_includes_kokoro_speakers(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    models = {item["id"]: item for item in response.json()["data"]}
    assert "af_heart" in models["kokoro"]["speakers"]
    assert models["kokoro"]["default_voice"] == "af_heart"
    assert models["qwen-0.6-customvoice"]["default_voice"] == "Ryan"
    assert models["chatterbox-turbo"]["speakers"] == []
