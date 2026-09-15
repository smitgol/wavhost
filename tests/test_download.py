"""Tests for the HTTP layer downloader and pull materialization."""

import hashlib
from pathlib import Path

import httpx
import pytest

from wavhost.download import compute_file_hash, download_file
from wavhost.exceptions import DownloadError, StorageError
from wavhost.registry import ModelInfo, ModelLayer
from wavhost.storage import WavhostStorage


class _FakeStreamResponse:
    def __init__(self, chunks, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks

    def iter_bytes(self, chunk_size=0):
        yield from self._chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def stream(self, method, url, headers=None):
        self.requests.append({"method": method, "url": url, "headers": headers or {}})
        if not self._responses:
            raise httpx.ConnectError("no more responses")
        return self._responses.pop(0)


def test_compute_file_hash(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"hello")
    assert compute_file_hash(path) == hashlib.sha256(b"hello").hexdigest()


def test_download_file_writes_and_hashes(monkeypatch, tmp_path):
    content = b"model-weights"
    digest = hashlib.sha256(content).hexdigest()
    dest = tmp_path / "ve.safetensors"

    client = _FakeClient(
        [
            _FakeStreamResponse(
                [content],
                headers={"Content-Length": str(len(content))},
            )
        ]
    )
    monkeypatch.setattr("wavhost.download.httpx.Client", lambda **kw: client)

    result = download_file(
        "https://example.com/ve.safetensors",
        dest,
        show_progress=False,
    )

    assert result == digest
    assert dest.read_bytes() == content
    assert not dest.with_suffix(dest.suffix + ".partial").exists()


def test_download_without_content_length_and_progress(monkeypatch, tmp_path):
    """Servers that omit Content-Length must not crash tqdm truthiness checks."""
    content = b'{"tokenizer": true}'
    dest = tmp_path / "tokenizer_config.json"

    client = _FakeClient(
        [
            _FakeStreamResponse(
                [content],
                headers={},  # no Content-Length → total=None
            )
        ]
    )
    monkeypatch.setattr("wavhost.download.httpx.Client", lambda **kw: client)

    result = download_file(
        "https://example.com/tokenizer_config.json",
        dest,
        show_progress=True,
    )

    assert result == hashlib.sha256(content).hexdigest()
    assert dest.read_bytes() == content


def test_download_file_resumes_partial(monkeypatch, tmp_path):
    full = b"abcdefghij"
    dest = tmp_path / "layer.bin"
    partial = dest.with_suffix(dest.suffix + ".partial")
    partial.write_bytes(full[:4])

    client = _FakeClient(
        [
            _FakeStreamResponse(
                [full[4:]],
                status_code=206,
                headers={
                    "Content-Length": "6",
                    "Content-Range": "bytes 4-9/10",
                },
            )
        ]
    )
    monkeypatch.setattr("wavhost.download.httpx.Client", lambda **kw: client)

    digest = download_file(
        "https://example.com/layer.bin",
        dest,
        show_progress=False,
    )

    assert dest.read_bytes() == full
    assert digest == hashlib.sha256(full).hexdigest()
    assert client.requests[0]["headers"]["Range"] == "bytes=4-"


def test_download_file_sha256_mismatch(monkeypatch, tmp_path):
    content = b"wrong"
    dest = tmp_path / "layer.bin"
    client = _FakeClient(
        [_FakeStreamResponse([content], headers={"Content-Length": "5"})]
    )
    monkeypatch.setattr("wavhost.download.httpx.Client", lambda **kw: client)

    with pytest.raises(DownloadError, match="SHA-256 mismatch"):
        download_file(
            "https://example.com/layer.bin",
            dest,
            expected_sha256="0" * 64,
            show_progress=False,
            max_retries=1,
        )

    assert not dest.exists()


def test_download_retries_then_succeeds(monkeypatch, tmp_path):
    content = b"ok"
    dest = tmp_path / "layer.bin"
    calls = {"n": 0}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def stream(self, method, url, headers=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ConnectError("boom")
            return _FakeStreamResponse(
                [content], headers={"Content-Length": "2"}
            )

    monkeypatch.setattr("wavhost.download.httpx.Client", lambda **kw: _Client())
    monkeypatch.setattr("wavhost.download.time.sleep", lambda s: None)

    digest = download_file(
        "https://example.com/layer.bin",
        dest,
        show_progress=False,
        max_retries=3,
    )
    assert digest == hashlib.sha256(content).hexdigest()
    assert calls["n"] == 2


def test_materialize_checkpoint_hardlinks_or_copies(tmp_path):
    storage = WavhostStorage(base_path=tmp_path)
    blob_content = b"weights"
    digest = hashlib.sha256(blob_content).hexdigest()
    blob = storage.get_blob_path(digest)
    blob.write_bytes(blob_content)

    layers = [{"filename": "ve.safetensors", "digest": digest, "size": len(blob_content)}]
    ckpt = storage.materialize_checkpoint("ns", "model", "latest", layers)

    assert (ckpt / "ve.safetensors").read_bytes() == blob_content
    assert storage.checkpoint_ready("ns", "model", "latest", layers)


def test_materialize_checkpoint_creates_nested_layer_dirs(tmp_path):
    """Qwen layers live under speech_tokenizer/; parents must exist before copy."""
    storage = WavhostStorage(base_path=tmp_path)
    blob_content = b'{"model_type": "qwen3"}'
    digest = hashlib.sha256(blob_content).hexdigest()
    storage.get_blob_path(digest).write_bytes(blob_content)

    layers = [
        {
            "filename": "speech_tokenizer/config.json",
            "digest": digest,
            "size": len(blob_content),
        }
    ]
    ckpt = storage.materialize_checkpoint("qwen", "qwen-0.6-customvoice", "latest", layers)

    nested = ckpt / "speech_tokenizer" / "config.json"
    assert nested.is_file()
    assert nested.read_bytes() == blob_content
    assert storage.checkpoint_ready("qwen", "qwen-0.6-customvoice", "latest", layers)


def test_materialize_missing_blob_raises(tmp_path):
    storage = WavhostStorage(base_path=tmp_path)
    with pytest.raises(StorageError, match="Missing blob"):
        storage.materialize_checkpoint(
            "ns",
            "model",
            "latest",
            [{"filename": "ve.safetensors", "digest": "a" * 64}],
        )


def test_pull_layers_downloads_and_writes_manifest(monkeypatch, tmp_path):
    storage = WavhostStorage(base_path=tmp_path)
    content = b"layer-bytes"
    digest = hashlib.sha256(content).hexdigest()

    def fake_download(url, dest, expected_sha256=None, show_progress=True, max_retries=5):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return digest

    monkeypatch.setattr("wavhost.download.download_file", fake_download)

    model = ModelInfo(
        namespace="test",
        name="tiny",
        tag="latest",
        backend="chatterbox",
        description="test",
        license="MIT",
        license_url="http://example.com",
        model_class="ChatterboxTurboTTS",
        layers=(
            ModelLayer(
                filename="ve.safetensors",
                url="https://example.com/ve.safetensors",
            ),
        ),
    )

    manifest = storage.pull_layers(model, show_progress=False)

    assert storage.manifest_exists("test", "tiny", "latest")
    assert manifest["layers"][0]["digest"] == digest
    assert storage.blob_exists(digest)
    ckpt = Path(manifest["checkpoint_path"])
    assert (ckpt / "ve.safetensors").read_bytes() == content


def test_pull_layers_resumes_after_partial_failure(monkeypatch, tmp_path):
    """A failed pull keeps blob digests so the next attempt skips them."""
    storage = WavhostStorage(base_path=tmp_path)
    contents = {
        "a.bin": b"aaa",
        "b.bin": b"bbb",
    }
    digests = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    calls: list[str] = []
    fail_b_once = {"done": False}

    def fake_download(url, dest, expected_sha256=None, show_progress=True, max_retries=5):
        name = Path(dest).name
        calls.append(name)
        if name == "b.bin" and not fail_b_once["done"]:
            fail_b_once["done"] = True
            raise DownloadError("simulated disconnect")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(contents[name])
        return digests[name]

    monkeypatch.setattr("wavhost.download.download_file", fake_download)

    model = ModelInfo(
        namespace="test",
        name="resume",
        tag="latest",
        backend="chatterbox",
        description="test",
        license="MIT",
        license_url="http://example.com",
        model_class="ChatterboxTurboTTS",
        layers=(
            ModelLayer(filename="a.bin", url="https://example.com/a.bin"),
            ModelLayer(filename="b.bin", url="https://example.com/b.bin"),
        ),
    )

    with pytest.raises(DownloadError):
        storage.pull_layers(model, show_progress=False)

    assert storage.blob_exists(digests["a.bin"])
    assert not storage.manifest_exists("test", "resume", "latest")

    calls.clear()
    manifest = storage.pull_layers(model, show_progress=False)

    assert "a.bin" not in calls  # skipped via pull-state
    assert calls == ["b.bin"]
    assert storage.manifest_exists("test", "resume", "latest")
    assert len(manifest["layers"]) == 2
