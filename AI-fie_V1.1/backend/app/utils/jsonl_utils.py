import json
import os
from typing import Dict, Any


def append_jsonl(file_path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    print(f"[JSONL] Appending record to: {file_path}")
    print(f"[JSONL] Record contents: {record}")

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("[JSONL] Record successfully written")