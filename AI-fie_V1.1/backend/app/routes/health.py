from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    print("[HEALTH] Health endpoint was called")
    return {
        "status": "ok",
        "message": "AI-fie V1.1 is running"
    }