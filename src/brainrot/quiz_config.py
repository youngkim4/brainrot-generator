"""Quiz mode config and types."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .config import TTSProvider, VideoConfig


class QuizType(Enum):
    TRIVIA = "trivia"
    WYR = "wyr"


@dataclass(frozen=True)
class TriviaQuestion:
    question: str
    options: tuple[str, ...]
    correct: int  # 0-based index
    time_limit: float = 7.0

    def __post_init__(self) -> None:
        if not self.options:
            raise ValueError("Options must not be empty")
        if self.correct < 0 or self.correct >= len(self.options):
            raise ValueError(
                f"correct index {self.correct} out of range for {len(self.options)} options"
            )
        if self.time_limit <= 0:
            raise ValueError("time_limit must be positive")


@dataclass(frozen=True)
class WYRQuestion:
    option_a: str
    option_b: str
    time_limit: float = 6.0

    def __post_init__(self) -> None:
        if not self.option_a or not self.option_b:
            raise ValueError("Both option_a and option_b are required")
        if self.time_limit <= 0:
            raise ValueError("time_limit must be positive")


@dataclass(frozen=True)
class QuizData:
    quiz_type: QuizType
    questions: tuple[TriviaQuestion | WYRQuestion, ...]

    def __post_init__(self) -> None:
        if not self.questions:
            raise ValueError("Quiz must have at least one question")


@dataclass(frozen=True)
class QuizPipelineConfig:
    quiz_data: QuizData
    background_video: Path
    output_path: Path
    character_image: Path | None = None
    tts_provider: TTSProvider = TTSProvider.EDGE
    tts_voice: str = "en-US-ChristopherNeural"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    video: VideoConfig = field(default_factory=VideoConfig)
    dev_mode: bool = False
    reveal_duration: float = 1.5
    gap_duration: float = 0.3

    def __repr__(self) -> str:
        masked_key = "***" if self.elevenlabs_api_key else ""
        return (
            f"QuizPipelineConfig(quiz_type={self.quiz_data.quiz_type!r}, "
            f"questions={len(self.quiz_data.questions)}, "
            f"background_video={self.background_video!r}, "
            f"output_path={self.output_path!r}, "
            f"elevenlabs_api_key={masked_key!r}, "
            f"dev_mode={self.dev_mode!r})"
        )
