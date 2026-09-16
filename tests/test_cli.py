"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner

from wavhost import dependencies
from wavhost.cli import main
from wavhost.storage import WavhostStorage


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """Point Wavhost at a throwaway storage directory."""
    store = WavhostStorage(base_path=tmp_path)
    monkeypatch.setattr("wavhost.cli.WavhostStorage", lambda: store)
    return store


@pytest.fixture
def engine(monkeypatch):
    """Control whether the backend engine looks installed, recording installs."""
    state = {"installed": True, "installs": [], "gpu_warning": None}

    monkeypatch.setattr(
        "wavhost.cli.dependencies.is_installed",
        lambda backend: state["installed"],
    )
    monkeypatch.setattr(
        "wavhost.cli.dependencies.install",
        lambda backend: state["installs"].append(backend),
    )
    # Never probe the host's GPU/torch from tests; each test decides the answer.
    monkeypatch.setattr(
        "wavhost.cli.dependencies.gpu_build_warning",
        lambda: state["gpu_warning"],
    )
    return state


@pytest.fixture
def fake_pull(monkeypatch, storage):
    """Skip real HTTP downloads; write a minimal manifest instead."""

    def _pull(model_info, force=False, show_progress=True):
        layers = [
            {
                "filename": layer.filename,
                "url": layer.url,
                "digest": "0" * 64,
                "size": 0,
            }
            for layer in model_info.layers
        ]
        ckpt = storage.get_checkpoint_path(
            model_info.namespace, model_info.name, model_info.tag
        )
        ckpt.mkdir(parents=True, exist_ok=True)
        for layer in layers:
            (ckpt / layer["filename"]).write_bytes(b"")
        manifest = {
            "model_name": model_info.name,
            "namespace": model_info.namespace,
            "name": model_info.name,
            "tag": model_info.tag,
            "backend": model_info.backend,
            "checkpoint_path": str(ckpt),
            "layers": layers,
            "model_info": model_info.to_dict(),
        }
        storage.save_manifest(
            model_info.namespace,
            model_info.name,
            model_info.tag,
            manifest,
        )
        return manifest

    monkeypatch.setattr(
        "wavhost.storage.WavhostStorage.pull_layers",
        lambda self, model_info, force=False, show_progress=True: _pull(
            model_info, force=force, show_progress=show_progress
        ),
    )


def test_pull_installs_engine_for_new_model(storage, engine, fake_pull):
    """A first-time pull installs the engine the model needs."""
    engine["installed"] = False

    result = CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\ny\n")

    assert result.exit_code == 0, result.output
    assert engine["installs"] == ["chatterbox"]
    assert storage.manifest_exists("resemble", "chatterbox-turbo", "latest")


def test_pull_installs_engine_when_model_already_pulled(storage, engine, fake_pull):
    """An existing manifest must not mask a missing engine."""
    CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")
    engine["installed"] = False
    engine["installs"].clear()

    result = CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")

    assert result.exit_code == 0
    assert "already installed" in result.output
    assert engine["installs"] == ["chatterbox"]


def test_pull_skips_engine_install_when_already_present(storage, engine, fake_pull):
    """A present engine is left alone."""
    result = CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")

    assert result.exit_code == 0
    assert engine["installs"] == []


def test_pull_warns_when_torch_is_cpu_build(storage, engine, fake_pull):
    """A CPU-only torch next to an NVIDIA GPU is reported with its fix."""
    engine["gpu_warning"] = "CPU-only build\n  pip install torch==X+cu124"

    result = CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "Warning: CPU-only build" in result.output
    assert "pip install torch==X+cu124" in result.output
    # Purely advisory: the pull still completes.
    assert storage.manifest_exists("resemble", "chatterbox-turbo", "latest")


def test_pull_stays_quiet_when_gpu_build_is_fine(storage, engine, fake_pull):
    """No GPU problem, no noise."""
    result = CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")

    assert result.exit_code == 0
    assert "Warning:" not in result.output


def test_pull_skip_deps_never_installs(storage, engine, fake_pull):
    """--skip-deps leaves environment management to the user."""
    engine["installed"] = False

    result = CliRunner().invoke(
        main, ["pull", "chatterbox-turbo", "--skip-deps"], input="y\n"
    )

    assert result.exit_code == 0
    assert engine["installs"] == []
    assert storage.manifest_exists("resemble", "chatterbox-turbo", "latest")


def test_pull_declining_engine_install_aborts(storage, engine, fake_pull):
    """Declining the install stops the pull and explains the manual path."""
    engine["installed"] = False

    result = CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\nn\n")

    assert result.exit_code == 0
    assert engine["installs"] == []
    assert dependencies.install_hint("chatterbox") in result.output
    assert not storage.manifest_exists("resemble", "chatterbox-turbo", "latest")


def test_pull_declining_license_aborts(storage, engine, fake_pull):
    """Declining the license stops before touching the environment."""
    engine["installed"] = False

    result = CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="n\n")

    assert result.exit_code == 0
    assert engine["installs"] == []
    assert not storage.manifest_exists("resemble", "chatterbox-turbo", "latest")


def test_pull_unknown_model_lists_alternatives(storage, engine, fake_pull):
    """An unknown name exits non-zero and shows what is available."""
    result = CliRunner().invoke(main, ["pull", "no-such-model"])

    assert result.exit_code == 1
    assert "chatterbox-turbo" in result.output


def test_rm_removes_installed_model(storage, engine, fake_pull):
    """wavhost rm deletes a pulled model from local storage."""
    CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")
    assert storage.manifest_exists("resemble", "chatterbox-turbo", "latest")

    result = CliRunner().invoke(main, ["rm", "chatterbox-turbo", "--yes"])

    assert result.exit_code == 0, result.output
    assert "Removed" in result.output
    assert not storage.manifest_exists("resemble", "chatterbox-turbo", "latest")


def test_rm_missing_model_fails(storage, engine, fake_pull):
    """Removing a model that was never pulled exits with an error."""
    result = CliRunner().invoke(main, ["rm", "chatterbox-turbo", "--yes"])

    assert result.exit_code == 1
    assert "not installed" in result.output


def test_uninstall_purges_storage(storage, engine, fake_pull):
    """wavhost uninstall wipes local data and prints pip uninstall hints."""
    CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")

    result = CliRunner().invoke(main, ["uninstall", "--yes"])

    assert result.exit_code == 0, result.output
    assert "Removed local data" in result.output
    assert "pip uninstall wavhost" in result.output
    assert storage.list_models() == []


def test_uninstall_keep_data_skips_purge(storage, engine, fake_pull):
    """--keep-data leaves ~/.wavhost alone but still shows package removal."""
    CliRunner().invoke(main, ["pull", "chatterbox-turbo"], input="y\n")

    result = CliRunner().invoke(main, ["uninstall", "--keep-data", "--yes"])

    assert result.exit_code == 0, result.output
    assert "Kept local data" in result.output
    assert storage.manifest_exists("resemble", "chatterbox-turbo", "latest")
    assert "pip uninstall wavhost" in result.output


def test_show_kokoro_lists_named_voices(storage):
    result = CliRunner().invoke(main, ["show", "kokoro"])

    assert result.exit_code == 0, result.output
    assert "hexgrad/kokoro:latest" in result.output
    assert "af_heart*" in result.output
    assert "bm_george" in result.output
    assert "American English" in result.output
    assert "wavhost pull kokoro" in result.output


def test_show_unknown_model_lists_alternatives(storage):
    result = CliRunner().invoke(main, ["show", "no-such-model"])

    assert result.exit_code == 1
    assert "chatterbox-turbo" in result.output
    assert "kokoro" in result.output


def test_list_points_at_show(storage):
    result = CliRunner().invoke(main, ["list"])

    assert result.exit_code == 0, result.output
    assert "kokoro" in result.output
    assert "wavhost show <model>" in result.output


def test_uninstall_mentions_kokoro(storage, engine, fake_pull):
    result = CliRunner().invoke(main, ["uninstall", "--keep-data", "--yes"])

    assert result.exit_code == 0, result.output
    assert "pip uninstall kokoro" in result.output
