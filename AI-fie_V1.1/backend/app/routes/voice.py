import os
import shutil
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.journal_models import VoiceResponse
from plugins.voice_io.piper_adapter import PiperAdapter
from plugins.voice_io.voice_controller import VoiceController
from plugins.voice_io.whisper_adapter import WhisperAdapter

router = APIRouter()

AUDIO_IN_DIR = "data/audio/in"
AUDIO_OUT_DIR = "data/audio/out"
PIPER_EXE = os.getenv("PIPER_EXE", r"C:\piper\piper.exe")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", r"C:\piper\models\voice.onnx")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

whisper_adapter = WhisperAdapter(
    model_size=WHISPER_MODEL_SIZE,
    compute_type=WHISPER_COMPUTE_TYPE,
)

piper_adapter = PiperAdapter(
    piper_exe=PIPER_EXE,
    model_path=PIPER_MODEL_PATH,
)

voice_controller = VoiceController(
    whisper_adapter=whisper_adapter,
    piper_adapter=piper_adapter,
    audio_out_dir=AUDIO_OUT_DIR,
)


@router.post("/voice/chat", response_model=VoiceResponse)
async def voice_chat(audio: UploadFile = File(...)):
    os.makedirs(AUDIO_IN_DIR, exist_ok=True)

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file must include a filename.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = os.path.basename(audio.filename)
    input_audio_path = os.path.join(AUDIO_IN_DIR, f"input_{timestamp}_{safe_name}")

    try:
        with open(input_audio_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        result = voice_controller.process_audio(input_audio_path)

        return VoiceResponse(
            transcript=result["transcript"],
            reply=result["reply"],
            response_audio_path=result["response_audio_path"],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
