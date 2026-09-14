"""Wavhost - Local-first TTS runtime."""

from wavhost.backends import TTSBackend, ChatterboxBackend, create_backend
from wavhost.config import VERSION
from wavhost.exceptions import (
    WavhostError,
    ModelNotFoundError,
    ModelNotInstalledError,
    BackendError,
    StorageError,
    ValidationError,
)
from wavhost.registry import ModelRegistry, ModelInfo
from wavhost.storage import WavhostStorage

__version__ = VERSION
__all__ = [
    "__version__",
    "TTSBackend",
    "ChatterboxBackend",
    "create_backend",
    "ModelRegistry",
    "ModelInfo",
    "WavhostStorage",
    "WavhostError",
    "ModelNotFoundError",
    "ModelNotInstalledError",
    "BackendError",
    "StorageError",
    "ValidationError",
]
