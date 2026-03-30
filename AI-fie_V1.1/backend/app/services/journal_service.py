from app.utils.time_utils import get_iso_timestamp
from app.utils.jsonl_utils import append_jsonl
from datetime import datetime
import os

from app.utils.jsonl_utils import append_jsonl

RAW_JOURNAL_PATH = "data/journal/raw_journal.jsonl"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_JOURNAL_PATH = os.path.join(BASE_DIR, "data", "journal", "raw_journal.jsonl")

def log_message(source: str, role: str, message: str) -> None:
    print("[JOURNAL] Preparing to log message...")
    print(f"[JOURNAL] Source: {source}")
    print(f"[JOURNAL] Role: {role}")
    print(f"[JOURNAL] Message: {message}")

    record = {
        "timestamp": get_iso_timestamp(),
        "source": source,
        "role": role,
        "message": message,
    }

    append_jsonl(RAW_JOURNAL_PATH, record)
    print("[JOURNAL] Logging complete")

def log_message_with_context(
    source: str,
    role: str,
    message: str,
    mode: str = "",
    module: str = "",
    question_key: str = "",
    message_type: str = ""
) -> None:
    record = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "source": source,
        "role": role,
        "message": message,
    }

    if mode:
        record["mode"] = mode
    if module:
        record["module"] = module
    if question_key:
        record["question_key"] = question_key
    if message_type:
        record["message_type"] = message_type

    append_jsonl(RAW_JOURNAL_PATH, record)