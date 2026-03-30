from datetime import datetime


def get_iso_timestamp() -> str:
    timestamp = datetime.now().astimezone().isoformat()
    print(f"[TIME] Generated timestamp: {timestamp}")
    return timestamp