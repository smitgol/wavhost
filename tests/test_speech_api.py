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
    iter_audio_chunks,
)
from wavhost.voices import VoiceStorage


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
    monkeypatch.setattr(
        "wavhost.server.create_backend",
        lambda *args, **kwargs: backend,
    )
    return {"generate": generate, "audio": audio, "sample_rate": sample_rate}


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
    assert len(response.content) > 0


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
