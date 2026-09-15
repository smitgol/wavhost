"""Custom exceptions for Wavhost."""


class WavhostError(Exception):
    """Base exception for all Wavhost errors."""

    pass


class ModelNotFoundError(WavhostError):
    """Raised when a requested model is not found in the registry."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        super().__init__(f"Model '{model_name}' not found in registry")


class ModelNotInstalledError(WavhostError):
    """Raised when attempting to use a model that hasn't been pulled."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        super().__init__(
            f"Model '{model_name}' is not installed. "
            f"Pull it first with: wavhost pull {model_name}"
        )


class BackendError(WavhostError):
    """Raised when there's an error with a TTS backend."""

    pass


class StorageError(WavhostError):
    """Raised when there's an error with storage operations."""

    pass


class DownloadError(WavhostError):
    """Raised when a model layer download fails."""

    pass
