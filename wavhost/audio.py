"""Tiny audio I/O helpers."""

from pathlib import Path
from typing import Union

import torch
import torchaudio


def save_wav(path: Union[str, Path], wav: torch.Tensor, sample_rate: int) -> Path:
    """Write a float waveform as 16-bit PCM WAV (plays correctly everywhere)."""
    out = Path(path)
    wav = wav.detach().float().cpu().clamp(-1.0, 1.0)
    torchaudio.save(
        str(out),
        wav,
        sample_rate,
        encoding="PCM_S",
        bits_per_sample=16,
    )
    return out
