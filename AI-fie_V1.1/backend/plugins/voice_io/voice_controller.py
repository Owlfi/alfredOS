import os
from datetime import datetime

from app.services.chat_orchestrator import handle_chat_message
from plugins.voice_io.piper_adapter import PiperAdapter
from plugins.voice_io.whisper_adapter import WhisperAdapter


class VoiceController:
    def __init__(
        self,
        whisper_adapter: WhisperAdapter,
        piper_adapter: PiperAdapter,
        audio_out_dir: str = "data/audio/out",
    ) -> None:
        self.whisper_adapter = whisper_adapter
        self.piper_adapter = piper_adapter
        self.audio_out_dir = audio_out_dir
        os.makedirs(self.audio_out_dir, exist_ok=True)

    def process_audio(self, input_audio_path: str) -> dict:
        transcript = self.whisper_adapter.transcribe(input_audio_path)

        reply = handle_chat_message(
            source="voice",
            message=transcript,
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_audio_path = os.path.join(self.audio_out_dir, f"reply_{timestamp}.wav")

        self.piper_adapter.synthesize(reply, output_audio_path)

        return {
            "transcript": transcript,
            "reply": reply,
            "response_audio_path": output_audio_path,
        }
