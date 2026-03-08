"""Quiz video compositing with MoviePy 2."""

import shutil
import wave
from pathlib import Path

import numpy as np
from moviepy import (
    AudioClip,
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
from .quiz_sfx import generate_all_sfx


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Read WAV into numpy samples array and sample rate. Cached by caller."""
    with wave.open(str(path), "rb") as wf:
        n_frames = wf.getnframes()
        sample_rate = wf.getframerate()
        raw = wf.readframes(n_frames)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32767.0
        samples = samples.reshape(-1, 1)  # mono -> (n, 1)
    return samples, sample_rate


def _make_sfx_clip(samples: np.ndarray, sample_rate: int) -> AudioClip:
    """Build an AudioClip from pre-loaded samples.

    MoviePy's CompositeAudioClip calls get_frame on ALL clips for ALL time
    values, then multiplies by 0 for out-of-range times. AudioFileClip's reader
    raises IOError for out-of-range access. Using a safe frame function that
    returns silence for out-of-range times avoids this.
    """
    duration = len(samples) / sample_rate

    def make_frame(t):
        t_arr = np.atleast_1d(t)
        result = np.zeros((len(t_arr), 1))
        indices = (t_arr * sample_rate).astype(int)
        valid = (indices >= 0) & (indices < len(samples))
        result[valid] = samples[indices[valid]]
        return result

    return AudioClip(make_frame, duration=duration, fps=sample_rate)


MAX_COUNTDOWN_FRAMES = 30
SFX_VOLUME = 0.6
TICK_VOLUME = 0.35
URGENT_THRESHOLD = 0.7  # fraction of countdown elapsed before urgent ticks


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


def _add_sfx_clips(
    audio_clips: list,
    sfx_audio_clips: list[AudioClip],
    sfx_samples: dict[str, tuple[np.ndarray, int]],
    current_t: float,
    tts_dur: float,
    think_dur: float,
    reveal_start: float,
) -> None:
    """Add SFX audio clips for one question to the audio timeline."""
    # question intro whoosh
    intro_clip = _make_sfx_clip(*sfx_samples["question_intro"])
    sfx_audio_clips.append(intro_clip)
    audio_clips.append(
        intro_clip.with_start(current_t).with_volume_scaled(SFX_VOLUME)
    )

    if think_dur <= 0:
        return

    countdown_start = current_t + tts_dur

    # countdown start tone
    cd_start_clip = _make_sfx_clip(*sfx_samples["countdown_start"])
    sfx_audio_clips.append(cd_start_clip)
    audio_clips.append(
        cd_start_clip.with_start(countdown_start).with_volume_scaled(SFX_VOLUME)
    )

    # ticking during countdown — one tick per second
    tick_interval = 1.0
    elapsed = 0.0
    while elapsed < think_dur - 0.1:
        progress = elapsed / think_dur
        is_urgent = progress >= URGENT_THRESHOLD

        sfx_key = "tick_urgent" if is_urgent else "tick"
        volume = TICK_VOLUME * (1.3 if is_urgent else 1.0)

        tick_clip = _make_sfx_clip(*sfx_samples[sfx_key])
        sfx_audio_clips.append(tick_clip)
        audio_clips.append(
            tick_clip.with_start(countdown_start + elapsed)
            .with_volume_scaled(volume)
        )

        # speed up ticks in urgent phase
        tick_interval = 0.5 if is_urgent else 1.0
        elapsed += tick_interval

    # reveal chime
    reveal_clip = _make_sfx_clip(*sfx_samples["reveal_correct"])
    sfx_audio_clips.append(reveal_clip)
    audio_clips.append(
        reveal_clip.with_start(reveal_start).with_volume_scaled(SFX_VOLUME)
    )


def compose_quiz_video(
    background_path: Path,
    audio_paths: list[Path],
    audio_durations: list[float],
    config: QuizPipelineConfig,
) -> Path:
    """Assemble quiz video: bg + question overlays + character + audio + SFX."""
    render_config = _get_render_config(config)
    questions = config.quiz_data.questions

    total_duration = _compute_total_duration(questions, config)

    # generate SFX WAVs, then pre-load samples into memory
    sfx_paths = generate_all_sfx()
    sfx_dir = sfx_paths["tick"].parent
    sfx_samples = {name: _read_wav(path) for name, path in sfx_paths.items()}

    bg = VideoFileClip(str(background_path))
    original_bg = bg
    final = None
    tts_audio_clips: list[AudioFileClip] = []
    sfx_audio_clips: list[AudioClip] = []
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
            n_questions = len(questions)
            q_frame = render_question_frame(
                question, render_config, reveal=False,
                question_index=i, total_questions=n_questions,
            )
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
            reveal_frame = render_question_frame(
                question, render_config, reveal=is_trivia,
                question_index=i, total_questions=n_questions,
            )
            reveal_clip = (
                ImageClip(np.array(reveal_frame))
                .with_duration(reveal_dur)
                .with_start(reveal_start)
                .with_position("center")
            )
            overlay_clips.append(reveal_clip)

            # TTS audio
            tts_audio = AudioFileClip(str(audio_paths[i]))
            tts_audio_clips.append(tts_audio)
            audio_clips.append(tts_audio.with_start(current_t))

            # SFX audio
            _add_sfx_clips(
                audio_clips, sfx_audio_clips, sfx_samples,
                current_t=current_t,
                tts_dur=tts_dur,
                think_dur=think_dur,
                reveal_start=reveal_start,
            )

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
        for c in sfx_audio_clips:
            c.close()
        bg.close()
        if original_bg is not bg:
            original_bg.close()
        # clean up temp SFX files
        shutil.rmtree(sfx_dir, ignore_errors=True)
