"""Tests for voice management API endpoints."""

import io
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from wavhost.server import app
from wavhost.voices import VoiceStorage


@pytest.fixture
def temp_voice_storage(tmp_path, monkeypatch):
    """Patch voice storage to use temp directory."""
    def get_voice_storage():
        return VoiceStorage(base_path=tmp_path)
    
    # Patch VoiceStorage() calls in server.py to use temp directory
    monkeypatch.setattr(
        "wavhost.server.VoiceStorage",
        lambda: get_voice_storage()
    )
    
    return get_voice_storage()


@pytest.fixture
def client(temp_voice_storage):
    """Test client for API."""
    return TestClient(app)


@pytest.fixture
def sample_audio_bytes():
    """Sample audio file content."""
    return b"FAKE_WAV_DATA_FOR_TESTING"


def test_list_voices_empty(client):
    """Test listing voices when none exist."""
    response = client.get("/v1/voices")
    
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert data["data"] == []


def test_create_voice(client, sample_audio_bytes):
    """Test creating a new voice via API."""
    response = client.post(
        "/v1/voices",
        data={
            "name": "test-voice",
            "description": "Test voice"
        },
        files={
            "file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-voice"
    assert "created successfully" in data["message"]


def test_create_voice_duplicate(client, sample_audio_bytes):
    """Test creating duplicate voice returns error."""
    # Create first voice
    client.post(
        "/v1/voices",
        data={"name": "test-voice"},
        files={"file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")}
    )
    
    # Try to create duplicate
    response = client.post(
        "/v1/voices",
        data={"name": "test-voice"},
        files={"file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")}
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_voice_without_file(client):
    """Test creating voice without file returns error."""
    response = client.post(
        "/v1/voices",
        data={"name": "test-voice"}
    )
    
    assert response.status_code == 422  # Validation error


def test_list_voices_after_creation(client, sample_audio_bytes):
    """Test listing voices after creating some."""
    # Create voices
    for i in range(3):
        client.post(
            "/v1/voices",
            data={
                "name": f"voice-{i}",
                "description": f"Voice {i}"
            },
            files={
                "file": (f"test{i}.wav", io.BytesIO(sample_audio_bytes), "audio/wav")
            }
        )
    
    response = client.get("/v1/voices")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3
    assert data["data"][0]["name"] == "voice-0"
    assert data["data"][0]["description"] == "Voice 0"


def test_get_voice(client, sample_audio_bytes):
    """Test getting voice details."""
    # Create voice
    client.post(
        "/v1/voices",
        data={
            "name": "test-voice",
            "description": "Test description"
        },
        files={
            "file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")
        }
    )
    
    response = client.get("/v1/voices/test-voice")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-voice"
    assert data["description"] == "Test description"
    assert data["backend"] == "chatterbox"
    assert "ref_audio" in data


def test_get_voice_not_found(client):
    """Test getting non-existent voice returns 404."""
    response = client.get("/v1/voices/missing-voice")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_delete_voice(client, sample_audio_bytes):
    """Test deleting a voice."""
    # Create voice
    client.post(
        "/v1/voices",
        data={"name": "test-voice"},
        files={"file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")}
    )
    
    # Delete voice
    response = client.delete("/v1/voices/test-voice")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-voice"
    assert data["deleted"] is True
    
    # Verify it's gone
    response = client.get("/v1/voices/test-voice")
    assert response.status_code == 404


def test_delete_voice_not_found(client):
    """Test deleting non-existent voice returns 404."""
    response = client.delete("/v1/voices/missing-voice")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_voice_api_integration(client, sample_audio_bytes):
    """Test full voice API workflow."""
    # 1. List voices (empty)
    response = client.get("/v1/voices")
    assert len(response.json()["data"]) == 0
    
    # 2. Create voice
    response = client.post(
        "/v1/voices",
        data={
            "name": "my-voice",
            "description": "Custom voice"
        },
        files={
            "file": ("voice.wav", io.BytesIO(sample_audio_bytes), "audio/wav")
        }
    )
    assert response.status_code == 200
    
    # 3. List voices (should have 1)
    response = client.get("/v1/voices")
    assert len(response.json()["data"]) == 1
    
    # 4. Get voice details
    response = client.get("/v1/voices/my-voice")
    assert response.status_code == 200
    assert response.json()["name"] == "my-voice"
    
    # 5. Delete voice
    response = client.delete("/v1/voices/my-voice")
    assert response.status_code == 200
    
    # 6. List voices (empty again)
    response = client.get("/v1/voices")
    assert len(response.json()["data"]) == 0


def test_create_voice_with_invalid_name(client, sample_audio_bytes):
    """Test creating voice with invalid name."""
    invalid_names = [
        "test/voice",
        "test\\voice",
        "../voice",
        ".hidden",
    ]
    
    for name in invalid_names:
        response = client.post(
            "/v1/voices",
            data={"name": name},
            files={
                "file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")
            }
        )
        assert response.status_code == 400, f"Expected 400 for name '{name}', got {response.status_code}"
