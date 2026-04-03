from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes.chat import router as chat_router
from app.routes.debug import router as debug_router
from app.routes.health import router as health_router
from app.routes.voice import router as voice_router

print("[BOOT] Starting AI-fie V1.1 app...")

app = FastAPI(title="AI-fie V1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    print("[ROOT] Root endpoint was called")
    return {
        "message": "AI-fie V1.1 is running",
        "check_health": "/health",
        "docs": "/docs",
        "debug_state": "/debug/state",
        "debug_latest": "/debug/latest",
        "debug_logs": "/debug/logs",
        "voice_chat": "/voice/chat",
    }


app.include_router(health_router)
app.include_router(chat_router)
app.include_router(debug_router)
app.include_router(voice_router)

app.mount("/audio", StaticFiles(directory="data/audio/out"), name="audio")
app.mount("/static", StaticFiles(directory="static"), name="static")

print("[BOOT] Routes loaded: /, /health, /chat, /voice/chat, /debug/state, /debug/latest, /debug/logs")
