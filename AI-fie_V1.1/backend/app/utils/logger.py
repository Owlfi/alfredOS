import os
from datetime import datetime

DEBUG_LOG_PATH = "data/logs/debug.log"


def debug_log(message: str) -> None:
    os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)

    timestamp = datetime.now().astimezone().isoformat()
    line = f"{timestamp} {message}"

    print(line)

    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as file:
        file.write(line + "\n")