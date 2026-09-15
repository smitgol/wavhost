"""Backend engine dependencies, resolved at pull time rather than install time.

Each TTS engine ships its own heavyweight package tree. Declaring them as
dependencies of Wavhost itself would force every user to download every
supported engine, so they are declared here per backend and installed only
when a model that needs them is pulled.
"""

import importlib.metadata
import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

from wavhost.config import TORCH_CUDA_INDEX_URL, TORCH_CUDA_TAG
from wavhost.exceptions import BackendError
from wavhost.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class BackendRequirement:
    """Packages a backend needs in order to run.

    Attributes:
        extra: Name of the pyproject optional-dependency group
        import_name: Top-level module used to probe whether the engine is present
        packages: Pip requirement specifiers to install
        import_probes: Additional modules that must also be importable. Use
            this for undeclared transitive dependencies so a half-working
            engine is detected at pull time, not at first synthesis.
    """

    extra: str
    import_name: str
    packages: tuple[str, ...] = field(default_factory=tuple)
    import_probes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def all_probes(self) -> tuple[str, ...]:
        """Every module that must resolve for the engine to count as installed."""
        probes = (self.import_name,) + tuple(self.import_probes)
        # Preserve order, drop duplicates.
        return tuple(dict.fromkeys(probes))


BACKEND_REQUIREMENTS: dict[str, BackendRequirement] = {
    "chatterbox": BackendRequirement(
        extra="chatterbox",
        import_name="chatterbox",
        # resemble-perth (Chatterbox's watermarker) imports pkg_resources but
        # doesn't declare setuptools. setuptools 82.0.0 removed pkg_resources,
        # which makes perth silently export PerthImplicitWatermarker=None and
        # Chatterbox fail with "'NoneType' object is not callable".
        packages=("chatterbox-tts>=0.1.0", "setuptools<82"),
        # Probe the deepest link in the chain so a broken perth is caught at
        # pull time instead of at first synthesis.
        import_probes=("chatterbox", "pkg_resources"),
    ),
    "qwen": BackendRequirement(
        extra="qwen",
        import_name="qwen_tts",
        packages=("qwen-tts>=0.1.0",),
        import_probes=("qwen_tts", "transformers"),
    ),
}


def get_requirement(backend: str) -> Optional[BackendRequirement]:
    """Look up the requirement for a backend.

    Args:
        backend: Backend identifier (e.g. 'chatterbox')

    Returns:
        The requirement, or None if the backend needs no extra packages
    """
    return BACKEND_REQUIREMENTS.get(backend)


def is_installed(backend: str) -> bool:
    """Check whether a backend's engine packages are importable.

    Args:
        backend: Backend identifier

    Returns:
        True if the engine is available (or needs nothing installed)
    """
    requirement = get_requirement(backend)
    if requirement is None:
        return True

    for module_name in requirement.all_probes:
        try:
            if importlib.util.find_spec(module_name) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def install_hint(backend: str) -> str:
    """Build a copy-pasteable command that installs a backend's engine.

    Args:
        backend: Backend identifier

    Returns:
        A pip command string, or an empty string if nothing is needed
    """
    requirement = get_requirement(backend)
    if requirement is None:
        return ""
    return f"pip install {' '.join(requirement.packages)}"


def missing_engine_message(backend: str) -> str:
    """Explain that an engine is absent, naming the interpreter that needs it.

    Engines are installed per interpreter while pulled models are recorded in
    shared storage, so the usual cause of a missing engine is running Wavhost
    from a different Python than the one it was set up in.

    Args:
        backend: Backend identifier

    Returns:
        A multi-line, actionable error message
    """
    return (
        f"The '{backend}' engine is not installed for this Python interpreter:\n"
        f"  {sys.executable}\n"
        f"Install it with: wavhost pull <model>\n"
        f"Or directly with: {install_hint(backend)}"
    )


def install(backend: str) -> None:
    """Install a backend's engine packages into the running interpreter.

    Pip output is streamed to the terminal so the user can follow a download
    that may take several minutes.

    Args:
        backend: Backend identifier

    Raises:
        BackendError: If the backend is unknown or pip fails
    """
    requirement = get_requirement(backend)
    if requirement is None:
        raise BackendError(f"No known dependencies for backend '{backend}'")

    logger.info(f"Installing {backend} engine: {', '.join(requirement.packages)}")

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *requirement.packages],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise BackendError(
            f"Failed to install the {backend} engine (pip exited with {e.returncode}).\n"
            f"Install it manually with: {install_hint(backend)}"
        )
    except OSError as e:
        raise BackendError(f"Could not run pip to install the {backend} engine: {e}")

    if not is_installed(backend):
        raise BackendError(
            f"The {backend} engine still is not importable after installation.\n"
            f"Try installing it manually with: {install_hint(backend)}"
        )


# --- GPU build check -------------------------------------------------------
#
# Engines pin an exact torch version (e.g. torch==2.6.0). Resolving that pin
# against PyPI yields the CPU-only wheel on Windows, silently replacing any
# CUDA build the user had. The model then "works" but runs several times
# slower, and the only symptom is a fallback warning at synthesis time.

_TORCH_PACKAGES: tuple[str, ...] = ("torch", "torchaudio", "torchvision")


def nvidia_gpu_present() -> bool:
    """Detect an NVIDIA GPU via the driver's nvidia-smi tool.

    Deliberately does not use torch, whose answer depends on the build we are
    trying to diagnose.

    Returns:
        True if nvidia-smi is on PATH and lists at least one GPU
    """
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and "GPU" in result.stdout


def torch_is_cpu_build() -> Optional[bool]:
    """Report whether the installed torch was built without CUDA.

    Returns:
        True for a CPU-only build, False for a CUDA build, None if torch is
        not importable
    """
    try:
        import torch
    except ImportError:
        return None
    return torch.version.cuda is None


def torch_cuda_install_hint() -> str:
    """Build the pip command that swaps installed torch packages for CUDA builds.

    Uses the versions already installed so the engine's exact pin is kept.
    The `+cuXXX` local tag is spelled out because pip treats `2.6.0+cpu` as
    satisfying a plain `torch==2.6.0` and would otherwise do nothing.

    Returns:
        A pip command string
    """
    specs = []
    for package in _TORCH_PACKAGES:
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            continue
        base = version.split("+", 1)[0]
        specs.append(f'"{package}=={base}+{TORCH_CUDA_TAG}"')

    if not specs:
        specs.append('torch torchaudio')

    return f"pip install {' '.join(specs)} --index-url {TORCH_CUDA_INDEX_URL}"


def gpu_build_warning() -> Optional[str]:
    """Explain when an NVIDIA GPU is present but torch cannot use it.

    Only the CPU-build case is reported, because it has a one-command fix. A
    CUDA build that still cannot see the GPU is a driver problem outside
    Wavhost's control and is left to torch's own diagnostics.

    Returns:
        A multi-line warning with the fix command, or None if nothing is wrong
    """
    if torch_is_cpu_build() is not True:
        return None
    if not nvidia_gpu_present():
        return None
    return (
        "An NVIDIA GPU was detected, but the installed torch is a CPU-only build,\n"
        "so models will run on the CPU (several times slower).\n"
        f"Interpreter: {sys.executable}\n"
        "Switch to the CUDA build with:\n"
        f"  {torch_cuda_install_hint()}"
    )
