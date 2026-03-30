from app.services.llm_service import generate_llm_response


def generate_basic_response(user_message: str) -> str:
    """
    Compatibility wrapper.

    The route still calls generate_basic_response(),
    but the actual work now happens in llm_service.py.
    """
    print("[RESPONSE] Routing response generation through llm_service...")
    print(f"[RESPONSE] User message received: {user_message}")

    reply = generate_llm_response(user_message)

    print(f"[RESPONSE] Final reply returned from llm_service: {reply}")
    return reply