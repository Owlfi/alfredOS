import json
import os
from collections import deque
from fastapi import APIRouter

from app.services.llm_service import check_ollama_health

router = APIRouter()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
JOURNAL_DIR = os.path.join(DATA_DIR, "journal")
MEMORY_DIR = os.path.join(DATA_DIR, "memory")
LOG_DIR = os.path.join(DATA_DIR, "logs")

RAW_JOURNAL_PATH = os.path.join(JOURNAL_DIR, "raw_journal.jsonl")
PROCESSED_JOURNAL_PATH = os.path.join(MEMORY_DIR, "processed_journal.jsonl")
CURRENT_FOCUS_PATH = os.path.join(MEMORY_DIR, "current-focus.md")
LONG_TERM_MEMORY_PATH = os.path.join(MEMORY_DIR, "long-term-memory.md")
TASK_LIST_PATH = os.path.join(MEMORY_DIR, "task-list.md")
SYSTEM_MODE_PATH = os.path.join(MEMORY_DIR, "system_mode.json")
GOAL_SESSION_PATH = os.path.join(MEMORY_DIR, "goal_update_session.json")
DEBUG_LOG_PATH = os.path.join(LOG_DIR, "debug.log")


def safe_read_json(file_path: str, default_data):
    if not os.path.exists(file_path):
        return default_data

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print(f"[DEBUG ROUTE] Failed to read JSON file {file_path}: {error}")
        return default_data


def safe_read_jsonl_last(file_path: str, default_data=None):
    if default_data is None:
        default_data = {}

    if not os.path.exists(file_path):
        return default_data

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if not lines:
            return default_data

        last_line = lines[-1].strip()
        if not last_line:
            return default_data

        return json.loads(last_line)
    except Exception as error:
        print(f"[DEBUG ROUTE] Failed to read last JSONL line from {file_path}: {error}")
        return default_data


def safe_read_jsonl_last_n(file_path: str, n: int = 20):
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            last_lines = deque(file, maxlen=n)

        results = []
        for line in last_lines:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        return results
    except Exception as error:
        print(f"[DEBUG ROUTE] Failed to read JSONL history from {file_path}: {error}")
        return []


def safe_read_last_logs(file_path: str, n: int = 100):
    if not os.path.exists(file_path):
        return ["[DEBUG] No log file found yet."]

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = deque(file, maxlen=n)

        return [line.rstrip("\n") for line in lines if line.strip()]
    except Exception as error:
        return [f"[DEBUG] Failed to read logs: {error}"]


@router.get("/debug/state")
def get_debug_state():
    system_mode = safe_read_json(SYSTEM_MODE_PATH, {"mode": "normal"})
    goal_session = safe_read_json(GOAL_SESSION_PATH, {"active": False, "messages": []})
    ollama_ok = check_ollama_health()

    return {
        "system": {
            "appName": "AI-fie V1.1",
            "mode": system_mode.get("mode", "normal"),
            "llmStatus": "connected" if ollama_ok else "offline",
            "model": "llama3.1:8b",
            "lastUpdated": __import__("datetime").datetime.now().astimezone().isoformat(),
        },
        "memory": {
            "rawJournalPath": RAW_JOURNAL_PATH,
            "processedJournalPath": PROCESSED_JOURNAL_PATH,
            "currentFocusPath": CURRENT_FOCUS_PATH,
            "longTermMemoryPath": LONG_TERM_MEMORY_PATH,
            "taskListPath": TASK_LIST_PATH,
            "systemModePath": SYSTEM_MODE_PATH,
            "goalSessionPath": GOAL_SESSION_PATH,
        },
        "goalMode": {
            "active": goal_session.get("active", False),
            "capturedMessages": goal_session.get("messages", []),
        },
    }


@router.get("/debug/latest")
def get_debug_latest():
    raw_history = safe_read_jsonl_last_n(RAW_JOURNAL_PATH, n=10)
    processed_latest = safe_read_jsonl_last(PROCESSED_JOURNAL_PATH, default_data={})

    latest_user = {}
    latest_assistant = {}

    for entry in reversed(raw_history):
        if not latest_assistant and entry.get("role") == "assistant":
            latest_assistant = entry
        elif not latest_user and entry.get("role") == "user":
            latest_user = entry

        if latest_user and latest_assistant:
            break

    return {
        "latestExchange": {
            "source": latest_user.get("source", "unknown"),
            "userMessage": latest_user.get("message", "No user message found."),
            "assistantReply": latest_assistant.get("message", "No assistant reply found."),
            "timestamp": latest_user.get("timestamp", "unknown"),
        },
        "processor": {
            "rawMessage": processed_latest.get("raw_message", "No processed message found."),
            "simplifiedMessage": processed_latest.get("simplified_message", "No simplified message found."),
            "category": processed_latest.get("category", "general"),
            "relevanceScore": processed_latest.get("relevance_score", 0),
            "strategicImportance": processed_latest.get("strategic_importance", 0),
            "route": processed_latest.get("route", "ignore"),
        },
    }


@router.get("/debug/logs")
def get_debug_logs():
    logs = safe_read_last_logs(DEBUG_LOG_PATH, n=200)
    return {"logs": logs}