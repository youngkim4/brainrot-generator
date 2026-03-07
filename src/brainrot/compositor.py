"""Video compositing."""

from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
)

from .captions import create_single_word_frame
from .config import CaptionStyle, PipelineConfig, VideoConfig
from .reddit_overlay import create_reddit_card
from .timestamps import WordTimestamp

_INTRO_DURATION = 3.0
_POP_IN_MS = 0.15  # scale-up pop duration
_POP_OUT_MS = 0.12


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

    src_aspect = src_w / src_h
    if src_aspect > target_aspect:
        scale = target_h / src_h
        scaled = clip.resized(scale)
        excess = scaled.size[0] - target_w
        x_center = excess // 2
        return scaled.cropped(x1=x_center, x2=x_center + target_w)

    scale = target_w / src_w
    scaled = clip.resized(scale)
    excess = scaled.size[1] - target_h
    y_center = excess // 2
    return scaled.cropped(y1=y_center, y2=y_center + target_h)


def _pop_scale(t: float, pop_duration: float = 0.08, scale_from: float = 1.3) -> float:
    """Scale factor for word captions: starts big, settles to 1.0."""
    if t < pop_duration:
        return scale_from + (1.0 - scale_from) * (t / pop_duration)
    return 1.0


def _card_scale(t: float, total_duration: float) -> float:
    """Scale factor for reddit card: pop in at start, pop out at end."""
    # pop in: 0.3 -> 1.0
    if t < _POP_IN_MS:
        progress = t / _POP_IN_MS
        return 0.3 + 0.7 * progress
    # pop out: 1.0 -> 0.3
    time_left = total_duration - t
    if time_left < _POP_OUT_MS:
        progress = time_left / _POP_OUT_MS
        return 0.3 + 0.7 * progress
    return 1.0


def _make_word_clips(
    words: list[WordTimestamp],
    video_config: VideoConfig,
    caption_style: CaptionStyle,
    time_offset: float = 0.0,
) -> list[VideoFileClip | ImageClip]:
    """One pop-in clip per word, shifted by time_offset."""
    clips = []
    for w in words:
        frame = create_single_word_frame(w.word, video_config, caption_style)
        duration = w.end - w.start
        if duration <= 0:
            continue
        clip = (
            ImageClip(np.array(frame))
            .with_duration(duration)
            .with_start(w.start + time_offset)
            .with_position("center")
            .resized(_pop_scale)
        )
        clips.append(clip)
    return clips


def compose_video(
    background_path: Path,
    audio_path: Path,
    words: list[WordTimestamp],
    config: PipelineConfig,
) -> Path:
    """Assemble bg + audio + captions. Intro card plays first, then narration."""
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
    bgm = None
    sfx_clips: list[AudioFileClip] = []
    final = None
    try:
        audio_duration = min(audio.duration, config.video.max_duration)
        intro_duration = min(_INTRO_DURATION, config.video.max_duration - audio_duration)
        total_duration = intro_duration + audio_duration

        bg = VideoFileClip(str(background_path))
        # skip first 5s of background to avoid static intro
        bg_skip = 5.0 if bg.duration >= total_duration + 5.0 else 0.0
        if bg.duration < total_duration + bg_skip:
            raise ValueError(
                f"Background video ({bg.duration:.1f}s) shorter than needed ({total_duration:.1f}s)"
            )
        bg = bg.subclipped(bg_skip, bg_skip + total_duration)
        bg = _crop_to_portrait(bg, render_config.width, render_config.height)

        # render card at full res for crisp text, then scale to render size
        reddit_frame = create_reddit_card(config.story_text, config.video)
        if config.dev_mode:
            from PIL import Image as PILImage

            reddit_frame = reddit_frame.resize(
                (render_config.width, render_config.height), PILImage.LANCZOS
            )
        card_duration = intro_duration

        def card_scale_fn(t: float) -> float:
            return _card_scale(t, card_duration)

        reddit_clip = (
            ImageClip(np.array(reddit_frame))
            .with_duration(card_duration)
            .with_start(0)
            .with_position("center")
            .resized(card_scale_fn)
        )

        # captions start after intro
        caption_clips = _make_word_clips(
            words, render_config, caption_style, time_offset=intro_duration
        )

        final = CompositeVideoClip([bg, reddit_clip, *caption_clips])

        # narration starts after intro, bgm plays the whole time
        narration = audio.with_duration(audio_duration).with_start(intro_duration)
        audio_clips = [narration]

        # pop sfx for card appear/disappear
        sfx_dir = Path(__file__).parent.parent.parent / "assets" / "sfx"
        pop_in_path = sfx_dir / "pop_in.wav"
        pop_out_path = sfx_dir / "pop_out.wav"
        if pop_in_path.exists():
            pop_in_sfx = AudioFileClip(str(pop_in_path)).with_start(0)
            sfx_clips.append(pop_in_sfx)
            audio_clips.append(pop_in_sfx)
        if pop_out_path.exists():
            pop_out_sfx = AudioFileClip(str(pop_out_path)).with_start(
                max(0, card_duration - _POP_OUT_MS)
            )
            sfx_clips.append(pop_out_sfx)
            audio_clips.append(pop_out_sfx)

        if config.bgm_path and config.bgm_path.exists():
            bgm = AudioFileClip(str(config.bgm_path))
            bgm = bgm.with_duration(total_duration).with_volume_scaled(config.bgm_volume)
            audio_clips.append(bgm)

        final = final.with_audio(CompositeAudioClip(audio_clips))

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
        for sfx in sfx_clips:
            sfx.close()
        if bgm is not None:
            bgm.close()
        if bg is not None:
            bg.close()
        audio.close()
