"""TTS engine with pluggable providers."""

from abc import ABC, abstractmethod
from pathlib import Path

from .config import PipelineConfig, TTSProvider


class TTSEngine(ABC):
    @abstractmethod
    async def synthesize(self, text: str, output_path: Path) -> Path:
        """Generate audio file from text. Returns path to audio file."""
        ...


class EdgeTTSEngine(TTSEngine):
    def __init__(self, voice: str = "en-US-ChristopherNeural"):
        self.voice = voice

    async def synthesize(self, text: str, output_path: Path) -> Path:
        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_path))
        return output_path


class ElevenLabsTTSEngine(TTSEngine):
    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id

    async def synthesize(self, text: str, output_path: Path) -> Path:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=self.api_key)
        audio = client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
        )

        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        return output_path


def create_tts_engine(config: PipelineConfig) -> TTSEngine:
    if config.tts_provider == TTSProvider.ELEVENLABS:
        if not config.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key required. Set ELEVENLABS_API_KEY env var.")
        if not config.elevenlabs_voice_id:
            raise ValueError("ElevenLabs voice ID required. Use --voice-id flag.")
        return ElevenLabsTTSEngine(config.elevenlabs_api_key, config.elevenlabs_voice_id)
    return EdgeTTSEngine(config.tts_voice)
