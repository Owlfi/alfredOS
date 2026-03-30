from app.services.journal_service import log_message
from app.services.response_service import generate_basic_response
from app.services.processor_service import process_message
from app.services.memory_service import process_and_store_memory
from app.services.goal_service import handle_goal_mode
from app.services.onboarding_service import handle_onboarding_mode
from app.utils.logger import debug_log


def handle_chat_message(source: str, message: str) -> str:
    debug_log("\n[CHAT] ===== New /chat request received =====")
    debug_log(f"[CHAT] Source: {source}")
    debug_log(f"[CHAT] Message: {message}")

    # Step 1: Log the user's raw message
    debug_log("[CHAT] Step 1: Logging user message")
    log_message(source=source, role="user", message=message)

    # Step 2: Handle onboarding mode first
    debug_log("[CHAT] Step 2: Checking onboarding mode")
    onboarding_result = handle_onboarding_mode(source=source, message=message)

    debug_log(f"[CHAT] Onboarding service returned: {onboarding_result}")

    if onboarding_result["action"] in [
        "entered_onboarding_mode",
        "captured_onboarding_message",
        "exited_onboarding_mode",
        "onboarding_active",
    ]:
        reply = onboarding_result["reply"]

        debug_log("[CHAT] Onboarding mode handled this message directly")
        debug_log("[CHAT] Logging assistant response from onboarding mode")
        log_message(source=source, role="assistant", message=reply)

        debug_log("[CHAT] ===== Request complete =====\n")
        return reply

    # Step 3: Handle goal mode second
    debug_log("[CHAT] Step 3: Checking goal mode")
    goal_result = handle_goal_mode(message)

    debug_log(f"[CHAT] Goal service returned: {goal_result}")

    if goal_result["action"] in [
        "entered_goal_update_mode",
        "captured_goal_update_message",
        "exited_goal_update_mode",
    ]:
        reply = goal_result["reply"]

        debug_log("[CHAT] Goal mode handled this message directly")
        debug_log("[CHAT] Logging assistant response from goal mode")
        log_message(source=source, role="assistant", message=reply)

        debug_log("[CHAT] ===== Request complete =====\n")
        return reply

    # Step 4: Process the user's message normally
    debug_log("[CHAT] Step 4: Processing user message")
    processed_result = process_message(
        source=source,
        role="user",
        raw_message=message
    )

    debug_log(f"[CHAT] Processed result returned to route: {processed_result}")

    # Step 5: Store processed result in memory
    debug_log("[CHAT] Step 5: Storing processed result in memory")
    process_and_store_memory(processed_result)

    # Step 6: Generate normal response
    debug_log("[CHAT] Step 6: Generating assistant response")
    reply = generate_basic_response(message)

    # Step 7: Log assistant response
    debug_log("[CHAT] Step 7: Logging assistant response")
    log_message(source=source, role="assistant", message=reply)

    debug_log("[CHAT] Step 8: Returning response to caller")
    debug_log("[CHAT] ===== Request complete =====\n")

    return reply