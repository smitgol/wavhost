"""Tests for PCM / audio format conversion."""

import struct

import pytest
import torch

from wavhost.server import (
    PCM_SAMPLE_RATES,
    AudioConverter,
    AudioFormat,
)


def _sine(sample_rate: int, seconds: float = 0.05, freq: float = 440.0) -> torch.Tensor:
    """Mono float32 sine in [-1, 1], shape (1, samples)."""
    n = int(sample_rate * seconds)
    t = torch.arange(n, dtype=torch.float32) / sample_rate
    return (0.5 * torch.sin(2 * torch.pi * freq * t)).unsqueeze(0)


@pytest.mark.parametrize(
    "fmt,rate",
    [
        (AudioFormat.PCM_16000, 16000),
        (AudioFormat.PCM_22050, 22050),
        (AudioFormat.PCM_24000, 24000),
        (AudioFormat.PCM_44100, 44100),
    ],
)
def test_pcm_rate_formats_produce_s16le_at_target_rate(fmt, rate):
    """Each pcm_* format is raw S16LE resampled to its named rate."""
    src_rate = 24000
    audio = _sine(src_rate, seconds=0.1)

    data = AudioConverter.convert(audio, src_rate, fmt)

    # int16 mono → 2 bytes per sample
    expected_samples = int(round(audio.shape[-1] * rate / src_rate))
    assert len(data) == expected_samples * 2
    assert len(data) % 2 == 0

    # First few samples should be valid int16 values
    first = struct.unpack_from("<h", data, 0)[0]
    assert -32768 <= first <= 32767


def test_plain_pcm_keeps_native_rate_as_s16le():
    """``pcm`` is S16LE at the model's native sample rate (no resample)."""
    src_rate = 24000
    audio = _sine(src_rate, seconds=0.05)

    data = AudioConverter.convert(audio, src_rate, AudioFormat.PCM)

    assert len(data) == audio.shape[-1] * 2


def test_pcm_clamps_out_of_range_floats():
    """Values outside [-1, 1] are clipped before int16 conversion."""
    audio = torch.tensor([[2.0, -2.0, 0.0]], dtype=torch.float32)

    data = AudioConverter.convert(audio, 16000, AudioFormat.PCM)
    samples = struct.unpack("<hhh", data)

    assert samples == (32767, -32767, 0)


def test_pcm_no_resample_when_rates_match():
    """pcm_24000 against a 24 kHz source keeps sample count."""
    audio = _sine(24000, seconds=0.1)
    data = AudioConverter.convert(audio, 24000, AudioFormat.PCM_24000)
    assert len(data) == audio.shape[-1] * 2


def test_is_pcm_covers_all_pcm_variants():
    for fmt in AudioFormat:
        if fmt.value.startswith("pcm"):
            assert AudioConverter.is_pcm(fmt)
        else:
            assert not AudioConverter.is_pcm(fmt)


def test_pcm_sample_rates_match_enum_names():
    for fmt, rate in PCM_SAMPLE_RATES.items():
        assert fmt.value == f"pcm_{rate}"


def test_get_filename_uses_pcm_extension():
    assert AudioConverter.get_filename(AudioFormat.PCM) == "speech.pcm"
    assert AudioConverter.get_filename(AudioFormat.PCM_16000) == "speech.pcm"
    assert AudioConverter.get_filename(AudioFormat.WAV) == "speech.wav"


def test_get_media_type_for_pcm():
    assert AudioConverter.get_media_type(AudioFormat.PCM_44100) == "audio/pcm"
