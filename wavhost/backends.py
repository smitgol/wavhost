"""TTS backend protocol and implementations."""

from abc import abstractmethod
from pathlib import Path
from typing import Optional, Protocol, Union

import torch

from wavhost import dependencies
from wavhost.config import CPU_DEVICE, DEFAULT_DEVICE, DEFAULT_SAMPLE_RATE
from wavhost.exceptions import BackendError
from wavhost.logging_config import get_logger
from wavhost.registry import ModelInfo

logger = get_logger(__name__)

BACKEND_NAME = "chatterbox"


class TTSBackend(Protocol):
    """Protocol for TTS backend implementations.
    
    All TTS backends must implement this interface for consistency.
    """
    
    @abstractmethod
    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> tuple[torch.Tensor, int]:
        """Generate speech from text.
        
        Args:
            text: Text to synthesize
            voice: Optional voice identifier or reference audio path
            **kwargs: Backend-specific parameters
            
        Returns:
            Tuple of (audio_tensor, sample_rate)
            
        Raises:
            BackendError: If generation fails
        """
        ...
    
    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Get the sample rate of generated audio.
        
        Returns:
            Sample rate in Hz
        """
        ...


class ChatterboxBackend:
    """Chatterbox TTS backend implementation.
    
    Loads weights from a local checkpoint directory produced by `wavhost pull`
    (never calls the Hugging Face Hub client at runtime).
    """
    
    def __init__(
        self,
        model_class: str,
        checkpoint_path: Union[str, Path],
        model_kwargs: Optional[dict] = None,
        device: Optional[str] = None
    ):
        """Initialize Chatterbox backend.
        
        Args:
            model_class: Name of the model class ('ChatterboxTTS' or 'ChatterboxTurboTTS')
            checkpoint_path: Local directory with model files (from pull)
            model_kwargs: Unused; kept for API compatibility
            device: Device to run on ('cuda', 'cpu', or 'mps'). Auto-detects if None.
            
        Raises:
            BackendError: If model class is invalid or checkpoint is missing
        """
        self._validate_model_class(model_class)
        
        self._model_class = model_class
        self._model_kwargs = model_kwargs or {}
        self._checkpoint_path = Path(checkpoint_path)
        self._device = device or self._detect_device()
        self._model = None
        self._sr = DEFAULT_SAMPLE_RATE
        
        if not self._checkpoint_path.is_dir():
            raise BackendError(
                f"Checkpoint directory not found: {self._checkpoint_path}. "
                f"Pull the model first with: wavhost pull <model>"
            )
        
        logger.info(
            f"Initialized {model_class} backend on {self._device} "
            f"from {self._checkpoint_path}"
        )
    
    @staticmethod
    def _validate_model_class(model_class: str) -> None:
        """Validate that the model class is supported.
        
        Args:
            model_class: Model class name
            
        Raises:
            BackendError: If model class is invalid
        """
        valid_classes = {"ChatterboxTTS", "ChatterboxTurboTTS"}
        if model_class not in valid_classes:
            raise BackendError(
                f"Invalid model class '{model_class}'. "
                f"Must be one of: {', '.join(valid_classes)}"
            )
    
    @staticmethod
    def _detect_device() -> str:
        """Detect the best available device.
        
        Returns:
            Device string ('cuda', 'mps', or 'cpu')
        """
        if torch.cuda.is_available():
            return DEFAULT_DEVICE
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        return CPU_DEVICE
    
    def _load_model(self) -> None:
        """Lazy load the model on first use from the local checkpoint.
        
        Raises:
            BackendError: If model loading fails
        """
        if self._model is not None:
            return
        
        if not dependencies.is_installed(BACKEND_NAME):
            raise BackendError(dependencies.missing_engine_message(BACKEND_NAME))
        
        logger.info(
            f"Loading {self._model_class} from {self._checkpoint_path}..."
        )
        
        try:
            if self._model_class == "ChatterboxTurboTTS":
                from chatterbox.tts_turbo import ChatterboxTurboTTS
                self._model = ChatterboxTurboTTS.from_local(
                    self._checkpoint_path,
                    self._device,
                )
            else:
                from chatterbox.tts import ChatterboxTTS
                self._model = ChatterboxTTS.from_local(
                    self._checkpoint_path,
                    self._device,
                )
            
            self._sr = self._model.sr
            logger.info(f"Model loaded successfully (sample rate: {self._sr} Hz)")
            
        except ImportError as e:
            raise BackendError(
                f"Failed to import Chatterbox. "
                f"Install with: {dependencies.install_hint(BACKEND_NAME)}\n"
                f"Error: {e}"
            ) from e
        except Exception as e:
            # Keep the original type and chain the cause so the real frame
            # (e.g. a broken transitive dependency) is recoverable from logs.
            logger.debug("Chatterbox model load failed", exc_info=True)
            raise BackendError(
                f"Failed to load Chatterbox model: {type(e).__name__}: {e}"
            ) from e
    
    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> tuple[torch.Tensor, int]:
        """Generate speech from text using Chatterbox.
        
        Args:
            text: Text to synthesize
            voice: Optional path to reference voice audio (for voice cloning)
            **kwargs: Additional parameters passed to model.generate()
            
        Returns:
            Tuple of (audio_tensor, sample_rate)
            
        Raises:
            BackendError: If generation fails
        """
        self._load_model()
        
        generate_kwargs = kwargs.copy()
        
        if voice:
            voice_path = Path(voice)
            if not voice_path.exists():
                raise BackendError(f"Reference voice audio not found: {voice}")
            
            logger.debug(f"Cloning voice from {voice_path}")
            generate_kwargs['audio_prompt_path'] = str(voice_path)
        
        try:
            logger.debug(f"Generating speech for text (length: {len(text)})")
            wav = self._model.generate(text, **generate_kwargs)
            return wav, self._sr
            
        except Exception as e:
            raise BackendError(f"Speech generation failed: {e}")
    
    @property
    def sample_rate(self) -> int:
        """Get the sample rate of generated audio.
        
        Returns:
            Sample rate in Hz
        """
        return self._sr


def create_backend(
    model_info: ModelInfo,
    device: Optional[str] = None,
    checkpoint_path: Optional[Union[str, Path]] = None,
) -> TTSBackend:
    """Factory function to create a TTS backend from model info.
    
    Args:
        model_info: Model information from registry
        device: Optional device override ('cuda', 'cpu', or 'mps')
        checkpoint_path: Local checkpoint directory from `wavhost pull`
        
    Returns:
        Initialized backend instance
        
    Raises:
        BackendError: If backend type is not supported or checkpoint is missing
    """
    backend_type = model_info.backend
    
    if backend_type == BACKEND_NAME:
        if checkpoint_path is None:
            raise BackendError(
                "checkpoint_path is required. "
                "Pull the model first with: wavhost pull <model>"
            )
        
        actual_device = device or model_info.recommended_device
        
        if actual_device == DEFAULT_DEVICE and not torch.cuda.is_available():
            message = "GPU not available, falling back to CPU"
            gpu_hint = dependencies.gpu_build_warning()
            if gpu_hint:
                message = f"{message}\n{gpu_hint}"
            logger.warning(message)
            actual_device = CPU_DEVICE
        
        return ChatterboxBackend(
            model_class=model_info.model_class,
            checkpoint_path=checkpoint_path,
            model_kwargs=model_info.model_kwargs,
            device=actual_device
        )
    
    raise BackendError(f"Unsupported backend type: {backend_type}")
