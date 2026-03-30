import json
import os
from datetime import datetime
from typing import Any, Dict

from app.utils.logger import debug_log


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MEMORY_DIR = os.path.join(BASE_DIR, "data", "memory")

SYSTEM_MODE_PATH = os.path.join(MEMORY_DIR, "system_mode.json")
GOAL_UPDATE_SESSION_PATH = os.path.join(MEMORY_DIR, "goal_update_session.json")
CURRENT_FOCUS_PATH = os.path.join(MEMORY_DIR, "current-focus.md")


VALID_MODES = {"normal", "goal_update", "onboarding"}


def get_system_mode() -> str:
    """
    Returns the current system mode.
    Defaults to 'normal' if the file is missing or invalid.
    """
    try:
        if not os.path.exists(SYSTEM_MODE_PATH):
            debug_log("[GOAL] system_mode.json missing, defaulting to normal")
            return "normal"

        with open(SYSTEM_MODE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        mode = data.get("mode", "normal")

        if mode not in VALID_MODES:
            debug_log(f"[GOAL] Invalid mode '{mode}' found, defaulting to normal")
            return "normal"

        return mode

    except Exception as error:
        debug_log(f"[GOAL] Error reading system mode: {error}")
        return "normal"


def set_system_mode(mode: str) -> None:
    """
    Sets the current system mode.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid system mode: {mode}")

    os.makedirs(MEMORY_DIR, exist_ok=True)

    payload = {
        "mode": mode,
        "updated_at": datetime.now().astimezone().isoformat()
    }

    with open(SYSTEM_MODE_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    debug_log(f"[GOAL] System mode set to: {mode}")


def handle_goal_mode(message: str) -> Dict[str, Any]:
    """
    Handles goal update mode and onboarding-aware mode checks.

    Returns a dict in the form:
    {
        "mode": "<current_mode>",
        "action": "<action_name>",
        "reply": "<assistant_reply>"
    }

    Expected actions:
    - no_action
    - entered_goal_update_mode
    - captured_goal_update_message
    - exited_goal_update_mode
    - onboarding_active
    """
    current_mode = get_system_mode()
    cleaned_message = message.strip()

    debug_log(f"[GOAL] handle_goal_mode called with mode={current_mode}, message={cleaned_message}")

    # If onboarding is active, do not let goal service interfere.
    if current_mode == "onboarding":
        return {
            "mode": "onboarding",
            "action": "onboarding_active",
            "reply": ""
        }

    # Enter goal update mode
    if current_mode == "normal" and _is_goal_update_trigger(cleaned_message):
        debug_log("[GOAL] Entering goal update mode")
        _create_goal_update_session()
        set_system_mode("goal_update")

        return {
            "mode": "goal_update",
            "action": "entered_goal_update_mode",
            "reply": (
                "Goal update mode is now active.\n\n"
                "Tell me what has changed, what your top goals are now, what matters most in the next 30 to 90 days, "
                "what should be deprioritised, what constraints I need to respect, how I should help you differently, "
                "and what the single most important next move is.\n\n"
                "When you're done, type 'finish goal update'."
            )
        }

    # Handle goal update mode
    if current_mode == "goal_update":
        if cleaned_message.lower() == "finish goal update":
            debug_log("[GOAL] Finishing goal update mode")
            session = _load_goal_update_session()

            combined_text = "\n".join(session.get("messages", [])).strip()

            if combined_text:
                _write_current_focus_from_goal_update(combined_text)

            set_system_mode("normal")
            _delete_goal_update_session()

            return {
                "mode": "normal",
                "action": "exited_goal_update_mode",
                "reply": "Goal update mode complete. Your updated focus has been saved."
            }

        debug_log("[GOAL] Capturing goal update message")
        _append_goal_update_message(cleaned_message)

        return {
            "mode": "goal_update",
            "action": "captured_goal_update_message",
            "reply": (
                "Captured. Keep going with any updates to your goals, priorities, constraints, or direction. "
                "When you're finished, type 'finish goal update'."
            )
        }

    return {
        "mode": current_mode,
        "action": "no_action",
        "reply": ""
    }


def _is_goal_update_trigger(message: str) -> bool:
    lowered = message.strip().lower()

    trigger_phrases = {
        "i am updating my goals",
        "i'm updating my goals",
        "update my goals",
        "goal update",
        "start goal update",
        "begin goal update",
    }

    return lowered in trigger_phrases


def _create_goal_update_session() -> None:
    """
    Creates a fresh goal update session file.
    """
    os.makedirs(MEMORY_DIR, exist_ok=True)

    payload = {
        "mode": "goal_update",
        "created_at": datetime.now().astimezone().isoformat(),
        "updated_at": datetime.now().astimezone().isoformat(),
        "messages": []
    }

    with open(GOAL_UPDATE_SESSION_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    debug_log("[GOAL] Created goal_update_session.json")


def _load_goal_update_session() -> Dict[str, Any]:
    """
    Loads the current goal update session.
    Returns a default empty session if missing.
    """
    if not os.path.exists(GOAL_UPDATE_SESSION_PATH):
        debug_log("[GOAL] goal_update_session.json missing, creating fallback structure")
        return {
            "mode": "goal_update",
            "created_at": datetime.now().astimezone().isoformat(),
            "updated_at": datetime.now().astimezone().isoformat(),
            "messages": []
        }

    try:
        with open(GOAL_UPDATE_SESSION_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        debug_log(f"[GOAL] Error loading goal update session: {error}")
        return {
            "mode": "goal_update",
            "created_at": datetime.now().astimezone().isoformat(),
            "updated_at": datetime.now().astimezone().isoformat(),
            "messages": []
        }


def _save_goal_update_session(session: Dict[str, Any]) -> None:
    """
    Saves the goal update session file.
    """
    session["updated_at"] = datetime.now().astimezone().isoformat()
    os.makedirs(MEMORY_DIR, exist_ok=True)

    with open(GOAL_UPDATE_SESSION_PATH, "w", encoding="utf-8") as file:
        json.dump(session, file, indent=2)

    debug_log("[GOAL] Saved goal_update_session.json")


def _append_goal_update_message(message: str) -> None:
    """
    Appends a message to the goal update session.
    """
    session = _load_goal_update_session()
    session.setdefault("messages", []).append(message)
    _save_goal_update_session(session)

    debug_log(f"[GOAL] Appended goal update message: {message}")


def _delete_goal_update_session() -> None:
    """
    Removes the goal update session file if it exists.
    """
    if os.path.exists(GOAL_UPDATE_SESSION_PATH):
        os.remove(GOAL_UPDATE_SESSION_PATH)
        debug_log("[GOAL] Deleted goal_update_session.json")


def _write_current_focus_from_goal_update(content: str) -> None:
    """
    Writes a very simple current-focus.md update based on captured goal update text.
    This keeps the behaviour lightweight and avoids overreaching.
    """
    os.makedirs(MEMORY_DIR, exist_ok=True)

    markdown = f"""# Current Focus

## Goal Update Notes
{content}
""".strip() + "\n"

    with open(CURRENT_FOCUS_PATH, "w", encoding="utf-8") as file:
        file.write(markdown)

    debug_log("[GOAL] Updated current-focus.md from goal update session")