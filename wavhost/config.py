"""Configuration and constants for Wavhost."""

from pathlib import Path
from typing import Final

VERSION: Final[str] = "0.1.1"

DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 11435
DEFAULT_DEVICE: Final[str] = "cuda"
CPU_DEVICE: Final[str] = "cpu"
MPS_DEVICE: Final[str] = "mps"

DEFAULT_OUTPUT_FILENAME: Final[str] = "output.wav"
DEFAULT_SAMPLE_RATE: Final[int] = 24000

MAX_INPUT_LENGTH: Final[int] = 4096
MIN_SPEED: Final[float] = 0.25
MAX_SPEED: Final[float] = 4.0
DEFAULT_SPEED: Final[float] = 1.0

HASH_ALGORITHM: Final[str] = "sha256"
BLOB_PREFIX: Final[str] = f"{HASH_ALGORITHM}-"
BUFFER_SIZE: Final[int] = 64 * 1024

MODELS_DIR_NAME: Final[str] = "models"
MANIFESTS_DIR_NAME: Final[str] = "manifests"
REGISTRY_DIR_NAME: Final[str] = "registry"
BLOBS_DIR_NAME: Final[str] = "blobs"
CHECKPOINTS_DIR_NAME: Final[str] = "checkpoints"
PULL_STATE_DIR_NAME: Final[str] = "pull-state"
DOWNLOAD_MAX_RETRIES: Final[int] = 12
DOWNLOAD_CHUNK_SIZE: Final[int] = 1024 * 1024
DOWNLOAD_TIMEOUT: Final[float] = 120.0
DOWNLOAD_USER_AGENT: Final[str] = (
    f"wavhost/{VERSION} (+https://github.com/smitgol/wavhost; httpx)"
)

# PyPI's default torch wheel is CPU-only on Windows; CUDA builds come from
# PyTorch's own index. cu124 needs NVIDIA driver >= 550 and covers every
# torch version engines currently pin.
TORCH_CUDA_TAG: Final[str] = "cu124"
TORCH_CUDA_INDEX_URL: Final[str] = f"https://download.pytorch.org/whl/{TORCH_CUDA_TAG}"


def get_default_storage_path() -> Path:
    """Get the default storage path for Wavhost."""
    return Path.home() / ".wavhost"


def get_models_path(base_path: Path) -> Path:
    """Get the models directory path."""
    return base_path / MODELS_DIR_NAME


def get_manifests_path(base_path: Path) -> Path:
    """Get the manifests registry directory path."""
    return get_models_path(base_path) / MANIFESTS_DIR_NAME / REGISTRY_DIR_NAME


def get_blobs_path(base_path: Path) -> Path:
    """Get the blobs directory path."""
    return get_models_path(base_path) / BLOBS_DIR_NAME


def get_checkpoints_path(base_path: Path) -> Path:
    """Get the materialized checkpoint directory root."""
    return get_models_path(base_path) / CHECKPOINTS_DIR_NAME


def get_pull_state_path(base_path: Path) -> Path:
    """Get the durable pull-resume state directory."""
    return get_models_path(base_path) / PULL_STATE_DIR_NAME
