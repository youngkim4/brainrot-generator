"""Word-level timestamps."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WordTimestamp:
    word: str
    start: float
    end: float
    confidence: float


_MIN_CONFIDENCE = 0.5


def generate_timestamps(
    audio_path: Path, model_size: str = "base", min_confidence: float = _MIN_CONFIDENCE
) -> list[WordTimestamp]:
    """DTW word timestamps via whisper. Filters low-confidence words."""
    import whisper_timestamped as whisper

    model = whisper.load_model(model_size)
    audio = whisper.load_audio(str(audio_path))
    result = whisper.transcribe(model, audio, language="en")

    timestamps = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            confidence = word_info.get("confidence", 0.0)
            if confidence < min_confidence:
                continue
            timestamps.append(
                WordTimestamp(
                    word=word_info["text"].strip(),
                    start=word_info["start"],
                    end=word_info["end"],
                    confidence=confidence,
                )
            )

    return timestamps


def validate_timestamps(
    timestamps: list[WordTimestamp], audio_duration: float, max_drift: float = 1.0
) -> bool:
    """Check timestamps match audio length."""
    if not timestamps:
        return False

    last_end = timestamps[-1].end
    drift = abs(last_end - audio_duration)
    return drift <= max_drift
