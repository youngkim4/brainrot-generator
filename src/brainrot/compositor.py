"""Video compositing using MoviePy 2."""

from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
)

from .captions import create_caption_frame
from .config import PipelineConfig, VideoConfig
from .timestamps import WordTimestamp


def _get_render_config(config: PipelineConfig) -> VideoConfig:
    """Return half-res config for dev mode, full-res for production."""
    if config.dev_mode:
        return VideoConfig(
            width=config.video.width // 2,
            height=config.video.height // 2,
            fps=config.video.fps,
            max_duration=config.video.max_duration,
        )
    return config.video


def _make_caption_clip(
    words: list[WordTimestamp],
    video_config: VideoConfig,
    caption_style: CaptionStyle,
    start: float,
    end: float,
) -> ImageClip:
    """Create a caption overlay clip for a time range."""
    mid_time = (start + end) / 2
    frame = create_caption_frame(words, mid_time, video_config, caption_style)
    frame_array = np.array(frame)

    return (
        ImageClip(frame_array)
        .with_duration(end - start)
        .with_start(start)
    )


from .config import CaptionStyle


def compose_video(
    background_path: Path,
    audio_path: Path,
    words: list[WordTimestamp],
    config: PipelineConfig,
) -> Path:
    """Assemble final video: background + audio + animated captions."""
    render_config = _get_render_config(config)

    audio = AudioFileClip(str(audio_path))
    audio_duration = min(audio.duration, config.video.max_duration)

    bg = (
        VideoFileClip(str(background_path))
        .with_duration(audio_duration)
        .resized((render_config.width, render_config.height))
    )

    # Build caption overlay clips grouped by words_per_group
    caption_clips = []
    n = config.captions.words_per_group
    for group_start_idx in range(0, len(words), n):
        group = words[group_start_idx : group_start_idx + n]
        if not group:
            break
        start = group[0].start
        end = group[-1].end
        clip = _make_caption_clip(words, render_config, config.captions, start, end)
        caption_clips.append(clip)

    final = CompositeVideoClip([bg, *caption_clips])
    final = final.with_audio(audio.with_duration(audio_duration))

    output_path = config.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final.write_videofile(
        str(output_path),
        fps=render_config.fps,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )

    # Clean up
    audio.close()
    bg.close()
    final.close()

    return output_path
