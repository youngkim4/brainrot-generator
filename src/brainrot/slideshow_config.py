"""Slideshow config and types."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SlideshowConfig:
    prompt: str  # question shown on intro card, e.g. "Where would you live?"
    output_path: Path
    bgm_path: Path
    image_paths: tuple[Path, ...] = ()  # pre-existing images, skip generation
    image_dir: Path | None = None  # directory to save generated images
    num_images: int = 8
    seconds_per_slide: float = 7.0
    intro_duration: float = 4.0
    fade_duration: float = 0.5
    ken_burns_zoom: float = 1.15  # 15% zoom over slide duration
    width: int = 1080
    height: int = 1920
    fps: int = 30
    bgm_volume: float = 0.8
    gemini_model: str = "gemini-3.1-flash-image-preview"
    dev_mode: bool = False

    @property
    def render_width(self) -> int:
        return self.width // 2 if self.dev_mode else self.width

    @property
    def render_height(self) -> int:
        return self.height // 2 if self.dev_mode else self.height
