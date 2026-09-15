"""Tests for voice management."""

from pathlib import Path

import pytest

from wavhost.voices import (
    VoiceAlreadyExistsError,
    VoiceError,
    VoiceNotFoundError,
    VoiceStorage,
)


@pytest.fixture
def voice_storage(tmp_path):
    """Voice storage with temp directory."""
    return VoiceStorage(base_path=tmp_path)


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file for testing."""
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"FAKE_AUDIO_DATA")
    return audio_file


def test_voice_storage_initialization(tmp_path):
    """Test voice storage initialization."""
    storage = VoiceStorage(base_path=tmp_path)
    
    assert storage.voices_path.exists()
    assert storage.manifests_path.exists()
    assert storage.blobs_path.exists()


def test_create_voice(voice_storage, sample_audio):
    """Test creating a new voice."""
    manifest = voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
        description="Test voice",
    )
    
    assert manifest["name"] == "test-voice"
    assert manifest["description"] == "Test voice"
    assert manifest["backend"] == "chatterbox"
    assert "ref_audio" in manifest
    assert manifest["ref_audio"]["original_filename"] == "sample.wav"


def test_create_voice_duplicate_raises_error(voice_storage, sample_audio):
    """Test creating duplicate voice raises error."""
    voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
    )
    
    with pytest.raises(VoiceAlreadyExistsError):
        voice_storage.create_voice(
            name="test-voice",
            ref_audio_path=sample_audio,
        )


def test_create_voice_missing_audio_raises_error(voice_storage, tmp_path):
    """Test creating voice with missing audio raises error."""
    missing_file = tmp_path / "missing.wav"
    
    with pytest.raises(VoiceError, match="Reference audio not found"):
        voice_storage.create_voice(
            name="test-voice",
            ref_audio_path=missing_file,
        )


def test_create_voice_invalid_name_raises_error(voice_storage, sample_audio):
    """Test creating voice with invalid name raises error."""
    # Empty names
    with pytest.raises(VoiceError, match="cannot be empty"):
        voice_storage.create_voice(name="", ref_audio_path=sample_audio)
    
    with pytest.raises(VoiceError, match="cannot be empty"):
        voice_storage.create_voice(name="  ", ref_audio_path=sample_audio)
    
    # Path separators
    invalid_names = [
        "test/voice",
        "test\\voice",
        "../voice",
    ]
    for name in invalid_names:
        with pytest.raises(VoiceError, match="cannot contain path separators"):
            voice_storage.create_voice(name=name, ref_audio_path=sample_audio)
    
    # Hidden files
    with pytest.raises(VoiceError, match="cannot start with"):
        voice_storage.create_voice(name=".hidden", ref_audio_path=sample_audio)


def test_get_voice(voice_storage, sample_audio):
    """Test retrieving a voice."""
    voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
        description="Test voice",
    )
    
    manifest = voice_storage.get_voice("test-voice")
    
    assert manifest["name"] == "test-voice"
    assert manifest["description"] == "Test voice"


def test_get_voice_not_found_raises_error(voice_storage):
    """Test getting non-existent voice raises error."""
    with pytest.raises(VoiceNotFoundError):
        voice_storage.get_voice("missing-voice")


def test_get_voice_ref_audio_path(voice_storage, sample_audio):
    """Test getting reference audio path."""
    voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
    )
    
    ref_path = voice_storage.get_voice_ref_audio_path("test-voice")
    
    assert ref_path.exists()
    assert ref_path.read_bytes() == b"FAKE_AUDIO_DATA"


def test_list_voices_empty(voice_storage):
    """Test listing voices when none exist."""
    voices = voice_storage.list_voices()
    assert voices == []


def test_list_voices(voice_storage, sample_audio):
    """Test listing multiple voices."""
    voice_storage.create_voice(
        name="voice-a",
        ref_audio_path=sample_audio,
        description="Voice A",
    )
    voice_storage.create_voice(
        name="voice-b",
        ref_audio_path=sample_audio,
        description="Voice B",
    )
    
    voices = voice_storage.list_voices()
    
    assert len(voices) == 2
    assert voices[0]["name"] == "voice-a"
    assert voices[1]["name"] == "voice-b"


def test_voice_exists(voice_storage, sample_audio):
    """Test checking if voice exists."""
    assert not voice_storage.voice_exists("test-voice")
    
    voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
    )
    
    assert voice_storage.voice_exists("test-voice")


def test_delete_voice(voice_storage, sample_audio):
    """Test deleting a voice."""
    voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
    )
    
    assert voice_storage.voice_exists("test-voice")
    
    deleted = voice_storage.delete_voice("test-voice")
    
    assert deleted is True
    assert not voice_storage.voice_exists("test-voice")


def test_delete_voice_not_found(voice_storage):
    """Test deleting non-existent voice returns False."""
    deleted = voice_storage.delete_voice("missing-voice")
    assert deleted is False


def test_delete_voice_prunes_unused_blob(voice_storage, sample_audio):
    """Test deleting voice removes unreferenced blob."""
    voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
    )
    
    manifest = voice_storage.get_voice("test-voice")
    digest = manifest["ref_audio"]["digest"]
    blob_path = voice_storage._get_blob_path(digest)
    
    assert blob_path.exists()
    
    voice_storage.delete_voice("test-voice")
    
    # Blob should be removed since no other voice references it
    assert not blob_path.exists()


def test_delete_voice_keeps_shared_blob(voice_storage, sample_audio):
    """Test deleting voice keeps blob if another voice uses it."""
    # Create two voices with the same reference audio
    voice_storage.create_voice(
        name="voice-a",
        ref_audio_path=sample_audio,
    )
    voice_storage.create_voice(
        name="voice-b",
        ref_audio_path=sample_audio,
    )
    
    manifest = voice_storage.get_voice("voice-a")
    digest = manifest["ref_audio"]["digest"]
    blob_path = voice_storage._get_blob_path(digest)
    
    assert blob_path.exists()
    
    # Delete one voice
    voice_storage.delete_voice("voice-a")
    
    # Blob should still exist because voice-b references it
    assert blob_path.exists()
    
    # Delete second voice
    voice_storage.delete_voice("voice-b")
    
    # Now blob should be removed
    assert not blob_path.exists()


def test_content_addressed_storage(voice_storage, tmp_path):
    """Test that identical audio files are deduplicated."""
    # Create two identical audio files with different names
    audio1 = tmp_path / "audio1.wav"
    audio2 = tmp_path / "audio2.wav"
    audio1.write_bytes(b"IDENTICAL_DATA")
    audio2.write_bytes(b"IDENTICAL_DATA")
    
    voice_storage.create_voice(
        name="voice-1",
        ref_audio_path=audio1,
    )
    voice_storage.create_voice(
        name="voice-2",
        ref_audio_path=audio2,
    )
    
    # Both voices should reference the same blob
    manifest1 = voice_storage.get_voice("voice-1")
    manifest2 = voice_storage.get_voice("voice-2")
    
    assert manifest1["ref_audio"]["digest"] == manifest2["ref_audio"]["digest"]
    
    # Should only have one blob file
    blobs = list(voice_storage.blobs_path.glob("*"))
    assert len(blobs) == 1


def test_voice_metadata(voice_storage, sample_audio):
    """Test storing custom metadata with voice."""
    metadata = {
        "custom_field": "value",
        "version": 1,
    }
    
    voice_storage.create_voice(
        name="test-voice",
        ref_audio_path=sample_audio,
        metadata=metadata,
    )
    
    manifest = voice_storage.get_voice("test-voice")
    assert manifest["metadata"] == metadata
