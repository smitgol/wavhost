"""Tests for backend engine dependency resolution."""

import subprocess
import sys

import pytest

from wavhost import dependencies
from wavhost.exceptions import BackendError
from wavhost.registry import ModelRegistry


def test_every_registry_backend_has_a_requirement():
    """Every backend referenced by a built-in model must declare its packages."""
    registry = ModelRegistry()

    for name in registry.list_models():
        backend = registry.get_model_info(name).backend
        assert dependencies.get_requirement(backend) is not None, (
            f"Model '{name}' uses backend '{backend}' with no declared requirement"
        )


def test_unknown_backend_has_no_requirement():
    """Backends without declared packages resolve to None."""
    assert dependencies.get_requirement("does-not-exist") is None


def test_unknown_backend_counts_as_installed():
    """A backend needing nothing is never blocked."""
    assert dependencies.is_installed("does-not-exist") is True


def test_is_installed_detects_present_module(monkeypatch):
    """A backend whose import name resolves is reported as installed."""
    monkeypatch.setitem(
        dependencies.BACKEND_REQUIREMENTS,
        "fake",
        dependencies.BackendRequirement(
            extra="fake",
            import_name="json",
            packages=("fake-tts>=1.0",),
        ),
    )

    assert dependencies.is_installed("fake") is True


def test_is_installed_detects_missing_module(monkeypatch):
    """A backend whose import name is absent is reported as missing."""
    monkeypatch.setitem(
        dependencies.BACKEND_REQUIREMENTS,
        "fake",
        dependencies.BackendRequirement(
            extra="fake",
            import_name="wavhost_no_such_engine",
            packages=("fake-tts>=1.0",),
        ),
    )

    assert dependencies.is_installed("fake") is False


def test_is_installed_requires_every_probe(monkeypatch):
    """A present top-level module is not enough if a declared probe is missing.

    This is the resemble-perth case: `chatterbox` imports fine, but perth
    swallows a failed `pkg_resources` import and exports None, so the engine
    only breaks at first synthesis. Probing the transitive module up front
    turns that into a pull-time install instead.
    """
    monkeypatch.setitem(
        dependencies.BACKEND_REQUIREMENTS,
        "fake",
        dependencies.BackendRequirement(
            extra="fake",
            import_name="json",
            packages=("fake-tts>=1.0",),
            import_probes=("wavhost_no_such_transitive_dep",),
        ),
    )

    assert dependencies.is_installed("fake") is False


def test_is_installed_passes_when_all_probes_resolve(monkeypatch):
    """All probes importable means the engine counts as installed."""
    monkeypatch.setitem(
        dependencies.BACKEND_REQUIREMENTS,
        "fake",
        dependencies.BackendRequirement(
            extra="fake",
            import_name="json",
            packages=("fake-tts>=1.0",),
            import_probes=("os", "sys"),
        ),
    )

    assert dependencies.is_installed("fake") is True


def test_all_probes_dedupes_and_keeps_import_name_first():
    """import_name is always probed, exactly once, before extra probes."""
    requirement = dependencies.BackendRequirement(
        extra="x",
        import_name="chatterbox",
        import_probes=("pkg_resources", "chatterbox"),
    )

    assert requirement.all_probes == ("chatterbox", "pkg_resources")


def test_chatterbox_requirement_pins_setuptools_below_82():
    """Guard against re-breaking the perth/pkg_resources chain.

    setuptools 82.0.0 removed pkg_resources; resemble-perth still imports it
    without declaring the dependency. The pin and the probe must both stay.
    """
    requirement = dependencies.BACKEND_REQUIREMENTS["chatterbox"]

    assert any(
        spec.startswith("setuptools") and "<82" in spec
        for spec in requirement.packages
    ), requirement.packages
    assert "pkg_resources" in requirement.import_probes


def _fake_versions(monkeypatch, versions):
    """Make importlib.metadata.version answer from a dict."""
    import importlib.metadata

    def _version(name):
        try:
            return versions[name]
        except KeyError:
            raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(dependencies.importlib.metadata, "version", _version)


def test_torch_cuda_install_hint_keeps_pins_and_spells_out_cuda_tag(monkeypatch):
    """The hint keeps the engine's exact versions and adds the +cuXXX tag.

    Spelling out the local tag matters: pip treats 2.6.0+cpu as satisfying
    torch==2.6.0 and would otherwise report 'already satisfied'.
    """
    _fake_versions(monkeypatch, {"torch": "2.6.0+cpu", "torchaudio": "2.6.0"})

    hint = dependencies.torch_cuda_install_hint()

    assert hint.startswith("pip install ")
    assert f'"torch==2.6.0+{dependencies.TORCH_CUDA_TAG}"' in hint
    assert f'"torchaudio==2.6.0+{dependencies.TORCH_CUDA_TAG}"' in hint
    assert "torchvision" not in hint
    assert f"--index-url {dependencies.TORCH_CUDA_INDEX_URL}" in hint


def test_torch_cuda_install_hint_without_torch_installed(monkeypatch):
    """With nothing installed the hint still points at the CUDA index."""
    _fake_versions(monkeypatch, {})

    hint = dependencies.torch_cuda_install_hint()

    assert "torch" in hint
    assert dependencies.TORCH_CUDA_INDEX_URL in hint


def test_gpu_build_warning_when_cpu_torch_meets_nvidia_gpu(monkeypatch):
    """CPU-only torch plus an NVIDIA GPU is the one case worth warning about."""
    monkeypatch.setattr(dependencies, "torch_is_cpu_build", lambda: True)
    monkeypatch.setattr(dependencies, "nvidia_gpu_present", lambda: True)
    _fake_versions(monkeypatch, {"torch": "2.6.0+cpu"})

    warning = dependencies.gpu_build_warning()

    assert warning is not None
    assert "CPU-only build" in warning
    assert f'"torch==2.6.0+{dependencies.TORCH_CUDA_TAG}"' in warning
    assert dependencies.sys.executable in warning


@pytest.mark.parametrize(
    ("cpu_build", "gpu_present"),
    [
        (False, True),   # CUDA build: nothing to fix here
        (True, False),   # CPU build but no NVIDIA GPU: CPU is correct
        (None, True),    # torch not installed at all
    ],
)
def test_gpu_build_warning_is_silent_otherwise(monkeypatch, cpu_build, gpu_present):
    """Only the fixable combination produces a warning."""
    monkeypatch.setattr(dependencies, "torch_is_cpu_build", lambda: cpu_build)
    monkeypatch.setattr(dependencies, "nvidia_gpu_present", lambda: gpu_present)

    assert dependencies.gpu_build_warning() is None


def test_nvidia_gpu_present_false_without_nvidia_smi(monkeypatch):
    """No driver tool on PATH means no NVIDIA GPU as far as we can tell."""
    monkeypatch.setattr(dependencies.shutil, "which", lambda name: None)

    assert dependencies.nvidia_gpu_present() is False


def test_nvidia_gpu_present_parses_nvidia_smi_output(monkeypatch):
    """nvidia-smi -L listing a GPU counts as present; failures do not."""
    import subprocess

    monkeypatch.setattr(dependencies.shutil, "which", lambda name: "nvidia-smi")

    def _ok(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="GPU 0: RTX 4050\n", stderr="")

    def _fail(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(dependencies.subprocess, "run", _ok)
    assert dependencies.nvidia_gpu_present() is True

    monkeypatch.setattr(dependencies.subprocess, "run", _fail)
    assert dependencies.nvidia_gpu_present() is False


def test_install_hint_lists_packages():
    """The hint is a runnable pip command covering every package."""
    hint = dependencies.install_hint("chatterbox")

    assert hint.startswith("pip install ")
    for package in dependencies.BACKEND_REQUIREMENTS["chatterbox"].packages:
        assert package in hint


def test_install_hint_is_empty_for_unknown_backend():
    """Nothing to install means nothing to suggest."""
    assert dependencies.install_hint("does-not-exist") == ""


def test_missing_engine_message_names_interpreter_and_fix():
    """The message must identify the interpreter, since that's the usual cause."""
    message = dependencies.missing_engine_message("chatterbox")

    assert sys.executable in message
    assert "wavhost pull" in message
    assert dependencies.install_hint("chatterbox") in message


def test_install_rejects_unknown_backend():
    """Installing a backend with no declared packages is an error."""
    with pytest.raises(BackendError, match="No known dependencies"):
        dependencies.install("does-not-exist")


def test_install_invokes_pip_with_declared_packages(monkeypatch):
    """Installation shells out to pip in the current interpreter."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setitem(
        dependencies.BACKEND_REQUIREMENTS,
        "fake",
        dependencies.BackendRequirement(
            extra="fake",
            import_name="json",
            packages=("fake-tts>=1.0",),
        ),
    )
    monkeypatch.setattr(dependencies.subprocess, "run", fake_run)

    dependencies.install("fake")

    assert calls == [[sys.executable, "-m", "pip", "install", "fake-tts>=1.0"]]


def test_install_raises_on_pip_failure(monkeypatch):
    """A non-zero pip exit is surfaced with a manual-install hint."""
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setitem(
        dependencies.BACKEND_REQUIREMENTS,
        "fake",
        dependencies.BackendRequirement(
            extra="fake",
            import_name="json",
            packages=("fake-tts>=1.0",),
        ),
    )
    monkeypatch.setattr(dependencies.subprocess, "run", fake_run)

    with pytest.raises(BackendError, match="pip install fake-tts>=1.0"):
        dependencies.install("fake")


def test_install_raises_when_engine_still_missing(monkeypatch):
    """A pip run that reports success but installs nothing is still a failure."""
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setitem(
        dependencies.BACKEND_REQUIREMENTS,
        "fake",
        dependencies.BackendRequirement(
            extra="fake",
            import_name="wavhost_no_such_engine",
            packages=("fake-tts>=1.0",),
        ),
    )
    monkeypatch.setattr(dependencies.subprocess, "run", fake_run)

    with pytest.raises(BackendError, match="not importable"):
        dependencies.install("fake")
