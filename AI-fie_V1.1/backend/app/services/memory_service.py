import json
import os
from collections import deque
from typing import Dict

from app.utils.jsonl_utils import append_jsonl
from app.utils.time_utils import get_iso_timestamp


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
JOURNAL_DIR = os.path.join(DATA_DIR, "journal")
MEMORY_DIR = os.path.join(DATA_DIR, "memory")

RAW_JOURNAL_PATH = os.path.join(JOURNAL_DIR, "raw_journal.jsonl")
PROCESSED_JOURNAL_PATH = os.path.join(MEMORY_DIR, "processed_journal.jsonl")
CURRENT_FOCUS_PATH = os.path.join(MEMORY_DIR, "current-focus.md")
LONG_TERM_MEMORY_PATH = os.path.join(MEMORY_DIR, "long-term-memory.md")
TASK_LIST_PATH = os.path.join(MEMORY_DIR, "task-list.md")

FOUNDER_PROFILE_PATH = os.path.join(MEMORY_DIR, "founder-profile.md")
GOALS_PATH = os.path.join(MEMORY_DIR, "goals.md")
HELP_PREFERENCES_PATH = os.path.join(MEMORY_DIR, "help-preferences.md")


def append_markdown(file_path: str, content: str) -> None:
    """
    Append plain text content to a markdown file.
    Creates folders if needed.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    print(f"[MEMORY] Appending to markdown file: {file_path}")
    print(f"[MEMORY] Content being added:\n{content}")

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(content + "\n")

    print("[MEMORY] Markdown append complete")


def save_processed_result(processed_result: Dict) -> None:
    """
    Save the full processed result into processed_journal.jsonl.
    This keeps a separate record of what the processor decided.
    """
    print("[MEMORY] Saving processed result to processed journal...")

    record = {
        "processed_at": get_iso_timestamp(),
        **processed_result
    }

    append_jsonl(PROCESSED_JOURNAL_PATH, record)
    print("[MEMORY] Processed result saved")


def route_to_memory(processed_result: Dict) -> None:
    """
    Route processed content into the correct memory file
    based on the selected route.
    """
    print("[MEMORY] Routing processed result to memory...")
    print(f"[MEMORY] Incoming processed result: {processed_result}")

    route = processed_result.get("route", "ignore")
    simplified_message = processed_result.get("simplified_message", "")
    category = processed_result.get("category", "unknown")
    relevance_score = processed_result.get("relevance_score", 0)
    strategic_importance = processed_result.get("strategic_importance", 0)
    source = processed_result.get("source", "unknown")
    role = processed_result.get("role", "unknown")
    raw_message = processed_result.get("raw_message", "")

    timestamp = get_iso_timestamp()

    entry = (
        f"## Entry - {timestamp}\n"
        f"- Source: {source}\n"
        f"- Role: {role}\n"
        f"- Category: {category}\n"
        f"- Relevance Score: {relevance_score}\n"
        f"- Strategic Importance: {strategic_importance}\n"
        f"- Raw Message: {raw_message}\n"
        f"- Simplified Message: {simplified_message}\n"
    )

    if route == "current_focus":
        print("[MEMORY] Route matched: current_focus")
        append_markdown(CURRENT_FOCUS_PATH, entry)

    elif route == "long_term_memory":
        print("[MEMORY] Route matched: long_term_memory")
        append_markdown(LONG_TERM_MEMORY_PATH, entry)

    elif route == "task_list":
        print("[MEMORY] Route matched: task_list")
        append_markdown(TASK_LIST_PATH, entry)

    else:
        print("[MEMORY] Route matched: ignore")
        print("[MEMORY] No markdown memory file updated")

    print("[MEMORY] Routing complete")


def process_and_store_memory(processed_result: Dict) -> None:
    """
    Main memory pipeline for processed outputs.

    1. Save full processed result to processed_journal.jsonl
    2. Route the relevant content to the correct markdown memory file
    """
    print("\n[MEMORY] ===== Starting memory storage pipeline =====")
    save_processed_result(processed_result)
    route_to_memory(processed_result)
    print("[MEMORY] ===== Memory storage pipeline complete =====\n")


def load_core_profile_context() -> str:
    """
    Load the core steering context created by onboarding.

    These files guide normal-mode responses:
    - founder-profile.md
    - goals.md
    - current-focus.md
    - help-preferences.md
    """
    print("[MEMORY] Loading core profile context...")

    file_paths = [
        FOUNDER_PROFILE_PATH,
        GOALS_PATH,
        CURRENT_FOCUS_PATH,
        HELP_PREFERENCES_PATH,
    ]

    parts = []

    for path in file_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                content = file.read().strip()
                if content:
                    parts.append(content)
                    print(f"[MEMORY] Loaded context file: {path}")
        else:
            print(f"[MEMORY] Context file not found: {path}")

    combined = "\n\n".join(parts).strip()
    print("[MEMORY] Core profile context load complete")
    return combined


def load_recent_conversation_context(limit: int = 10) -> str:
    """
    Load the most recent user/assistant messages from raw_journal.jsonl.

    limit=10 is roughly:
    - last 5 user messages
    - last 5 assistant replies

    Excludes onboarding and goal_update mode entries so those structured flows
    do not pollute normal conversation continuity.
    """
    print(f"[MEMORY] Loading recent conversation context with limit={limit}...")

    if not os.path.exists(RAW_JOURNAL_PATH):
        print("[MEMORY] raw_journal.jsonl not found")
        return ""

    recent_messages = deque(maxlen=limit)

    with open(RAW_JOURNAL_PATH, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            role = record.get("role", "").strip()
            message = record.get("message", "").strip()
            mode = record.get("mode", "").strip()

            if role not in {"user", "assistant"}:
                continue

            if not message:
                continue

            if mode in {"onboarding", "goal_update"}:
                continue

            recent_messages.append({
                "role": role,
                "message": message
            })

    if not recent_messages:
        print("[MEMORY] No recent conversation context found")
        return ""

    lines = []
    for item in recent_messages:
        label = "User" if item["role"] == "user" else "Assistant"
        lines.append(f"{label}: {item['message']}")

    combined = "\n".join(lines).strip()
    print("[MEMORY] Recent conversation context load complete")
    return combined