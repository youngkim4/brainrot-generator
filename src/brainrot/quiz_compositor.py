"""Quiz video compositing with MoviePy 2."""

from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from .compositor import _crop_to_portrait
from .config import VideoConfig
from .quiz_config import QuizPipelineConfig, TriviaQuestion, WYRQuestion
from .quiz_renderer import (
    load_character_image,
    render_countdown_bar,
    render_question_frame,
)


MAX_COUNTDOWN_FRAMES = 30


def _get_render_config(config: QuizPipelineConfig) -> VideoConfig:
    """Half-res in dev mode."""
    if config.dev_mode:
        return VideoConfig(
            width=config.video.width // 2,
            height=config.video.height // 2,
            fps=config.video.fps,
            min_duration=config.video.min_duration,
            max_duration=config.video.max_duration,
        )
    return config.video


def _compute_total_duration(
    questions: tuple[TriviaQuestion | WYRQuestion, ...],
    config: QuizPipelineConfig,
) -> float:
    """Total video duration across all questions."""
    total = 0.0
    for q in questions:
        total += q.time_limit + config.reveal_duration + config.gap_duration
    return total


def compose_quiz_video(
    background_path: Path,
    audio_paths: list[Path],
    audio_durations: list[float],
    config: QuizPipelineConfig,
) -> Path:
    """Assemble quiz video: bg + question overlays + character + audio."""
    render_config = _get_render_config(config)
    questions = config.quiz_data.questions

    total_duration = _compute_total_duration(questions, config)

    bg = VideoFileClip(str(background_path))
    original_bg = bg
    final = None
    tts_audio_clips: list[AudioFileClip] = []
    try:
        # skip first 5s to avoid static intro
        bg_skip = 5.0
        if bg.duration < total_duration + bg_skip:
            bg_skip = 0.0
        if bg.duration < total_duration:
            loops_needed = int(total_duration / bg.duration) + 1
            bg = concatenate_videoclips([bg] * loops_needed)

        bg = bg.subclipped(bg_skip, bg_skip + total_duration)
        bg = _crop_to_portrait(bg, render_config.width, render_config.height)

        overlay_clips: list[ImageClip] = []
        audio_clips = []
        current_t = 0.0

        # character overlay (full duration)
        if config.character_image and config.character_image.exists():
            char_img = load_character_image(config.character_image, render_config)
            char_x = render_config.width - char_img.width - 20
            char_y = render_config.height - char_img.height - 20
            char_clip = (
                ImageClip(np.array(char_img))
                .with_duration(total_duration)
                .with_start(0)
                .with_position((char_x, char_y))
            )
            overlay_clips.append(char_clip)

        for i, question in enumerate(questions):
            tts_dur = audio_durations[i]
            think_dur = max(0, question.time_limit - tts_dur)
            reveal_dur = config.reveal_duration
            gap_dur = config.gap_duration

            # question frame overlay
            q_frame = render_question_frame(question, render_config, reveal=False)
            q_clip = (
                ImageClip(np.array(q_frame))
                .with_duration(question.time_limit)
                .with_start(current_t)
                .with_position("center")
            )
            overlay_clips.append(q_clip)

            # countdown bar (capped frame count)
            if think_dur > 0:
                countdown_start = current_t + tts_dur
                n_frames = min(MAX_COUNTDOWN_FRAMES, max(2, int(think_dur * render_config.fps / 3)))
                for frame_i in range(n_frames):
                    progress = frame_i / max(1, n_frames - 1)
                    frame_dur = think_dur / n_frames
                    bar_frame = render_countdown_bar(render_config, progress)
                    bar_clip = (
                        ImageClip(np.array(bar_frame))
                        .with_duration(frame_dur)
                        .with_start(countdown_start + frame_i * frame_dur)
                        .with_position("center")
                    )
                    overlay_clips.append(bar_clip)

            # reveal frame
            reveal_start = current_t + question.time_limit
            is_trivia = isinstance(question, TriviaQuestion)
            reveal_frame = render_question_frame(question, render_config, reveal=is_trivia)
            reveal_clip = (
                ImageClip(np.array(reveal_frame))
                .with_duration(reveal_dur)
                .with_start(reveal_start)
                .with_position("center")
            )
            overlay_clips.append(reveal_clip)

            # audio per question
            tts_audio = AudioFileClip(str(audio_paths[i]))
            tts_audio_clips.append(tts_audio)
            audio_clips.append(tts_audio.with_start(current_t))

            current_t += question.time_limit + reveal_dur + gap_dur

        final = CompositeVideoClip([bg, *overlay_clips])

        if audio_clips:
            mixed_audio = CompositeAudioClip(audio_clips)
            final = final.with_audio(mixed_audio).with_duration(total_duration)

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
        for c in tts_audio_clips:
            c.close()
        bg.close()
        if original_bg is not bg:
            original_bg.close()
