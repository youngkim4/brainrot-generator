"""Video compositing."""

from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    vfx,
)

from .captions import create_single_word_frame
from .config import CaptionStyle, PipelineConfig, VideoConfig
from .timestamps import WordTimestamp


def _get_render_config(config: PipelineConfig) -> VideoConfig:
    """Half-res if dev, else full."""
    if config.dev_mode:
        return VideoConfig(
            width=config.video.width // 2,
            height=config.video.height // 2,
            fps=config.video.fps,
            min_duration=config.video.min_duration,
            max_duration=config.video.max_duration,
        )
    return config.video


def _crop_to_portrait(clip: VideoFileClip, target_w: int, target_h: int) -> VideoFileClip:
    """Crop+scale to portrait."""
    src_w, src_h = clip.size
    target_aspect = target_w / target_h

    # scale short side, crop excess
    src_aspect = src_w / src_h
    if src_aspect > target_aspect:
        # wider — scale height, crop width
        scale = target_h / src_h
        scaled = clip.resized(scale)
        excess = scaled.size[0] - target_w
        x_center = excess // 2
        return scaled.cropped(x1=x_center, x2=x_center + target_w)
    else:
        # taller — scale width, crop height
        scale = target_w / src_w
        scaled = clip.resized(scale)
        excess = scaled.size[1] - target_h
        y_center = excess // 2
        return scaled.cropped(y1=y_center, y2=y_center + target_h)


def _pop_scale(t: float, pop_duration: float = 0.08, scale_from: float = 1.3) -> float:
    """Scale factor: starts big, settles to 1.0."""
    if t < pop_duration:
        return scale_from + (1.0 - scale_from) * (t / pop_duration)
    return 1.0


def _make_word_clips(
    words: list[WordTimestamp],
    video_config: VideoConfig,
    caption_style: CaptionStyle,
) -> list[VideoFileClip | ImageClip]:
    """One pop-in clip per word."""
    clips = []
    for w in words:
        frame = create_single_word_frame(w.word, video_config, caption_style)
        duration = w.end - w.start
        if duration <= 0:
            continue
        clip = (
            ImageClip(np.array(frame))
            .with_duration(duration)
            .with_start(w.start)
            .with_position("center")
            .resized(lambda t: _pop_scale(t))
        )
        clips.append(clip)
    return clips


def compose_video(
    background_path: Path,
    audio_path: Path,
    words: list[WordTimestamp],
    config: PipelineConfig,
) -> Path:
    """Assemble bg + audio + captions."""
    render_config = _get_render_config(config)
    caption_style = config.captions
    if config.dev_mode:
        scale = render_config.width / config.video.width
        caption_style = CaptionStyle(
            font_size=max(1, int(caption_style.font_size * scale)),
            font_color=caption_style.font_color,
            stroke_color=caption_style.stroke_color,
            stroke_width=max(1, int(caption_style.stroke_width * scale)),
            position=caption_style.position,
            words_per_group=caption_style.words_per_group,
            highlight_color=caption_style.highlight_color,
        )

    audio = AudioFileClip(str(audio_path))
    bg = None
    final = None
    try:
        audio_duration = min(audio.duration, config.video.max_duration)

        bg = VideoFileClip(str(background_path))
        if bg.duration < audio_duration:
            raise ValueError(
                f"Background video ({bg.duration:.1f}s) is shorter than audio ({audio_duration:.1f}s)"
            )
        bg = bg.with_duration(audio_duration)
        bg = _crop_to_portrait(bg, render_config.width, render_config.height)

        # one pop-in caption per word
        caption_clips = _make_word_clips(words, render_config, caption_style)

        final = CompositeVideoClip([bg, *caption_clips])

        # mix narration + bgm
        narration = audio.with_duration(audio_duration)
        if config.bgm_path and config.bgm_path.exists():
            bgm = AudioFileClip(str(config.bgm_path))
            bgm = bgm.with_duration(audio_duration).with_volume_scaled(config.bgm_volume)
            mixed = CompositeAudioClip([narration, bgm])
            final = final.with_audio(mixed)
        else:
            final = final.with_audio(narration)

        output_path = config.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        final.write_videofile(
            str(output_path),
            fps=render_config.fps,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

        return output_path
    finally:
        if final is not None:
            final.close()
        if bg is not None:
            bg.close()
        audio.close()
