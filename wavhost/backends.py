"""TTS backend protocol and implementations."""

import inspect
from pathlib import Path
from typing import Any, Optional, Protocol, Union

import torch

from wavhost import dependencies
from wavhost.config import CPU_DEVICE, DEFAULT_DEVICE, DEFAULT_SAMPLE_RATE
from wavhost.exceptions import BackendError
from wavhost.logging_config import get_logger
from wavhost.registry import (
    ModelInfo,
    QWEN_DEFAULT_SPEAKER,
    QWEN_SPEAKERS,
)

logger = get_logger(__name__)

CHATTERBOX = "chatterbox"
QWEN = "qwen"

# PyPI chatterbox-tts 0.1.7 loads Turbo only. Nano (GPT2-small + t3_nano_v1)
# landed on GitHub later; register the missing backbone until a release ships
# from_local(..., nano=True).
_GPT2_SMALL_CONFIG = {
    "activation_function": "gelu_new",
    "architectures": ["GPT2LMHeadModel"],
    "attn_pdrop": 0.1,
    "bos_token_id": 50256,
    "embd_pdrop": 0.1,
    "eos_token_id": 50256,
    "initializer_range": 0.02,
    "layer_norm_epsilon": 1e-05,
    "model_type": "gpt2",
    "n_ctx": 8196,
    "n_embd": 768,
    "hidden_size": 768,
    "n_head": 12,
    "n_layer": 12,
    "n_positions": 8196,
    "n_special": 0,
    "predict_special_tokens": True,
    "resid_pdrop": 0.1,
    "summary_activation": None,
    "summary_first_dropout": 0.1,
    "summary_proj_to_labels": True,
    "summary_type": "cls_index",
    "summary_use_proj": True,
    "task_specific_params": {
        "text-generation": {"do_sample": True, "max_length": 50}
    },
    "vocab_size": 50276,
}

# Kept for older imports / tests.
BACKEND_NAME = CHATTERBOX
QWEN_BACKEND_NAME = QWEN


def _from_local_kwargs(loader: Any, requested: dict[str, Any]) -> dict[str, Any]:
    """Drop kwargs the installed ``from_local`` does not accept."""
    params = inspect.signature(loader).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return dict(requested)
    return {k: v for k, v in requested.items() if k in params}


def _ensure_gpt2_small_config() -> None:
    from chatterbox.models.t3.llama_configs import LLAMA_CONFIGS

    LLAMA_CONFIGS.setdefault("GPT2_small", _GPT2_SMALL_CONFIG)


def _load_chatterbox_nano_compat(model_cls: Any, ckpt_dir: Path, device: str) -> Any:
    """Load Nano on chatterbox-tts builds that lack ``from_local(..., nano=True)``."""
    from safetensors.torch import load_file
    from transformers import AutoTokenizer

    from chatterbox.models.s3gen import S3Gen
    from chatterbox.models.t3 import T3
    from chatterbox.models.t3.modules.t3_config import T3Config
    from chatterbox.models.voice_encoder import VoiceEncoder
    from chatterbox.tts_turbo import Conditionals

    _ensure_gpt2_small_config()
    ckpt_dir = Path(ckpt_dir)
    t3_path = ckpt_dir / "t3_nano_v1.safetensors"
    if not t3_path.is_file():
        raise BackendError(
            f"Chatterbox Nano checkpoint is missing {t3_path.name} in {ckpt_dir}"
        )

    map_location = torch.device("cpu") if device in ("cpu", "mps") else None

    ve = VoiceEncoder()
    ve.load_state_dict(load_file(ckpt_dir / "ve.safetensors"))
    ve.to(device).eval()

    hp = T3Config(text_tokens_dict_size=50276)
    hp.llama_config_name = "GPT2_small"
    hp.speech_tokens_dict_size = 6563
    hp.input_pos_emb = None
    hp.speech_cond_prompt_len = 375
    hp.use_perceiver_resampler = False
    hp.emotion_adv = False

    t3 = T3(hp)
    t3_state = load_file(t3_path)
    if "model" in t3_state.keys():
        t3_state = t3_state["model"][0]
    t3.load_state_dict(t3_state)
    del t3.tfmr.wte
    t3.to(device).eval()

    s3gen = S3Gen(meanflow=True)
    s3gen.load_state_dict(load_file(ckpt_dir / "s3gen_meanflow.safetensors"), strict=True)
    s3gen.to(device).eval()

    tokenizer = AutoTokenizer.from_pretrained(ckpt_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    conds = None
    builtin_voice = ckpt_dir / "conds.pt"
    if builtin_voice.exists():
        conds = Conditionals.load(builtin_voice, map_location=map_location).to(device)

    return model_cls(t3, s3gen, ve, tokenizer, device, conds=conds)


def _load_chatterbox_turbo(
    model_cls: Any,
    ckpt_dir: Path,
    device: str,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> Any:
    requested = dict(model_kwargs or {})
    loader = model_cls.from_local
    accepted = _from_local_kwargs(loader, requested)
    if requested.get("nano") and "nano" not in inspect.signature(loader).parameters:
        logger.info(
            "Installed chatterbox-tts has no from_local(nano=...); "
            "loading Nano with a compatibility loader"
        )
        return _load_chatterbox_nano_compat(model_cls, Path(ckpt_dir), device)
    return loader(ckpt_dir, device, **accepted)


def _detect_device() -> str:
    if torch.cuda.is_available():
        return DEFAULT_DEVICE
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return CPU_DEVICE


def _require_checkpoint(path: Path) -> Path:
    if not path.is_dir():
        raise BackendError(
            f"Checkpoint directory not found: {path}. "
            f"Pull the model first with: wavhost pull <model>"
        )
    return path


def _ref_audio_path(
    voice: Optional[str] = None,
    voice_handle: Optional[Any] = None,
    *,
    require: bool = False,
) -> Optional[str]:
    """Resolve a reference audio path from a saved-voice handle or filesystem path."""
    if voice_handle is not None:
        if isinstance(voice_handle, dict) and "ref_audio_path" in voice_handle:
            path = Path(voice_handle["ref_audio_path"])
            if not path.exists():
                raise BackendError(f"Voice reference audio not found: {path}")
            return str(path)
        raise BackendError(f"Invalid voice handle: {voice_handle}")

    if voice:
        path = Path(voice)
        if path.exists():
            return str(path)
        if require:
            raise BackendError(f"Reference voice audio not found: {voice}")
    elif require:
        raise BackendError("Reference voice audio is required")
    return None


def _voice_handle(ref_audio_path: str) -> dict[str, str]:
    path = Path(ref_audio_path)
    if not path.exists():
        raise BackendError(f"Reference audio not found: {ref_audio_path}")
    return {"ref_audio_path": str(path)}


class TTSBackend(Protocol):
    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        voice_handle: Optional[Any] = None,
        **kwargs,
    ) -> tuple[torch.Tensor, int]: ...

    def create_voice(self, ref_audio_path: str, **kwargs) -> Any: ...

    @property
    def sample_rate(self) -> int: ...


class ChatterboxBackend:
    """Local Chatterbox checkpoint; never hits the Hub at runtime."""

    def __init__(
        self,
        model_class: str,
        checkpoint_path: Union[str, Path],
        model_kwargs: Optional[dict] = None,
        device: Optional[str] = None,
    ):
        self._model_class = model_class
        self._model_kwargs = model_kwargs or {}
        self._multilingual = model_class == "ChatterboxMultilingualTTS"
        self._default_language = self._model_kwargs.get("default_language", "en")
        self._checkpoint_path = _require_checkpoint(Path(checkpoint_path))
        self._device = device or _detect_device()
        self._model = None
        self._sr = DEFAULT_SAMPLE_RATE
        logger.info(
            f"Initialized {model_class} on {self._device} from {self._checkpoint_path}"
        )

    def _load_model(self) -> None:
        if self._model is not None:
            return
        if not dependencies.is_installed(CHATTERBOX):
            raise BackendError(dependencies.missing_engine_message(CHATTERBOX))

        logger.info(f"Loading {self._model_class} from {self._checkpoint_path}...")
        try:
            if self._model_class == "ChatterboxTurboTTS":
                from chatterbox.tts_turbo import ChatterboxTurboTTS

                self._model = _load_chatterbox_turbo(
                    ChatterboxTurboTTS,
                    self._checkpoint_path,
                    self._device,
                    self._model_kwargs,
                )
            elif self._model_class == "ChatterboxMultilingualTTS":
                from chatterbox.mtl_tts import ChatterboxMultilingualTTS

                self._model = ChatterboxMultilingualTTS.from_local(
                    self._checkpoint_path, self._device
                )
            else:
                from chatterbox.tts import ChatterboxTTS

                self._model = ChatterboxTTS.from_local(
                    self._checkpoint_path, self._device
                )
            self._sr = self._model.sr
        except ImportError as e:
            raise BackendError(
                f"Failed to import Chatterbox. "
                f"Install with: {dependencies.install_hint(CHATTERBOX)}\nError: {e}"
            ) from e
        except Exception as e:
            logger.debug("Chatterbox model load failed", exc_info=True)
            raise BackendError(
                f"Failed to load Chatterbox model: {type(e).__name__}: {e}"
            ) from e

    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        voice_handle: Optional[Any] = None,
        **kwargs,
    ) -> tuple[torch.Tensor, int]:
        self._load_model()
        generate_kwargs = kwargs.copy()
        # Accept either language or language_id from CLI/API.
        language = generate_kwargs.pop("language", None)
        language_id = generate_kwargs.pop("language_id", None) or language

        ref = _ref_audio_path(voice, voice_handle, require=bool(voice or voice_handle))
        if ref:
            generate_kwargs["audio_prompt_path"] = ref

        try:
            if self._multilingual:
                lang = (language_id or self._default_language or "en").lower()
                return (
                    self._model.generate(text, lang, **generate_kwargs),
                    self._sr,
                )
            return self._model.generate(text, **generate_kwargs), self._sr
        except Exception as e:
            raise BackendError(f"Speech generation failed: {e}") from e

    def create_voice(self, ref_audio_path: str, **kwargs) -> dict[str, str]:
        return _voice_handle(ref_audio_path)

    @property
    def sample_rate(self) -> int:
        return self._sr


class QwenBackend:
    """Qwen3-TTS: CustomVoice (named speakers) or Base (reference cloning)."""

    def __init__(
        self,
        model_class: str,
        checkpoint_path: Union[str, Path],
        model_kwargs: Optional[dict] = None,
        device: Optional[str] = None,
    ):
        self._model_kwargs = model_kwargs or {}
        self._task = self._model_kwargs.get("task", "custom_voice")
        self._default_speaker = self._model_kwargs.get(
            "default_speaker", QWEN_DEFAULT_SPEAKER
        )
        self._checkpoint_path = _require_checkpoint(Path(checkpoint_path))
        self._device = device or _detect_device()
        self._model = None
        self._sr = DEFAULT_SAMPLE_RATE
        logger.info(
            f"Initialized Qwen3-TTS ({self._task}) on {self._device} "
            f"from {self._checkpoint_path}"
        )

    def _load_model(self) -> None:
        if self._model is not None:
            return
        if not dependencies.is_installed(QWEN):
            raise BackendError(dependencies.missing_engine_message(QWEN))

        logger.info(f"Loading Qwen3TTSModel from {self._checkpoint_path}...")
        try:
            from qwen_tts import Qwen3TTSModel

            device_map = "cuda:0" if self._device == "cuda" else self._device
            dtype = (
                torch.bfloat16 if self._device in ("cuda", "mps") else torch.float32
            )
            self._model = Qwen3TTSModel.from_pretrained(
                str(self._checkpoint_path),
                device_map=device_map,
                dtype=dtype,
            )
            self._sr = 24000
        except ImportError as e:
            raise BackendError(
                f"Failed to import Qwen3-TTS. "
                f"Install with: {dependencies.install_hint(QWEN)}\nError: {e}"
            ) from e
        except Exception as e:
            logger.debug("Qwen3-TTS model load failed", exc_info=True)
            raise BackendError(
                f"Failed to load Qwen3-TTS model: {type(e).__name__}: {e}"
            ) from e

    @staticmethod
    def _to_tensor(wavs: Any) -> torch.Tensor:
        wav = torch.as_tensor(wavs[0] if isinstance(wavs, list) else wavs).float()
        if wav.ndim == 1:
            return wav.unsqueeze(0)
        if wav.ndim == 2 and wav.shape[0] > wav.shape[1]:
            return wav.transpose(0, 1)
        return wav

    def _speaker(self, voice: Optional[str]) -> str:
        if voice is None or voice.lower() in {"", "default"}:
            return self._default_speaker
        key = voice.lower()
        if key in QWEN_SPEAKERS:
            return QWEN_SPEAKERS[key]
        names = ", ".join(sorted(QWEN_SPEAKERS.values()))
        raise BackendError(f"Unknown Qwen speaker '{voice}'. Use one of: {names}")

    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        voice_handle: Optional[Any] = None,
        **kwargs,
    ) -> tuple[torch.Tensor, int]:
        self._load_model()
        opts = kwargs.copy()
        ref = _ref_audio_path(voice, voice_handle)
        # CLI/API may send language_id; Qwen wants language names (English, …).
        if "language" not in opts and "language_id" in opts:
            opts["language"] = opts.pop("language_id")
        else:
            opts.pop("language_id", None)

        try:
            if self._task == "custom_voice":
                if ref:
                    raise BackendError(
                        "This Qwen CustomVoice model uses named speakers, not "
                        "reference-audio cloning. Pass a speaker such as Ryan "
                        "or Aiden, or pull a qwen-*-base model for voice cloning."
                    )
                call = {
                    "text": text,
                    "speaker": self._speaker(voice),
                    "language": opts.pop("language", "English"),
                    "non_streaming_mode": opts.pop("non_streaming_mode", True),
                    # Stabler than the checkpoint's 0.9 / top_p=1.0 defaults.
                    "temperature": opts.pop("temperature", 0.7),
                    "top_p": opts.pop("top_p", 0.9),
                    "repetition_penalty": opts.pop("repetition_penalty", 1.1),
                    **opts,
                }
                instruct = call.pop("instruct", None)
                if instruct:
                    call["instruct"] = instruct
                wavs, sr = self._model.generate_custom_voice(**call)
            else:
                if not ref:
                    raise BackendError(
                        "Qwen Base models require a reference voice for cloning. "
                        "Use --voice with a saved voice or audio file, or pull "
                        "a qwen-*-customvoice model for predefined speakers."
                    )
                wavs, sr = self._model.generate_voice_clone(
                    text=text,
                    language=opts.pop("language", "English"),
                    ref_audio=ref,
                    ref_text=opts.pop("ref_text", None),
                    x_vector_only_mode=opts.pop("x_vector_only_mode", True),
                    **opts,
                )
            self._sr = sr
            return self._to_tensor(wavs), sr
        except BackendError:
            raise
        except Exception as e:
            raise BackendError(f"Speech generation failed: {e}") from e

    def create_voice(self, ref_audio_path: str, **kwargs) -> dict[str, str]:
        return _voice_handle(ref_audio_path)

    @property
    def sample_rate(self) -> int:
        return self._sr


def create_backend(
    model_info: ModelInfo,
    device: Optional[str] = None,
    checkpoint_path: Optional[Union[str, Path]] = None,
) -> TTSBackend:
    if checkpoint_path is None:
        raise BackendError(
            "checkpoint_path is required. Pull the model first with: wavhost pull <model>"
        )

    actual = device or model_info.recommended_device
    if actual == DEFAULT_DEVICE and not torch.cuda.is_available():
        message = "GPU not available, falling back to CPU"
        hint = dependencies.gpu_build_warning()
        if hint:
            message = f"{message}\n{hint}"
        logger.warning(message)
        actual = CPU_DEVICE

    common = dict(
        model_class=model_info.model_class,
        checkpoint_path=checkpoint_path,
        model_kwargs=model_info.model_kwargs,
        device=actual,
    )
    if model_info.backend == CHATTERBOX:
        return ChatterboxBackend(**common)
    if model_info.backend == QWEN:
        return QwenBackend(**common)
    raise BackendError(f"Unsupported backend type: {model_info.backend}")
