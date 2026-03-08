"""Programmatic SFX generation for quiz videos — no external assets needed."""

import struct
import tempfile
import math
from pathlib import Path


SAMPLE_RATE = 44100


def _write_wav(path: Path, samples: list[float], sample_rate: int = SAMPLE_RATE) -> Path:
    """Write mono 16-bit WAV file from float samples [-1.0, 1.0]."""
    n = len(samples)
    data_size = n * 2
    file_size = 36 + data_size

    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", file_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # chunk size
        f.write(struct.pack("<H", 1))   # PCM
        f.write(struct.pack("<H", 1))   # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))   # block align
        f.write(struct.pack("<H", 16))  # bits per sample
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            f.write(struct.pack("<h", int(clamped * 32767)))

    return path


def _sine(freq: float, duration: float, volume: float = 0.5) -> list[float]:
    """Generate sine wave samples."""
    n = int(SAMPLE_RATE * duration)
    return [
        volume * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
        for i in range(n)
    ]


def _fade(samples: list[float], fade_in: float = 0.0, fade_out: float = 0.0) -> list[float]:
    """Apply fade in/out to samples."""
    result = list(samples)
    n = len(result)
    fade_in_samples = int(SAMPLE_RATE * fade_in)
    fade_out_samples = int(SAMPLE_RATE * fade_out)

    for i in range(min(fade_in_samples, n)):
        result[i] *= i / fade_in_samples

    for i in range(min(fade_out_samples, n)):
        idx = n - 1 - i
        result[idx] *= i / fade_out_samples

    return result


def _mix(tracks: list[list[float]]) -> list[float]:
    """Mix multiple sample tracks together."""
    max_len = max(len(t) for t in tracks)
    result = [0.0] * max_len
    for track in tracks:
        for i, s in enumerate(track):
            result[i] += s
    return result


def generate_tick(output_dir: Path) -> Path:
    """Short click/tick — played each second during countdown."""
    # sharp attack, quick decay
    samples = _sine(880, 0.06, volume=0.4)
    overtone = _sine(1760, 0.03, volume=0.15)
    mixed = _mix([samples, overtone])
    mixed = _fade(mixed, fade_in=0.002, fade_out=0.04)
    return _write_wav(output_dir / "tick.wav", mixed)


def generate_tick_urgent(output_dir: Path) -> Path:
    """Higher-pitched urgent tick — last few seconds."""
    samples = _sine(1200, 0.05, volume=0.5)
    overtone = _sine(2400, 0.03, volume=0.2)
    mixed = _mix([samples, overtone])
    mixed = _fade(mixed, fade_in=0.002, fade_out=0.03)
    return _write_wav(output_dir / "tick_urgent.wav", mixed)


def generate_reveal_correct(output_dir: Path) -> Path:
    """Ascending two-tone chime — correct answer revealed."""
    tone1 = _sine(523, 0.15, volume=0.4)   # C5
    tone2 = _sine(784, 0.25, volume=0.45)  # G5
    silence = [0.0] * int(SAMPLE_RATE * 0.05)
    samples = tone1 + silence + tone2
    samples = _fade(samples, fade_in=0.01, fade_out=0.1)
    return _write_wav(output_dir / "reveal_correct.wav", samples)


def generate_question_intro(output_dir: Path) -> Path:
    """Quick rising whoosh — new question appearing."""
    duration = 0.25
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        progress = i / n
        # sweep from 200 Hz to 600 Hz
        freq = 200 + 400 * progress
        volume = 0.3 * (1.0 - abs(progress - 0.5) * 2)  # peak in middle
        samples.append(volume * math.sin(2 * math.pi * freq * t))
    samples = _fade(samples, fade_in=0.02, fade_out=0.08)
    return _write_wav(output_dir / "question_intro.wav", samples)


def generate_countdown_start(output_dir: Path) -> Path:
    """Subtle tone — countdown phase begins."""
    tone = _sine(440, 0.12, volume=0.25)  # A4
    tone = _fade(tone, fade_in=0.01, fade_out=0.08)
    return _write_wav(output_dir / "countdown_start.wav", tone)


def generate_all_sfx(output_dir: Path | None = None) -> dict[str, Path]:
    """Generate all SFX files, return name->path mapping."""
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="quiz_sfx_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "tick": generate_tick(output_dir),
        "tick_urgent": generate_tick_urgent(output_dir),
        "reveal_correct": generate_reveal_correct(output_dir),
        "question_intro": generate_question_intro(output_dir),
        "countdown_start": generate_countdown_start(output_dir),
    }
