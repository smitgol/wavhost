"""Tiny audio I/O helpers."""

import io
import wave
from pathlib import Path
from typing import Union

import torch


def _pcm16_interleaved(audio: torch.Tensor) -> tuple[bytes, int]:
    """Encode a float waveform as interleaved signed 16-bit PCM.

    Args:
        audio: Float waveform in roughly [-1, 1], shape (channels, samples)
            or (samples,).

    Returns:
        ``(pcm_bytes, channel_count)`` with little-endian interleaved frames.
    """
    wav = audio.detach().float().cpu().clamp(-1.0, 1.0)
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    if wav.ndim != 2:
        raise ValueError(f"Expected 1D or 2D audio, got shape {tuple(wav.shape)}")

    channels = int(wav.shape[0])
    # (channels, samples) -> (samples, channels) so WAV/PCM frames interleave.
    pcm = (wav * 32767.0).to(torch.int16).transpose(0, 1).contiguous()
    offset = pcm.storage_offset() * pcm.element_size()
    nbytes = pcm.numel() * pcm.element_size()
    return bytes(pcm.untyped_storage())[offset : offset + nbytes], channels


def encode_wav(wav: torch.Tensor, sample_rate: int) -> bytes:
    """Encode a float waveform as 16-bit PCM WAV bytes.

    Uses the stdlib ``wave`` module so WAV output does not depend on
    torchaudio/TorchCodec (required by ``torchaudio.save`` since 2.9).
    """
    pcm, channels = _pcm16_interleaved(wav)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(int(sample_rate))
        writer.writeframes(pcm)
    return buf.getvalue()


def save_wav(path: Union[str, Path], wav: torch.Tensor, sample_rate: int) -> Path:
    """Write a float waveform as 16-bit PCM WAV (plays correctly everywhere)."""
    out = Path(path)
    out.write_bytes(encode_wav(wav, sample_rate))
    return out
