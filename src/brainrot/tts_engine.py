"""TTS engine."""

from abc import ABC, abstractmethod
from pathlib import Path

from .config import PipelineConfig, TTSProvider


class TTSEngine(ABC):
    @abstractmethod
    async def synthesize(self, text: str, output_path: Path) -> Path:
        """Text to audio file."""
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
    def __init__(self, api_key: str, voice_id: str, model_id: str = "eleven_multilingual_v2"):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id

    async def synthesize(self, text: str, output_path: Path) -> Path:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=self.api_key)
        audio = client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id=self.model_id,
        )

        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        return output_path


class PollyTTSEngine(TTSEngine):
    def __init__(self, voice: str = "Brian", region: str = "us-east-1"):
        self.voice = voice
        self.region = region

    async def synthesize(self, text: str, output_path: Path) -> Path:
        import boto3

        client = boto3.client("polly", region_name=self.region)

        # Polly has a 3000 char limit per request, split if needed
        chunks = self._split_text(text, max_chars=2900)
        audio_bytes = b""
        for chunk in chunks:
            resp = client.synthesize_speech(
                Text=chunk,
                VoiceId=self.voice,
                Engine="neural",
                OutputFormat="mp3",
            )
            audio_bytes += resp["AudioStream"].read()

        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        return output_path

    @staticmethod
    def _split_text(text: str, max_chars: int = 2900) -> list[str]:
        """Split text on sentence boundaries."""
        if len(text) <= max_chars:
            return [text]
        chunks = []
        current = ""
        for sentence in text.replace(". ", ".|").split("|"):
            if len(current) + len(sentence) > max_chars:
                if current:
                    chunks.append(current)
                current = sentence
            else:
                current += sentence
        if current:
            chunks.append(current)
        return chunks


def create_tts_engine(config: PipelineConfig) -> TTSEngine:
    if config.tts_provider == TTSProvider.ELEVENLABS:
        if not config.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key required. Set ELEVENLABS_API_KEY env var.")
        if not config.elevenlabs_voice_id:
            raise ValueError("ElevenLabs voice ID required. Use --voice-id flag.")
        return ElevenLabsTTSEngine(
            config.elevenlabs_api_key,
            config.elevenlabs_voice_id,
            config.elevenlabs_model_id,
        )
    if config.tts_provider == TTSProvider.POLLY:
        return PollyTTSEngine(config.tts_voice, config.polly_region)
    return EdgeTTSEngine(config.tts_voice)
