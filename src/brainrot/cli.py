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
@click.option("--quiz", "quiz_file", required=True, type=click.Path(exists=True), help="Path to quiz JSON file")
@click.option("--background", required=True, type=click.Path(exists=True), help="Path to background video")
@click.option("--character", type=click.Path(exists=True), default=None, help="Path to character overlay PNG")
@click.option("--output", "-o", default="output/quiz.mp4", help="Output file path")
@click.option("--tts", type=click.Choice(["edge", "elevenlabs"]), default="edge", help="TTS provider")
@click.option("--voice", default="en-US-ChristopherNeural", help="Voice name")
@click.option("--dev", is_flag=True, help="Dev mode: render at 540x960 for speed")
def quiz(quiz_file: str, background: str, character: str | None, output: str, tts: str, voice: str, dev: bool):
    """Generate quiz video from JSON file."""
    from .quiz_loader import load_quiz
    from .quiz_pipeline import run_quiz
    from .quiz_config import QuizPipelineConfig

    provider = TTSProvider.ELEVENLABS if tts == "elevenlabs" else TTSProvider.EDGE

    quiz_data = load_quiz(Path(quiz_file))

    config = QuizPipelineConfig(
        quiz_data=quiz_data,
        background_video=Path(background),
        output_path=Path(output),
        character_image=Path(character) if character else None,
        tts_provider=provider,
        tts_voice=voice if provider == TTSProvider.EDGE else "en-US-ChristopherNeural",
        elevenlabs_voice_id=voice if provider == TTSProvider.ELEVENLABS else "",
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        dev_mode=dev,
    )

    click.echo("Generating quiz video...")
    click.echo(f"  Type: {quiz_data.quiz_type.value}")
    click.echo(f"  Questions: {len(quiz_data.questions)}")
    click.echo(f"  TTS: {tts} ({voice})")
    click.echo(f"  Resolution: {'540x960 (dev)' if dev else '1080x1920'}")

    result = run_quiz(config)
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
