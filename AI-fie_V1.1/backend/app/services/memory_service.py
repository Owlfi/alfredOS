import os
from typing import Dict
from app.utils.jsonl_utils import append_jsonl
from app.utils.time_utils import get_iso_timestamp

PROCESSED_JOURNAL_PATH = "data/memory/processed_journal.jsonl"
CURRENT_FOCUS_PATH = "data/memory/current-focus.md"
LONG_TERM_MEMORY_PATH = "data/memory/long-term-memory.md"
TASK_LIST_PATH = "data/memory/task-list.md"


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