"""CLI entry point using Click."""

import os
from pathlib import Path

import click

from .config import PipelineConfig, TTSProvider


@click.group()
@click.version_option()
def main():
    """Brainrot Generator - Automated short-form video generation."""
    pass


@main.command()
@click.option("--story", required=True, help="Story text or path to a text file")
@click.option("--background", required=True, type=click.Path(exists=True), help="Path to background video")
@click.option("--output", "-o", default="output/video.mp4", help="Output file path")
@click.option("--tts", type=click.Choice(["edge", "elevenlabs"]), default="edge", help="TTS provider")
@click.option("--voice", default="en-US-ChristopherNeural", help="Voice name (edge-tts) or voice ID (ElevenLabs)")
@click.option("--dev", is_flag=True, help="Dev mode: render at 540x960 for speed")
def generate(story: str, background: str, output: str, tts: str, voice: str, dev: bool):
    """Generate a short-form video with TTS narration and captions."""
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

    click.echo(f"Generating video...")
    click.echo(f"  TTS: {tts} ({voice})")
    click.echo(f"  Background: {background}")
    click.echo(f"  Resolution: {'540x960 (dev)' if dev else '1080x1920'}")

    result = run(config)
    click.echo(f"Done! Output: {result}")


@main.command("download-bg")
@click.argument("url")
@click.option("--output", "-o", default="assets/backgrounds/", help="Output directory")
def download_bg(url: str, output: str):
    """Download a background video from YouTube."""
    import subprocess

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
