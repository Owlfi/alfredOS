from app.services.llm_service import call_ollama
from app.services.memory_service import (
    load_core_profile_context,
    load_recent_conversation_context,
)


def generate_basic_response(user_message: str) -> str:
    """
    Builds a full prompt including:
    - core profile (onboarding)
    - recent conversation
    - current user message
    """

    print("[RESPONSE] Building contextual response...")

    profile_context = load_core_profile_context()
    recent_context = load_recent_conversation_context(limit=10)

    prompt = f"""
You are AI-fie, a personal chief-of-staff style assistant.

Use the user's profile and recent conversation to guide your response.

---------------------
CORE PROFILE
---------------------
{profile_context if profile_context else "No profile context available."}

---------------------
RECENT CONVERSATION
---------------------
{recent_context if recent_context else "No recent conversation available."}

---------------------
CURRENT MESSAGE
---------------------
{user_message}

---------------------
RULES
---------------------
- Stay aligned with the user's goals and current focus
- Respect their help preferences
- Continue the conversation naturally
- Be practical, direct, and useful
- Do not mention internal files unless relevant

Respond directly.
""".strip()

    print("[RESPONSE] Sending enriched prompt to LLM...")

    reply = call_ollama(prompt)

    print(f"[RESPONSE] Final reply: {reply}")
    return reply