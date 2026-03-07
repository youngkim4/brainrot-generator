# Brainrot Generator — Project CLAUDE.md

## Project Overview

**What:** Automated short-form video generator for TikTok/Reels/Shorts. Combines background gameplay footage with TTS narration and word-highlighted captions.

**Goal:** Maximize viewer attention. One word on screen at a time, pop-in animation, no visual clutter competing with the background video.

**Stack:** Python 3.10+, MoviePy 2.x, edge-tts / ElevenLabs, whisper-timestamped, Pillow, yt-dlp, Click

**Architecture:**

```
                    CLI / Pipeline Orchestrator
                              │
        ┌─────────┬───────────┼───────────┬──────────┐
        ▼         ▼           ▼           ▼          ▼
  ┌──────────┐ ┌───────┐ ┌──────────┐ ┌────────┐ ┌──────────┐
  │  Story   │ │  TTS  │ │Timestamp │ │Caption │ │Compositor│
  │  Source  │ │Engine │ │Generator │ │Renderer│ │          │
  └──────────┘ └───────┘ └──────────┘ └────────┘ └──────────┘
       │           │           │           │          │
   text input   edge-tts    whisper-     Pillow     MoviePy 2
   or Reddit   ElevenLabs  timestamped  word-by-   + FFmpeg
   scraping                 DTW-based   word glow   9:16 MP4
```

Each stage is an independent module with a clean interface. Stages are composable — swap TTS providers or caption styles without touching other modules.

## Pinned Dependencies

| Package | Version | Why |
|---------|---------|-----|
| moviepy | >=2.2.1 | v2 API — import from `moviepy`, use `.with_*()` methods, effects are classes |
| edge-tts | >=7.2.7 | Free TTS via Microsoft Edge, no API key |
| elevenlabs | >=2.37.0 | Production TTS, optional dependency |
| whisper-timestamped | latest | DTW-based word timestamps with confidence scores — more accurate than openai-whisper |
| Pillow | >=12.1.1 | Caption frame rendering |
| yt-dlp | >=2026.1.29 | Background video downloading, requires Python 3.10+ |
| click | >=8.3.1 | CLI framework |
| pytest | >=8.0.0 | Testing |
| pytest-asyncio | >=0.24.0 | Async test support |

## Critical Rules

### Pipeline-Specific

- Never process video at full resolution during development — use 540x960 for fast iteration, 1080x1920 for final renders only
- Always validate background video duration >= audio duration before compositing
- TTS audio is the source of truth for video duration — trim background video to match, never stretch audio
- Word timestamps must be validated — reject if total duration drifts >0.5s from audio length
- Captions show one word at a time with pop-in animation — no multi-word groups

### MoviePy v2 (CRITICAL — do not use v1 patterns)

- Import: `from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip` — NOT `from moviepy.editor`
- Clip methods: `.with_duration()`, `.with_position()`, `.with_start()` — NOT `.set_duration()`, `.set_position()`, `.set_start()`
- Effects are classes: `clip.with_effects([vfx.Resize(0.5)])` — NOT `clip.fx(resize, 0.5)`
- Clips must be closed after use to free resources

### Whisper-Timestamped (NOT openai-whisper)

- Use `whisper_timestamped.transcribe()` — NOT `whisper.transcribe()`
- Output includes `words` key per segment with `start`, `end`, `confidence`
- DTW alignment gives accurate word boundaries — essential for caption sync
- Validate confidence scores — flag words below 0.5 confidence

### TTS Providers

- **edge-tts** is the default for all development and testing (free, fast, no API key)
- **ElevenLabs** is production-only — never call ElevenLabs in tests, always mock it
- Provider selection via abstract base class — new providers implement `TTSEngine.synthesize()`

### Video Output

- Resolution: 1080x1920 (9:16 vertical)
- FPS: 30
- Max duration: 60 seconds
- Output format: MP4 (H.264 video + AAC audio)
- Background videos stored in `assets/backgrounds/` — never committed to git (large files)

### Asset Management

- Background videos are downloaded via yt-dlp and stored locally — never bundle in repo
- Use `.gitkeep` in `assets/backgrounds/` and `output/` to preserve directory structure
- Whisper model downloads on first run (~140MB for base) — document in setup instructions

## File Structure

```
src/brainrot/
    __init__.py
    cli.py              # Click CLI entry point
    config.py           # Frozen dataclasses for pipeline config
    pipeline.py         # Orchestrates the full generation pipeline
    tts_engine.py       # TTS providers (edge-tts, ElevenLabs)
    timestamps.py       # whisper-timestamped word-level extraction
    captions.py         # Caption frame rendering with Pillow
    compositor.py       # MoviePy 2 video assembly
    story_source.py     # Manual input and Reddit scraping
assets/
    backgrounds/        # Background video files (gitignored)
output/                 # Generated videos (gitignored)
tests/
    conftest.py         # Shared fixtures (sample audio, mock TTS)
    test_tts_engine.py
    test_timestamps.py
    test_captions.py
    test_compositor.py
    test_pipeline.py    # Integration test with short inputs
```

## Code Patterns

### Config Objects (Frozen Dataclasses)

```python
@dataclass(frozen=True)
class VideoConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
```

### TTS Provider Interface

```python
class TTSEngine(ABC):
    @abstractmethod
    async def synthesize(self, text: str, output_path: Path) -> Path: ...

class EdgeTTSEngine(TTSEngine):
    async def synthesize(self, text: str, output_path: Path) -> Path:
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_path))
        return output_path
```

### MoviePy v2 Compositing Pattern

```python
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip

bg = VideoFileClip("background.mp4").with_duration(audio_duration)
caption_overlay = ImageClip(frame).with_duration(word.end - word.start).with_start(word.start)
final = CompositeVideoClip([bg, caption_overlay])
final.write_videofile("output.mp4", fps=30, codec="libx264", audio_codec="aac")
bg.close()
```

### Word Timestamp Data

```python
@dataclass(frozen=True)
class WordTimestamp:
    word: str
    start: float    # seconds
    end: float      # seconds
    confidence: float  # 0.0-1.0, from whisper-timestamped
```

## Testing

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=brainrot --cov-report=html
```

### Test Strategy

- **Unit tests**: Each module independently — mock TTS calls, mock Whisper, use short fixture audio
- **Integration test**: Full pipeline with a 5-second test input and tiny background clip
- **Fixtures**: `conftest.py` provides sample audio bytes, pre-computed timestamps, small test video

### Example Test

```python
@pytest.mark.asyncio
async def test_edge_tts_generates_audio(tmp_path):
    engine = EdgeTTSEngine(voice="en-US-ChristopherNeural")
    output = tmp_path / "test.mp3"
    result = await engine.synthesize("Hello world", output)
    assert result.exists()
    assert result.stat().st_size > 0
```

## Environment Variables

```bash
# Optional — only for ElevenLabs production renders
ELEVENLABS_API_KEY=

# Optional — for Reddit story scraping
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
```

## Running

```bash
# Generate video with manual story
brainrot generate --story "Your horror story here" --background assets/backgrounds/minecraft.mp4

# Generate with ElevenLabs
brainrot generate --story story.txt --background video.mp4 --tts elevenlabs

# Download a background video from YouTube
brainrot download-bg "https://youtube.com/watch?v=..."
```

## Corrections

<!-- Track project-specific mistakes here so they don't repeat -->
