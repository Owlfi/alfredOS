from faster_whisper import WhisperModel


class WhisperAdapter:
    def __init__(self, model_size: str = "small", compute_type: str = "int8") -> None:
        self.model_size = model_size
        self.compute_type = compute_type
        self.model = WhisperModel(model_size, compute_type=compute_type)

    def transcribe(self, audio_path: str) -> str:
        segments, _ = self.model.transcribe(audio_path)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()

        if not transcript:
            raise RuntimeError("Whisper returned an empty transcript.")

        return transcript
