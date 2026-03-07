"""Config and types."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TTSProvider(Enum):
    EDGE = "edge"
    ELEVENLABS = "elevenlabs"
    POLLY = "polly"


@dataclass(frozen=True)
class VideoConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    min_duration: int = 60
    max_duration: int = 180


@dataclass(frozen=True)
class CaptionStyle:
    font_size: int = 50
    font_color: str = "white"
    stroke_color: str = "black"
    stroke_width: int = 2
    position: str = "center"
    words_per_group: int = 3
    highlight_color: str = "yellow"


@dataclass(frozen=True)
class PipelineConfig:
    story_text: str
    background_video: Path
    output_path: Path
    tts_provider: TTSProvider = TTSProvider.POLLY
    tts_voice: str = "Brian"
    elevenlabs_voice_id: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    polly_region: str = "us-east-1"
    bgm_path: Path | None = None
    bgm_volume: float = 0.1  # relative to narration
    video: VideoConfig = field(default_factory=VideoConfig)
    captions: CaptionStyle = field(default_factory=CaptionStyle)
    dev_mode: bool = False  # half-res mode

    def __repr__(self) -> str:
        masked_key = "***" if self.elevenlabs_api_key else ""
        return (
            f"PipelineConfig(story_text={self.story_text!r}, "
            f"background_video={self.background_video!r}, "
            f"output_path={self.output_path!r}, "
            f"tts_provider={self.tts_provider!r}, "
            f"tts_voice={self.tts_voice!r}, "
            f"elevenlabs_voice_id={self.elevenlabs_voice_id!r}, "
            f"elevenlabs_api_key={masked_key!r}, "
            f"elevenlabs_model_id={self.elevenlabs_model_id!r}, "
            f"video={self.video!r}, "
            f"captions={self.captions!r}, "
            f"dev_mode={self.dev_mode!r})"
        )
