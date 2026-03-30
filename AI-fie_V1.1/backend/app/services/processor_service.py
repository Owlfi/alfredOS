from typing import Dict
from app.services.llm_service import process_message_with_llm


def fallback_process_result(source: str, role: str, raw_message: str) -> Dict:
    """
    Safe fallback if structured LLM processing fails.
    """
    print("[PROCESSOR] Using fallback processor result")

    return {
        "source": source,
        "role": role,
        "raw_message": raw_message,
        "simplified_message": raw_message.strip(),
        "category": "general",
        "relevance_score": 50,
        "strategic_importance": 40,
        "route": "ignore"
    }


def validate_processed_result(result: Dict) -> bool:
    """
    Validate the minimum structure we expect back from the LLM.
    """
    print("[PROCESSOR] Validating processed result...")

    required_keys = {
        "simplified_message",
        "category",
        "relevance_score",
        "strategic_importance",
        "route"
    }

    if not isinstance(result, dict):
        print("[PROCESSOR] Validation failed: result is not a dict")
        return False

    missing = required_keys - set(result.keys())
    if missing:
        print(f"[PROCESSOR] Validation failed: missing keys {missing}")
        return False

    print("[PROCESSOR] Validation passed")
    return True


def process_message(source: str, role: str, raw_message: str) -> Dict:
    """
    Full processor pipeline using the LLM for categorisation and scoring.
    """
    print("\n[PROCESSOR] ===== Starting message processing =====")
    print(f"[PROCESSOR] Source: {source}")
    print(f"[PROCESSOR] Role: {role}")
    print(f"[PROCESSOR] Raw message: {raw_message}")

    llm_result = process_message_with_llm(
        source=source,
        role=role,
        raw_message=raw_message
    )

    if not llm_result or not validate_processed_result(llm_result):
        print("[PROCESSOR] LLM result invalid or empty, using fallback")
        final_result = fallback_process_result(source, role, raw_message)
    else:
        final_result = {
            "source": source,
            "role": role,
            "raw_message": raw_message,
            "simplified_message": llm_result["simplified_message"],
            "category": llm_result["category"],
            "relevance_score": llm_result["relevance_score"],
            "strategic_importance": llm_result["strategic_importance"],
            "route": llm_result["route"]
        }

    print("[PROCESSOR] Final processed result:")
    print(final_result)
    print("[PROCESSOR] ===== Processing complete =====\n")

    return final_result