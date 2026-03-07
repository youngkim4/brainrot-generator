# brainrot-generator

Automated short-form video generator for TikTok, Reels, and YouTube Shorts. Combines background gameplay footage with TTS narration, word-level captions, and a Reddit-style intro card.

## How it works

1. Feed it a story (text or file)
2. TTS narrates the story (Edge TTS, Amazon Polly, or ElevenLabs)
3. Whisper extracts word-level timestamps
4. MoviePy composites everything into a 9:16 vertical video:
   - Background gameplay (Minecraft parkour, etc.)
   - Reddit dark-mode post card intro with pop-in/pop-out animation + SFX
   - One-word-at-a-time captions with pop-in effect
   - Background music

## Quick start

```bash
# Install
pip install -e ".[all]"

# Download a background video
brainrot download-bg "https://youtube.com/watch?v=..."

# Generate a video
brainrot generate \
  --story "Your horror story here." \
  --background assets/backgrounds/minecraft.mp4 \
  --tts polly \
  --dev
```

## Requirements

- Python 3.10+
- FFmpeg (installed and on PATH)
- Whisper model downloads ~140MB on first run

## CLI commands

### `brainrot generate`

Generate a narrated story video.

```
--story TEXT          Story text or path to a .txt file (required)
--background PATH    Background video file (required)
--output, -o PATH    Output file (default: output/video.mp4)
--tts CHOICE         TTS provider: edge, polly, elevenlabs (default: polly)
--voice TEXT         Voice name or ID (default: Brian)
--dev                Half-resolution (540x960) for fast iteration
```

### `brainrot download-bg`

Download a background video from YouTube via yt-dlp.

```
brainrot download-bg "https://youtube.com/watch?v=..." -o assets/backgrounds/
```

### `brainrot slideshow` *(in development)*

Generate a slideshow video from a directory of images with BGM and Ken Burns effect.

```
--prompt TEXT             Intro card question (required)
--images-dir PATH        Directory of images (required)
--bgm PATH               Background music file (required)
--seconds-per-slide NUM  Duration per slide (default: 6.0)
--intro-duration NUM     Intro card duration (default: 3.0)
--dev                    Half-resolution mode
```

### `brainrot slideshow-gen` *(in development)*

Same as `slideshow`, but auto-generates images using Gemini.

```
--prompt TEXT         Question prompt (required)
--bgm PATH           Background music (required)
--subjects TEXT       Comma-separated subjects, or auto-generated
--num-images NUM      Number of images to generate (default: 6)
```

### `brainrot quiz` *(in development)*

Generate a quiz video (trivia or would-you-rather) from a JSON file.

```
--quiz PATH          Quiz JSON file (required)
--background PATH    Background video (required)
--character PATH     Character overlay PNG (optional)
--tts CHOICE         TTS provider: edge, elevenlabs
--dev                Half-resolution mode
```

Quiz JSON format:

```json
{
  "type": "trivia",
  "questions": [
    {
      "question": "What is the capital of France?",
      "options": ["London", "Paris", "Berlin", "Madrid"],
      "correct": 1,
      "time_limit": 7.0
    }
  ]
}
```

## TTS providers

| Provider | Setup | Notes |
|----------|-------|-------|
| **edge-tts** | None (free) | Microsoft Edge voices, no API key needed |
| **Amazon Polly** | AWS credentials (`~/.aws/credentials` or env vars) | Neural voices, default provider |
| **ElevenLabs** | `ELEVENLABS_API_KEY` env var + `--voice` with voice ID | High quality, paid |

## Project structure

```
src/brainrot/
    cli.py              # Click CLI
    config.py           # Frozen dataclass configs
    pipeline.py         # Orchestrates story -> TTS -> timestamps -> video
    tts_engine.py       # TTS providers (Edge, Polly, ElevenLabs)
    timestamps.py       # whisper-timestamped word-level extraction
    captions.py         # Single-word caption rendering (Pillow)
    compositor.py       # MoviePy 2 video assembly
    reddit_overlay.py   # Reddit dark-mode post card overlay
    story_source.py     # Story text/file loader
assets/
    backgrounds/        # Background videos (gitignored)
    bgm/                # Background music
    sfx/                # Sound effects (pop in/out)
output/                 # Generated videos (gitignored)
tests/
```

## Video output

- Resolution: 1080x1920 (9:16 portrait), or 540x960 in `--dev` mode
- FPS: 30
- Max duration: 60 seconds
- Format: MP4 (H.264 + AAC)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=brainrot --cov-report=html

# Fast iteration: always use --dev flag during development
brainrot generate --story "Test." --background bg.mp4 --dev
```

## Dependencies

| Package | Purpose |
|---------|---------|
| moviepy >=2.2.1 | Video compositing (v2 API) |
| edge-tts >=7.2.7 | Free TTS |
| whisper-timestamped | Word-level timestamps via DTW |
| Pillow | Caption and overlay rendering |
| yt-dlp | Background video downloading |
| click | CLI framework |
| boto3 | Amazon Polly TTS |
| elevenlabs | ElevenLabs TTS (optional) |
