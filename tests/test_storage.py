"""Tests for storage layer."""

import json
import tempfile
from pathlib import Path

import pytest

from wavhost.exceptions import StorageError
from wavhost.storage import WavhostStorage


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield WavhostStorage(base_path=Path(tmpdir))


def test_storage_initialization(temp_storage):
    """Test storage directory initialization."""
    assert temp_storage.base_path.exists()
    assert temp_storage.manifests_path.exists()
    assert temp_storage.blobs_path.exists()


def test_blob_storage(temp_storage, tmp_path):
    """Test storing and retrieving blobs."""
    test_file = tmp_path / "test.txt"
    test_content = b"Hello, Wavhost!"
    test_file.write_bytes(test_content)
    
    digest = temp_storage.store_blob(test_file, show_progress=False)
    
    assert len(digest) == 64
    assert temp_storage.blob_exists(digest)
    
    blob_path = temp_storage.get_blob_path(digest)
    assert blob_path.exists()
    assert blob_path.read_bytes() == test_content


def test_blob_storage_nonexistent_file(temp_storage, tmp_path):
    """Test storing a nonexistent file raises error."""
    nonexistent = tmp_path / "nonexistent.txt"
    
    with pytest.raises(StorageError, match="File not found"):
        temp_storage.store_blob(nonexistent, show_progress=False)


def test_manifest_operations(temp_storage):
    """Test manifest save, load, and delete operations."""
    namespace = "test"
    model = "test-model"
    tag = "latest"

    manifest_data = {
        "model_name": "test-model",
        "backend": "test",
        "version": "1.0",
    }

    assert not temp_storage.manifest_exists(namespace, model, tag)

    temp_storage.save_manifest(namespace, model, tag, manifest_data)
    assert temp_storage.manifest_exists(namespace, model, tag)

    loaded = temp_storage.load_manifest(namespace, model, tag)
    assert loaded == manifest_data

    models = temp_storage.list_models()
    assert (namespace, model, tag) in models

    assert temp_storage.delete_model(namespace, model, tag)
    assert not temp_storage.manifest_exists(namespace, model, tag)

    assert not temp_storage.delete_model(namespace, model, tag)


def test_delete_model_removes_checkpoint_and_orphaned_blobs(temp_storage, tmp_path):
    """Deleting a model frees its checkpoint and blobs nothing else uses."""
    namespace, model, tag = "resemble", "demo", "latest"
    digest_a = "a" * 64
    digest_b = "b" * 64

    (temp_storage.blobs_path / f"sha256-{digest_a}").write_bytes(b"weight-a")
    (temp_storage.blobs_path / f"sha256-{digest_b}").write_bytes(b"weight-b")

    ckpt = temp_storage.get_checkpoint_path(namespace, model, tag)
    ckpt.mkdir(parents=True)
    (ckpt / "ve.safetensors").write_bytes(b"weight-a")

    state = temp_storage.pull_state_path / f"{namespace}__{model}.json"
    state.write_text("{}", encoding="utf-8")

    temp_storage.save_manifest(
        namespace,
        model,
        tag,
        {
            "layers": [
                {"filename": "ve.safetensors", "digest": digest_a},
                {"filename": "t3.safetensors", "digest": digest_b},
            ]
        },
    )

    assert temp_storage.delete_model(namespace, model, tag)
    assert not temp_storage.manifest_exists(namespace, model, tag)
    assert not ckpt.exists()
    assert not state.exists()
    assert not temp_storage.blob_exists(digest_a)
    assert not temp_storage.blob_exists(digest_b)


def test_delete_model_keeps_shared_blobs(temp_storage):
    """A blob still referenced by another model is not pruned."""
    shared = "c" * 64
    (temp_storage.blobs_path / f"sha256-{shared}").write_bytes(b"shared")

    temp_storage.save_manifest(
        "ns",
        "model-a",
        "latest",
        {"layers": [{"filename": "a.bin", "digest": shared}]},
    )
    temp_storage.save_manifest(
        "ns",
        "model-b",
        "latest",
        {"layers": [{"filename": "b.bin", "digest": shared}]},
    )

    assert temp_storage.delete_model("ns", "model-a", "latest")
    assert temp_storage.blob_exists(shared)
    assert temp_storage.manifest_exists("ns", "model-b", "latest")


def test_purge_wipes_storage_and_recreates_layout(temp_storage):
    """purge removes everything under the storage root, then re-inits dirs."""
    blob = temp_storage.blobs_path / ("sha256-" + "d" * 64)
    blob.write_bytes(b"gone")
    temp_storage.save_manifest("ns", "m", "latest", {"layers": []})

    root = temp_storage.purge()

    assert root == temp_storage.base_path
    assert temp_storage.manifests_path.exists()
    assert temp_storage.blobs_path.exists()
    assert list(temp_storage.list_models()) == []
    assert not blob.exists()



def test_load_nonexistent_manifest(temp_storage):
    """Test loading nonexistent manifest returns None."""
    result = temp_storage.load_manifest("nonexistent", "model", "tag")
    assert result is None


def test_list_models(temp_storage):
    """Test listing multiple models."""
    models_to_create = [
        ("ns1", "model1", "v1"),
        ("ns1", "model1", "v2"),
        ("ns2", "model2", "latest"),
    ]
    
    for namespace, model, tag in models_to_create:
        temp_storage.save_manifest(namespace, model, tag, {"test": "data"})
    
    listed_models = temp_storage.list_models()
    assert len(listed_models) == 3
    
    for model_tuple in models_to_create:
        assert model_tuple in listed_models


def test_list_models_empty_storage(temp_storage):
    """Test listing models in empty storage."""
    models = temp_storage.list_models()
    assert models == []
