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
@click.option("--tts", type=click.Choice(["edge", "elevenlabs", "polly", "cartesia"]), default="polly", help="TTS provider")
@click.option("--voice", default="Brian", help="Voice name (edge-tts/polly) or voice ID (ElevenLabs)")
@click.option("--dev", is_flag=True, help="Dev mode: render at 540x960 for speed")
def generate(story: str, background: str, output: str, tts: str, voice: str, dev: bool):
    """Generate video with TTS and captions."""
    from .pipeline import run

    _provider_map = {
        "edge": TTSProvider.EDGE,
        "elevenlabs": TTSProvider.ELEVENLABS,
        "polly": TTSProvider.POLLY,
        "cartesia": TTSProvider.CARTESIA,
    }
    provider = _provider_map[tts]

    config = PipelineConfig(
        story_text=story,
        background_video=Path(background),
        output_path=Path(output),
        tts_provider=provider,
        tts_voice=voice if provider not in (TTSProvider.ELEVENLABS, TTSProvider.CARTESIA) else "Brian",
        elevenlabs_voice_id=voice if provider == TTSProvider.ELEVENLABS else "",
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        cartesia_api_key=os.environ.get("CARTESIA_API_KEY", ""),
        cartesia_voice_id=voice if provider == TTSProvider.CARTESIA else "a0e99841-438c-4a64-b679-ae501e7d6091",
        dev_mode=dev,
    )

    click.echo("Generating video...")
    click.echo(f"  TTS: {tts} ({voice})")
    click.echo(f"  Background: {background}")
    click.echo(f"  Resolution: {'540x960 (dev)' if dev else '1080x1920'}")

    result = run(config)
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
        "--restrict-filenames",
        "--output", str(output_dir / "%(title)s.%(ext)s"),
        url,
    ]

    click.echo(f"Downloading: {url}")
    subprocess.run(cmd, check=True)
    click.echo(f"Saved to: {output_dir}")
