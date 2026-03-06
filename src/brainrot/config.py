"""Configuration and shared types."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TTSProvider(Enum):
    EDGE = "edge"
    ELEVENLABS = "elevenlabs"


@dataclass(frozen=True)
class VideoConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    max_duration: int = 60


@dataclass(frozen=True)
class CaptionStyle:
    font_size: int = 70
    font_color: str = "white"
    stroke_color: str = "black"
    stroke_width: int = 3
    position: str = "center"
    words_per_group: int = 3
    highlight_color: str = "yellow"


@dataclass(frozen=True)
class PipelineConfig:
    story_text: str
    background_video: Path
    output_path: Path
    tts_provider: TTSProvider = TTSProvider.EDGE
    tts_voice: str = "en-US-ChristopherNeural"
    elevenlabs_voice_id: str = ""
    elevenlabs_api_key: str = ""
    video: VideoConfig = field(default_factory=VideoConfig)
    captions: CaptionStyle = field(default_factory=CaptionStyle)
    dev_mode: bool = False  # use 540x960 for fast iteration
