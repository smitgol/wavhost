"""Wavhost - Local-first TTS runtime."""

from wavhost.backends import ChatterboxBackend, KokoroBackend, QwenBackend, TTSBackend, create_backend
from wavhost.config import VERSION
from wavhost.exceptions import (
    BackendError,
    ModelNotFoundError,
    ModelNotInstalledError,
    StorageError,
    WavhostError,
)
from wavhost.registry import ModelInfo, ModelRegistry
from wavhost.storage import WavhostStorage

__version__ = VERSION
__all__ = [
    "__version__",
    "TTSBackend",
    "ChatterboxBackend",
    "QwenBackend",
    "KokoroBackend",
    "create_backend",
    "ModelRegistry",
    "ModelInfo",
    "WavhostStorage",
    "WavhostError",
    "ModelNotFoundError",
    "ModelNotInstalledError",
    "BackendError",
    "StorageError",
]
