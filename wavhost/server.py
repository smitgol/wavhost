"""FastAPI server with OpenAI-compatible /v1/audio/speech endpoint."""

import tempfile
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

import torch
import torchaudio
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

from wavhost.backends import create_backend
from wavhost.config import MAX_INPUT_LENGTH, MAX_SPEED, MIN_SPEED, VERSION
from wavhost.exceptions import (
    BackendError,
    ModelNotFoundError,
    ModelNotInstalledError,
    StorageError,
)
from wavhost.logging_config import get_logger
from wavhost.registry import ModelRegistry
from wavhost.storage import WavhostStorage
from wavhost.voices import (
    VoiceAlreadyExistsError,
    VoiceError,
    VoiceNotFoundError,
    VoiceStorage,
    resolve_voice,
)

logger = get_logger(__name__)

app = FastAPI(
    title="Wavhost",
    description="Local-first TTS runtime with OpenAI-compatible API",
    version=VERSION
)


class AudioFormat(str, Enum):
    """Supported audio output formats.

    ``pcm`` is raw signed 16-bit little-endian (S16LE) at the model's native
    sample rate (OpenAI-compatible). The ``pcm_*`` variants resample to a
    fixed rate first (ElevenLabs-compatible naming).
    """

    MP3 = "mp3"
    OPUS = "opus"
    AAC = "aac"
    FLAC = "flac"
    WAV = "wav"
    PCM = "pcm"
    PCM_16000 = "pcm_16000"
    PCM_22050 = "pcm_22050"
    PCM_24000 = "pcm_24000"
    PCM_44100 = "pcm_44100"


# Target sample rates for rate-specific PCM formats (Hz).
PCM_SAMPLE_RATES: dict[AudioFormat, int] = {
    AudioFormat.PCM_16000: 16000,
    AudioFormat.PCM_22050: 22050,
    AudioFormat.PCM_24000: 24000,
    AudioFormat.PCM_44100: 44100,
}


class SpeechRequest(BaseModel):
    """Request model for /v1/audio/speech endpoint (OpenAI-compatible)."""
    
    model: str = Field(
        ...,
        description="Model to use for generation (e.g., 'chatterbox-turbo')",
        min_length=1
    )
    input: str = Field(
        ...,
        description="Text to synthesize",
        min_length=1,
        max_length=MAX_INPUT_LENGTH
    )
    voice: str = Field(
        default="default",
        description=(
            "Voice to use: 'default' (model built-in / Qwen Ryan), a CustomVoice "
            "speaker name (Ryan, Aiden, ...), a saved voice, or a reference audio "
            "path (Qwen Base / Chatterbox)"
        ),
    )
    language: Optional[str] = Field(
        default=None,
        description=(
            "Language for synthesis. Chatterbox Multilingual: ISO code "
            "(en, fr, zh, …). Qwen: English, Chinese, Japanese, …"
        ),
    )
    response_format: AudioFormat = Field(
        default=AudioFormat.MP3,
        description=(
            "Audio format for the output. PCM options: pcm (native rate S16LE), "
            "pcm_16000, pcm_22050, pcm_24000, pcm_44100"
        ),
    )
    speed: float = Field(
        default=1.0,
        ge=MIN_SPEED,
        le=MAX_SPEED,
        description="Speed of the audio (currently not implemented)"
    )


class ModelData(BaseModel):
    """Model data for /v1/models endpoint."""
    
    id: str
    object: Literal["model"] = "model"
    created: int = 0
    owned_by: str
    installed: bool
    description: str


class ModelsResponse(BaseModel):
    """Response model for /v1/models endpoint."""
    
    object: Literal["list"] = "list"
    data: list[ModelData]


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: Literal["ok"] = "ok"


class AudioConverter:
    """Handles audio format conversion."""

    MEDIA_TYPES = {
        AudioFormat.MP3: "audio/mpeg",
        AudioFormat.OPUS: "audio/opus",
        AudioFormat.AAC: "audio/aac",
        AudioFormat.FLAC: "audio/flac",
        AudioFormat.WAV: "audio/wav",
        AudioFormat.PCM: "audio/pcm",
        AudioFormat.PCM_16000: "audio/pcm",
        AudioFormat.PCM_22050: "audio/pcm",
        AudioFormat.PCM_24000: "audio/pcm",
        AudioFormat.PCM_44100: "audio/pcm",
    }

    @classmethod
    def is_pcm(cls, target_format: AudioFormat) -> bool:
        """True for raw PCM formats (native or rate-specific)."""
        return (
            target_format == AudioFormat.PCM
            or target_format in PCM_SAMPLE_RATES
        )

    @staticmethod
    def to_pcm16_bytes(audio_tensor: torch.Tensor) -> bytes:
        """Encode float waveform as signed 16-bit little-endian PCM.

        Args:
            audio_tensor: Float audio in roughly [-1, 1], shape (channels, samples)

        Returns:
            Raw S16LE bytes (interleaved by channel if multi-channel)
        """
        audio = audio_tensor.detach().float().cpu().clamp(-1.0, 1.0)
        pcm = (audio * 32767.0).to(torch.int16).contiguous()
        # Avoid Tensor.numpy(): torch can be installed without NumPy.
        offset = pcm.storage_offset() * pcm.element_size()
        nbytes = pcm.numel() * pcm.element_size()
        return bytes(pcm.untyped_storage())[offset : offset + nbytes]

    @classmethod
    def resample(
        cls,
        audio_tensor: torch.Tensor,
        sample_rate: int,
        target_rate: int,
    ) -> torch.Tensor:
        """Resample audio to ``target_rate``, or return as-is when rates match."""
        if sample_rate == target_rate:
            return audio_tensor
        return torchaudio.functional.resample(
            audio_tensor.float(),
            orig_freq=sample_rate,
            new_freq=target_rate,
        )

    @classmethod
    def convert(
        cls,
        audio_tensor: torch.Tensor,
        sample_rate: int,
        target_format: AudioFormat,
    ) -> bytes:
        """Convert audio tensor to target format.

        Args:
            audio_tensor: Audio tensor (channels, samples)
            sample_rate: Sample rate in Hz
            target_format: Target audio format

        Returns:
            Audio bytes in target format

        Raises:
            RuntimeError: If conversion fails
        """
        if cls.is_pcm(target_format):
            target_rate = PCM_SAMPLE_RATES.get(target_format, sample_rate)
            resampled = cls.resample(audio_tensor, sample_rate, target_rate)
            return cls.to_pcm16_bytes(resampled)

        with tempfile.NamedTemporaryFile(
            suffix=f".{target_format.value}",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            save_kwargs = {"format": target_format.value}

            if target_format == AudioFormat.OPUS:
                save_kwargs["bits_per_sample"] = 16
            elif target_format == AudioFormat.WAV:
                # Avoid float32 WAV — many players decode it incorrectly.
                save_kwargs["encoding"] = "PCM_S"
                save_kwargs["bits_per_sample"] = 16
                audio_tensor = (
                    audio_tensor.detach().float().cpu().clamp(-1.0, 1.0)
                )

            torchaudio.save(
                str(tmp_path),
                audio_tensor,
                sample_rate,
                **save_kwargs,
            )

            with open(tmp_path, "rb") as f:
                return f.read()

        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise RuntimeError(
                f"Failed to convert audio to {target_format.value}: {e}"
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @classmethod
    def get_media_type(cls, format: AudioFormat) -> str:
        """Get MIME type for audio format.

        Args:
            format: Audio format

        Returns:
            MIME type string
        """
        return cls.MEDIA_TYPES.get(format, "audio/mpeg")

    @classmethod
    def get_filename(cls, format: AudioFormat) -> str:
        """Build a download filename for the given format."""
        if cls.is_pcm(format):
            return "speech.pcm"
        return f"speech.{format.value}"


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Wavhost",
        "version": VERSION,
        "description": "Local-first TTS runtime",
        "endpoints": {
            "speech": "/v1/audio/speech",
            "models": "/v1/models",
            "health": "/health"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/v1/models", response_model=ModelsResponse, tags=["Models"])
async def list_models():
    """List available models (OpenAI-compatible).
    
    Returns information about all models in the registry,
    including whether they are currently installed.
    """
    try:
        registry = ModelRegistry()
        storage = WavhostStorage()
        
        installed_models = set(storage.list_models())
        
        models_data = []
        for model_name in registry.list_models():
            model_info = registry.get_model_info(model_name)
            
            is_installed = (
                model_info.namespace,
                model_info.name,
                model_info.tag
            ) in installed_models
            
            models_data.append(ModelData(
                id=model_name,
                owned_by=model_info.namespace,
                installed=is_installed,
                description=model_info.description,
            ))
        
        return ModelsResponse(data=models_data)
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@app.post("/v1/audio/speech", tags=["Speech"])
async def create_speech(request: SpeechRequest):
    """Generate speech from text (OpenAI-compatible endpoint).
    
    Compatible with OpenAI's /v1/audio/speech API.
    
    Example:
        curl http://localhost:11435/v1/audio/speech \\
          -H "Content-Type: application/json" \\
          -d '{"model":"chatterbox-turbo","input":"Hello world","voice":"my-voice"}' \\
          --output speech.mp3
    """
    try:
        storage = WavhostStorage()
        registry = ModelRegistry()
        voice_storage = VoiceStorage()
        
        model_info = registry.get_model_info(request.model)
        checkpoint = storage.ensure_checkpoint(model_info)
        backend = create_backend(model_info, checkpoint_path=checkpoint)

        voice_arg, voice_handle = resolve_voice(request.voice, voice_storage)
        if voice_handle:
            logger.info(f"Using saved voice: {request.voice}")
        elif voice_arg:
            logger.info(f"Using voice/speaker: {voice_arg}")

        logger.info(
            f"Generating speech for model={request.model}, length={len(request.input)}"
        )
        wav, sr = backend.generate(
            request.input,
            voice=voice_arg,
            voice_handle=voice_handle,
            **({"language": request.language} if request.language else {}),
        )

        audio_bytes = AudioConverter.convert(wav, sr, request.response_format)
        media_type = AudioConverter.get_media_type(request.response_format)
        filename = AudioConverter.get_filename(request.response_format)

        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )
        
    except ModelNotFoundError as e:
        logger.warning(f"Model not found: {e.model_name}")
        raise HTTPException(
            status_code=404,
            detail=f"Model '{e.model_name}' not found. Use GET /v1/models to see available models."
        )
    except ModelNotInstalledError as e:
        logger.warning(f"Model not installed: {e.model_name}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except (BackendError, StorageError) as e:
        logger.error(f"Backend/storage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in speech generation")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating speech: {str(e)}"
        )


# Voice management endpoints

class VoiceInfo(BaseModel):
    """Voice information model."""
    
    name: str
    description: str = ""
    backend: str
    ref_audio: dict


class VoiceListResponse(BaseModel):
    """Response model for voice list endpoint."""
    
    object: Literal["list"] = "list"
    data: list[VoiceInfo]


class VoiceCreateResponse(BaseModel):
    """Response model for voice creation."""
    
    name: str
    message: str


class VoiceDeleteResponse(BaseModel):
    """Response model for voice deletion."""
    
    name: str
    deleted: bool


@app.post("/v1/voices", response_model=VoiceCreateResponse, tags=["Voices"])
async def create_voice(
    name: str = Form(...),
    file: UploadFile = File(...),
    description: str = Form(""),
):
    """Create a new voice from reference audio.
    
    Upload reference audio to create a saved voice that can be used
    in speech generation requests.
    
    Example:
        curl -X POST http://localhost:11435/v1/voices \\
          -F "name=my-voice" \\
          -F "file=@reference.wav" \\
          -F "description=My custom voice"
    """
    try:
        voice_storage = VoiceStorage()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = Path(tmp.name)
            content = await file.read()
            tmp.write(content)
        
        try:
            # Create voice from uploaded file
            voice_storage.create_voice(
                name=name,
                ref_audio_path=tmp_path,
                description=description,
            )
            
            logger.info(f"Created voice via API: {name}")
            
            return VoiceCreateResponse(
                name=name,
                message=f"Voice '{name}' created successfully"
            )
            
        finally:
            # Clean up temporary file
            if tmp_path.exists():
                tmp_path.unlink()
        
    except VoiceAlreadyExistsError as e:
        logger.warning(f"Voice creation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Voice '{name}' already exists. Use a different name or delete the existing voice first."
        )
    except VoiceError as e:
        logger.error(f"Voice creation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error creating voice")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating voice: {str(e)}"
        )


@app.get("/v1/voices", response_model=VoiceListResponse, tags=["Voices"])
async def list_voices():
    """List all saved voices.
    
    Returns a list of all voices in the local voice library.
    
    Example:
        curl http://localhost:11435/v1/voices
    """
    try:
        voice_storage = VoiceStorage()
        voices = voice_storage.list_voices()
        
        voice_data = [
            VoiceInfo(
                name=v["name"],
                description=v.get("description", ""),
                backend=v.get("backend", ""),
                ref_audio=v.get("ref_audio", {})
            )
            for v in voices
        ]
        
        return VoiceListResponse(data=voice_data)
        
    except Exception as e:
        logger.exception("Error listing voices")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing voices: {str(e)}"
        )


@app.get("/v1/voices/{name}", response_model=VoiceInfo, tags=["Voices"])
async def get_voice(name: str):
    """Get details about a specific voice.
    
    Returns information about a saved voice including its metadata
    and reference audio details.
    
    Example:
        curl http://localhost:11435/v1/voices/my-voice
    """
    try:
        voice_storage = VoiceStorage()
        manifest = voice_storage.get_voice(name)
        
        return VoiceInfo(
            name=manifest["name"],
            description=manifest.get("description", ""),
            backend=manifest.get("backend", ""),
            ref_audio=manifest.get("ref_audio", {})
        )
        
    except VoiceNotFoundError as e:
        logger.warning(f"Voice not found: {name}")
        raise HTTPException(
            status_code=404,
            detail=f"Voice '{name}' not found. Use GET /v1/voices to see available voices."
        )
    except Exception as e:
        logger.exception("Error getting voice")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting voice: {str(e)}"
        )


@app.delete("/v1/voices/{name}", response_model=VoiceDeleteResponse, tags=["Voices"])
async def delete_voice(name: str):
    """Delete a saved voice.
    
    Removes a voice from the local library and cleans up unused
    reference audio blobs.
    
    Example:
        curl -X DELETE http://localhost:11435/v1/voices/my-voice
    """
    try:
        voice_storage = VoiceStorage()
        
        if not voice_storage.voice_exists(name):
            raise HTTPException(
                status_code=404,
                detail=f"Voice '{name}' not found"
            )
        
        deleted = voice_storage.delete_voice(name)
        
        if deleted:
            logger.info(f"Deleted voice via API: {name}")
            return VoiceDeleteResponse(name=name, deleted=True)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Voice '{name}' not found"
            )
        
    except VoiceError as e:
        logger.error(f"Voice deletion error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting voice")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting voice: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=11435)
