"""Slideshow pipeline orchestrator."""

from pathlib import Path

from .image_gen import generate_images, generate_subjects, load_images_from_dir
from .slideshow_compositor import compose_slideshow
from .slideshow_config import SlideshowConfig


def run_slideshow(config: SlideshowConfig) -> Path:
    """Run slideshow pipeline from existing images."""

    if config.image_paths:
        image_paths = list(config.image_paths)
    elif config.image_dir and config.image_dir.exists():
        image_paths = load_images_from_dir(config.image_dir)
    else:
        raise ValueError(
            "Provide --images-dir with existing images, or use "
            "slideshow-gen to generate images with AI"
        )

    if len(image_paths) < 2:
        raise ValueError("Need at least 2 images for a slideshow")

    return compose_slideshow(
        image_paths=image_paths,
        bgm_path=config.bgm_path,
        prompt=config.prompt,
        output_path=config.output_path,
        seconds_per_slide=config.seconds_per_slide,
        intro_duration=config.intro_duration,
        fade_duration=config.fade_duration,
        ken_burns_zoom=config.ken_burns_zoom,
        width=config.render_width,
        height=config.render_height,
        fps=config.fps,
        bgm_volume=config.bgm_volume,
    )


def run_slideshow_with_generation(
    config: SlideshowConfig,
    subjects: list[dict[str, str]] | None = None,
) -> Path:
    """Generate images via Gemini, then compose slideshow.

    If subjects is None, auto-generates concepts from the prompt.
    """
    if subjects is None:
        subjects = generate_subjects(
            prompt=config.prompt,
            count=config.num_images,
            model=config.gemini_model,
        )

    output_dir = config.image_dir or (config.output_path.parent / "slides")
    image_paths = generate_images(
        prompt=config.prompt,
        subjects=subjects,
        output_dir=output_dir,
        model=config.gemini_model,
    )

    return compose_slideshow(
        image_paths=image_paths,
        bgm_path=config.bgm_path,
        prompt=config.prompt,
        output_path=config.output_path,
        seconds_per_slide=config.seconds_per_slide,
        intro_duration=config.intro_duration,
        fade_duration=config.fade_duration,
        ken_burns_zoom=config.ken_burns_zoom,
        width=config.render_width,
        height=config.render_height,
        fps=config.fps,
        bgm_volume=config.bgm_volume,
    )
