"""CLI entry point."""

import os
from pathlib import Path
from urllib.parse import urlparse

import click

from .config import PipelineConfig, TTSProvider


def _validate_video_url(url: str) -> None:
    """Reject bad URLs."""
    if url.startswith("-"):
        raise click.BadParameter(
            "URL must not start with '-'", param_hint="url"
        )
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise click.BadParameter(
            "URL must be an http:// or https:// URL", param_hint="url"
        )


@click.group()
@click.version_option()
def main():
    """Brainrot video generator."""
    pass


@main.command()
@click.option("--story", required=True, help="Story text or path to a text file")
@click.option("--background", required=True, type=click.Path(exists=True), help="Path to background video")
@click.option("--output", "-o", default="output/video.mp4", help="Output file path")
@click.option("--tts", type=click.Choice(["edge", "elevenlabs"]), default="edge", help="TTS provider")
@click.option("--voice", default="en-US-ChristopherNeural", help="Voice name (edge-tts) or voice ID (ElevenLabs)")
@click.option("--dev", is_flag=True, help="Dev mode: render at 540x960 for speed")
def generate(story: str, background: str, output: str, tts: str, voice: str, dev: bool):
    """Generate video with TTS and captions."""
    from .pipeline import run

    provider = TTSProvider.ELEVENLABS if tts == "elevenlabs" else TTSProvider.EDGE

    config = PipelineConfig(
        story_text=story,
        background_video=Path(background),
        output_path=Path(output),
        tts_provider=provider,
        tts_voice=voice if provider == TTSProvider.EDGE else "en-US-ChristopherNeural",
        elevenlabs_voice_id=voice if provider == TTSProvider.ELEVENLABS else "",
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        dev_mode=dev,
    )

    click.echo("Generating video...")
    click.echo(f"  TTS: {tts} ({voice})")
    click.echo(f"  Background: {background}")
    click.echo(f"  Resolution: {'540x960 (dev)' if dev else '1080x1920'}")

    result = run(config)
    click.echo(f"Done! Output: {result}")


@main.command()
@click.option("--prompt", required=True, help="Question for the intro card, e.g. 'Where would you live?'")
@click.option("--images-dir", required=True, type=click.Path(exists=True), help="Directory of images for slides")
@click.option("--bgm", required=True, type=click.Path(exists=True), help="Background music file")
@click.option("--output", "-o", default="output/slideshow.mp4", help="Output file path")
@click.option("--seconds-per-slide", default=6.0, type=float, help="Duration per slide in seconds")
@click.option("--intro-duration", default=3.0, type=float, help="Intro card duration in seconds")
@click.option("--dev", is_flag=True, help="Dev mode: render at 540x960 for speed")
def slideshow(
    prompt: str,
    images_dir: str,
    bgm: str,
    output: str,
    seconds_per_slide: float,
    intro_duration: float,
    dev: bool,
):
    """Generate slideshow video from images with BGM."""
    from .slideshow_config import SlideshowConfig
    from .slideshow_pipeline import run_slideshow

    config = SlideshowConfig(
        prompt=prompt,
        output_path=Path(output),
        bgm_path=Path(bgm),
        image_dir=Path(images_dir),
        seconds_per_slide=seconds_per_slide,
        intro_duration=intro_duration,
        dev_mode=dev,
    )

    click.echo("Generating slideshow...")
    click.echo(f"  Prompt: {prompt}")
    click.echo(f"  Images: {images_dir}")
    click.echo(f"  BGM: {bgm}")
    click.echo(f"  Resolution: {'540x960 (dev)' if dev else '1080x1920'}")

    result = run_slideshow(config)
    click.echo(f"Done! Output: {result}")


@main.command("slideshow-gen")
@click.option("--prompt", required=True, help="Question prompt, e.g. 'Where would you live?'")
@click.option("--bgm", required=True, type=click.Path(exists=True), help="Background music file")
@click.option("--output", "-o", default="output/slideshow.mp4", help="Output file path")
@click.option("--subjects", default=None, help="Comma-separated subjects (auto-generated if omitted)")
@click.option("--num-images", default=6, type=int, help="Number of images to generate (if auto)")
@click.option("--images-dir", default=None, type=click.Path(), help="Directory to save generated images")
@click.option("--seconds-per-slide", default=6.0, type=float, help="Duration per slide in seconds")
@click.option("--intro-duration", default=3.0, type=float, help="Intro card duration in seconds")
@click.option("--dev", is_flag=True, help="Dev mode: render at 540x960 for speed")
def slideshow_gen(
    prompt: str,
    bgm: str,
    output: str,
    subjects: str | None,
    num_images: int,
    images_dir: str | None,
    seconds_per_slide: float,
    intro_duration: float,
    dev: bool,
):
    """Generate AI slideshow: auto-creates concepts and images from a prompt."""
    from .slideshow_config import SlideshowConfig
    from .slideshow_pipeline import run_slideshow_with_generation

    subject_dicts = None
    if subjects:
        # manual subjects — wrap as dicts with subject key only
        subject_list = [s.strip() for s in subjects.split(",") if s.strip()]
        if len(subject_list) < 2:
            raise click.BadParameter("Need at least 2 subjects", param_hint="--subjects")
        subject_dicts = [{"subject": s, "setting_detail": s} for s in subject_list]
        num_images = len(subject_list)

    config = SlideshowConfig(
        prompt=prompt,
        output_path=Path(output),
        bgm_path=Path(bgm),
        image_dir=Path(images_dir) if images_dir else None,
        num_images=num_images,
        seconds_per_slide=seconds_per_slide,
        intro_duration=intro_duration,
        dev_mode=dev,
    )

    click.echo("Generating slideshow with AI images...")
    click.echo(f"  Prompt: {prompt}")
    if subject_dicts:
        click.echo(f"  Subjects: {', '.join(s['subject'] for s in subject_dicts)}")
    else:
        click.echo(f"  Auto-generating {num_images} concepts...")
    click.echo(f"  BGM: {bgm}")
    click.echo(f"  Resolution: {'540x960 (dev)' if dev else '1080x1920'}")

    result = run_slideshow_with_generation(config, subject_dicts)
    click.echo(f"Done! Output: {result}")


@main.command("download-bg")
@click.argument("url")
@click.option("--output", "-o", default="assets/backgrounds/", help="Output directory")
def download_bg(url: str, output: str):
    """Download bg video from YouTube."""
    import subprocess

    _validate_video_url(url)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "--format", "bestvideo[height<=1920]+bestaudio/best[height<=1920]",
        "--merge-output-format", "mp4",
        "--output", str(output_dir / "%(title)s.%(ext)s"),
        url,
    ]

    click.echo(f"Downloading: {url}")
    subprocess.run(cmd, check=True)
    click.echo(f"Saved to: {output_dir}")
