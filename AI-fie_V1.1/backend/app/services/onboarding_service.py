import json
import os
from datetime import datetime
from typing import List

from app.services.goal_service import get_system_mode, set_system_mode
from app.services.journal_service import log_message_with_context
from app.services.llm_service import call_ollama
from app.utils.logger import debug_log


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MEMORY_DIR = os.path.join(BASE_DIR, "data", "memory")
ONBOARDING_SESSION_PATH = os.path.join(MEMORY_DIR, "onboarding_session.json")

print("ONBOARDING SERVICE LOADED")


def handle_onboarding_mode(source: str, message: str) -> dict:
    """
    Main onboarding entry point for chat_orchestrator.

    Returns:
    {
        "action": str,
        "reply": str
    }
    """
    debug_log("[ONBOARDING] FUNCTION HIT")
    lowered = message.strip().lower()

    if lowered == "enter onboarding mode":
        debug_log("[ONBOARDING] Force entering onboarding mode")
        session = _create_onboarding_session()
        first_question = _generate_conversational_next_question(session)
        _append_conversation_turn(session, "assistant", first_question)
        _save_session(session)
        set_system_mode("onboarding")

        return {
            "action": "entered_onboarding_mode",
            "reply": first_question,
        }

    current_mode = get_system_mode()
    debug_log(f"[ONBOARDING] Current system mode: {current_mode}")

    if current_mode != "onboarding" and _is_onboarding_trigger(message):
        debug_log("[ONBOARDING] Entering onboarding mode")
        session = _create_onboarding_session()
        first_question = _generate_conversational_next_question(session)
        _append_conversation_turn(session, "assistant", first_question)
        _save_session(session)
        set_system_mode("onboarding")

        return {
            "action": "entered_onboarding_mode",
            "reply": first_question,
        }

    if current_mode == "onboarding":
        debug_log("[ONBOARDING] Onboarding mode is active")

        if not os.path.exists(ONBOARDING_SESSION_PATH):
            debug_log("[ONBOARDING] No session found, creating a new onboarding session")
            session = _create_onboarding_session()
            first_question = _generate_conversational_next_question(session)
            _append_conversation_turn(session, "assistant", first_question)
            _save_session(session)

            return {
                "action": "entered_onboarding_mode",
                "reply": first_question,
            }

        session = _load_session()

        if session.get("awaiting_confirmation", False):
            if lowered == "confirm":
                debug_log("[ONBOARDING] Final confirmation received")
                _write_onboarding_files(session)
                set_system_mode("normal")
                _delete_session()

                return {
                    "action": "exited_onboarding_mode",
                    "reply": "Onboarding complete. Your project onboarding files have been saved.",
                }

            debug_log("[ONBOARDING] Revising final summary based on feedback")
            _append_conversation_turn(session, "user", message)

            session["final_summary"] = _revise_summary(
                current_summary=session.get("final_summary", ""),
                correction_feedback=message,
            )

            reply = (
                f"{session['final_summary']}\n\n"
                "Reply with 'confirm' to save it, or tell me what still needs changing."
            )
            _append_conversation_turn(session, "assistant", reply)
            _save_session(session)

            return {
                "action": "captured_onboarding_message",
                "reply": reply,
            }

        result = _process_onboarding_message(session, source, message)
        _save_session(session)
        return result

    return {
        "action": "no_action",
        "reply": "",
    }


def _is_onboarding_trigger(message: str) -> bool:
    trigger_phrases = [
        "start onboarding",
        "begin onboarding",
        "i want to do onboarding",
        "let's do onboarding",
        "setup my project",
        "set up my project",
        "project onboarding",
        "start project onboarding",
    ]
    lowered = message.strip().lower()
    return lowered in trigger_phrases


def _create_onboarding_session() -> dict:
    now = datetime.now().astimezone().isoformat()

    return {
        "session_id": f"onboarding_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "mode": "onboarding",
        "status": "in_progress",
        "awaiting_confirmation": False,
        "final_summary": "",
        "created_at": now,
        "updated_at": now,
        "conversation_history": [],
        "working_summary": "",
        "key_points": [],
        "missing_areas": [],
        "resolved_areas": [],
        "out_of_scope_areas": [],
        "readiness": {
            "is_ready": False,
            "confidence": "low",
            "reason": "",
        },
        "readiness_streak": 0,
        "structured_project": {
            "project_name": "",
            "project_purpose": "",
            "current_stage": "",
            "current_objective": "",
            "workflow_context": "",
            "constraints": "",
            "support_preferences": "",
        },
    }


def _process_onboarding_message(session: dict, source: str, message: str) -> dict:
    log_message_with_context(
        source=source,
        role="user",
        message=message,
        mode="onboarding",
        module="freeform_onboarding",
        question_key="dynamic",
        message_type="interview_answer",
    )

    _append_conversation_turn(session, "user", message)

    update_result = _update_project_understanding(session, message)

    session["working_summary"] = update_result.get("working_summary", session.get("working_summary", ""))
    session["key_points"] = update_result.get("key_points", session.get("key_points", []))
    session["missing_areas"] = update_result.get("missing_areas", session.get("missing_areas", []))
    session["resolved_areas"] = update_result.get("resolved_areas", session.get("resolved_areas", []))
    session["out_of_scope_areas"] = update_result.get("out_of_scope_areas", session.get("out_of_scope_areas", []))
    session["readiness"] = {
        "is_ready": bool(update_result.get("is_ready", False)),
        "confidence": str(update_result.get("confidence", "low")).lower(),
        "reason": str(update_result.get("reason", "")).strip(),
    }

    if session["readiness"]["is_ready"] and session["readiness"]["confidence"] in ["medium", "high"]:
        session["readiness_streak"] = session.get("readiness_streak", 0) + 1
    else:
        session["readiness_streak"] = 0

    structured_project = update_result.get("structured_project", {})
    if isinstance(structured_project, dict):
        for key in session["structured_project"].keys():
            value = str(structured_project.get(key, "")).strip()
            if value:
                session["structured_project"][key] = value

    if _should_move_to_confirmation(session):
        session["awaiting_confirmation"] = True
        session["final_summary"] = _generate_final_summary(session)

        reply = (
            f"{session['final_summary']}\n\n"
            "Does this accurately reflect the project and how I should help? "
            "Reply with 'confirm' to save it, or tell me what needs changing."
        )
        _append_conversation_turn(session, "assistant", reply)

        return {
            "action": "captured_onboarding_message",
            "reply": reply,
        }

    next_question = _generate_conversational_next_question(session)
    _append_conversation_turn(session, "assistant", next_question)

    return {
        "action": "captured_onboarding_message",
        "reply": next_question,
    }


def _append_conversation_turn(session: dict, role: str, message: str, max_turns: int = 16) -> None:
    session.setdefault("conversation_history", []).append(
        {
            "role": role,
            "message": message,
        }
    )

    if len(session["conversation_history"]) > max_turns:
        session["conversation_history"] = session["conversation_history"][-max_turns:]


def _extract_json_object(raw: str) -> str:
    raw = (raw or "").strip()

    if raw.startswith("```"):
        lines = raw.splitlines()

        # Remove opening fence
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        # Remove closing fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        raw = "\n".join(lines).strip()

        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    start = raw.find("{")
    end = raw.rfind("}")

    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]

    return raw


def _update_project_understanding(session: dict, user_message: str) -> dict:
    recent_turns = session.get("conversation_history", [])[-10:]
    current_summary = session.get("working_summary", "")
    current_key_points = session.get("key_points", [])
    current_missing_areas = session.get("missing_areas", [])
    current_resolved_areas = session.get("resolved_areas", [])
    current_out_of_scope_areas = session.get("out_of_scope_areas", [])
    current_readiness = session.get("readiness", {})
    current_structured_project = session.get("structured_project", {})

    prompt = f"""
You are Jeffrey, the professional onboarder.

Your role is to onboard new projects into the system through natural conversation and turn messy explanations into usable understanding.

You are friendly, perceptive, and relaxed in tone, but underneath that you are sharp. You notice vagueness, contradictions, fuzzy goals, and missing logic. You do not attack the user, but you do try to get to clarity.

This is a FREEFORM conversational onboarding process.
It is not a rigid form.
It is not a checklist.
Different projects may need different kinds of questions.

Your job here is not to ask the next question.
Your job here is to update your understanding of the project based on the conversation so far.

You are trying to understand the project well enough that the assistant can be genuinely useful.

That means building a grounded view of:
- what the project is
- what it is trying to achieve
- what stage it is at
- what is still unclear
- what has already been answered well enough
- what has been explicitly marked outside scope
- what may be blocked, fuzzy, unrealistic, or underdefined
- how the system should help

Recent conversation:
{json.dumps(recent_turns, indent=2)}

Current working summary:
{current_summary}

Current key points:
{json.dumps(current_key_points, indent=2)}

Current missing areas:
{json.dumps(current_missing_areas, indent=2)}

Current resolved areas:
{json.dumps(current_resolved_areas, indent=2)}

Current out-of-scope areas:
{json.dumps(current_out_of_scope_areas, indent=2)}

Current readiness state:
{json.dumps(current_readiness, indent=2)}

Current structured project draft:
{json.dumps(current_structured_project, indent=2)}

Latest user message:
{user_message}

Update the onboarding understanding.

Return valid JSON only with this schema:
{{
  "working_summary": "A concise rolling summary of the project and what matters.",
  "key_points": ["Important point 1", "Important point 2"],
  "missing_areas": ["Specific unresolved area 1", "Specific unresolved area 2"],
  "resolved_areas": ["Area already answered sufficiently 1"],
  "out_of_scope_areas": ["Area explicitly outside scope 1"],
  "is_ready": false,
  "confidence": "low",
  "reason": "Why onboarding is or is not ready to move to confirmation.",
  "structured_project": {{
    "project_name": "",
    "project_purpose": "",
    "current_stage": "",
    "current_objective": "",
    "workflow_context": "",
    "constraints": "",
    "support_preferences": ""
  }}
}}

Rules:
- Stay grounded in what the user actually said.
- Do not invent details.
- It is okay for structured fields to stay blank if still unclear.
- Keep the working summary concise but useful.
- Key points should capture the most important facts or directions already established.
- Missing areas should be specific, concrete, and high-value.
- Do not use vague labels like "details", "workflow", or "constraints" on their own.
- Phrase missing areas as the real uncertainty still blocking useful support.
- Good example: "which part of the current workflow is still manual and painful"
- Bad example: "workflow"
- Resolved areas should capture topics that are now answered sufficiently and should not be re-opened unless the user changes direction.
- Out-of-scope areas should capture topics the user explicitly closed off, deprioritised, or marked as outside scope.
- If the user says something is outside scope, do not keep treating it as missing.
- Do not list more than 3 missing areas.
- Do not list more than 5 resolved or out-of-scope areas each.
- Prioritise unknowns that would most improve the assistant's usefulness.
- Mark is_ready true only if the assistant now has enough understanding to support this project meaningfully.
- Output JSON only.
""".strip()

    raw = call_ollama(prompt)
    debug_log(f"[ONBOARDING] RAW UNDERSTANDING RESPONSE: {raw}")

    cleaned = _extract_json_object(raw)
    debug_log(f"[ONBOARDING] CLEANED UNDERSTANDING RESPONSE: {cleaned}")

    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        debug_log(f"[ONBOARDING] Failed to parse project understanding JSON: {e}")
        return {
            "working_summary": session.get("working_summary", ""),
            "key_points": session.get("key_points", []),
            "missing_areas": session.get("missing_areas", []),
            "resolved_areas": session.get("resolved_areas", []),
            "out_of_scope_areas": session.get("out_of_scope_areas", []),
            "is_ready": False,
            "confidence": "low",
            "reason": f"Fallback due to JSON parse failure: {str(e)}",
            "structured_project": session.get("structured_project", {}),
        }

    parsed["missing_areas"] = _clean_string_list(parsed.get("missing_areas", []), max_items=3)
    parsed["resolved_areas"] = _clean_string_list(parsed.get("resolved_areas", []), max_items=5)
    parsed["out_of_scope_areas"] = _clean_string_list(parsed.get("out_of_scope_areas", []), max_items=5)
    parsed["key_points"] = _clean_string_list(parsed.get("key_points", []), max_items=8)

    parsed["missing_areas"] = _remove_overlaps(
        parsed["missing_areas"],
        parsed["resolved_areas"] + parsed["out_of_scope_areas"]
    )

    return parsed


def _generate_conversational_next_question(session: dict) -> str:
    recent_turns = session.get("conversation_history", [])[-10:]
    working_summary = session.get("working_summary", "")
    key_points = session.get("key_points", [])
    missing_areas = session.get("missing_areas", [])
    resolved_areas = session.get("resolved_areas", [])
    out_of_scope_areas = session.get("out_of_scope_areas", [])
    readiness = session.get("readiness", {})

    prompt = f"""
You are Jeffrey, the professional onboarder.

Your role is to onboard new projects into the system through natural conversation.

You are friendly, calm, perceptive, and slightly playful. You make the conversation feel easy and human, not like a formal interview. You are good at helping people explain messy ideas in a clearer way.

You do not just make small talk. Your job is to get enough real understanding to properly set up the project.

You are willing to challenge weak, vague, contradictory, or fuzzy thinking, but you do it in a light, constructive way. You do not come across as harsh, preachy, or accusatory. You push gently but clearly when something does not make sense yet.

You ask one question at a time. Each question should reduce uncertainty that matters. You listen closely to what the user already said and build from it.

This is a FREEFORM conversational onboarding process.
It is not a rigid interview.
It is not a checklist.
Different projects may need different questions.

Your goal is to understand the project well enough that the assistant can be genuinely useful.

You are trying to naturally uncover:
- what the project is
- what it is trying to achieve
- what stage it is in
- what is unclear or blocked
- how the system should help

When asking the next question:
- ask the single most useful question for improving project understanding
- connect it to what the user already said
- prefer concrete clarification over broad invitation
- if needed, challenge gently
- keep it conversational and natural
- avoid sounding like a checklist
- avoid sounding too clinical
- avoid generic filler
- do not reopen areas already resolved unless the user clearly changed direction
- do not ask about areas explicitly marked out of scope
- if the user explicitly marks something as outside scope, accept it and move on
- choose the most decision-relevant unresolved ambiguity

Do NOT ask generic filler questions like:
- "Can you tell me a bit more about that?"
- "Can you tell me more about that?"
- "Can you elaborate?"
- "Can you expand on that?"
- "Tell me more about that."

Do not ask the user to generally continue talking.
Instead, identify the most important unresolved ambiguity and ask a question that would reduce it.

Recent conversation:
{json.dumps(recent_turns, indent=2)}

Current working summary:
{working_summary}

Key points understood so far:
{json.dumps(key_points, indent=2)}

Missing areas or uncertainties:
{json.dumps(missing_areas, indent=2)}

Resolved areas:
{json.dumps(resolved_areas, indent=2)}

Out-of-scope areas:
{json.dumps(out_of_scope_areas, indent=2)}

Readiness state:
{json.dumps(readiness, indent=2)}

Output rules:
- Ask one question only.
- Output plain text only.
- Do not include labels, notes, or explanation.
- Do not write anything except the question.

Next question:
""".strip()

    raw = call_ollama(prompt)
    debug_log(f"[ONBOARDING] RAW QUESTION RESPONSE: {raw}")

    question = raw.strip()

    if _is_bad_onboarding_question(question):
        return _regenerate_question_with_stronger_prompt(session)

    return question


def _regenerate_question_with_stronger_prompt(session: dict) -> str:
    recent_turns = session.get("conversation_history", [])[-10:]
    working_summary = session.get("working_summary", "")
    missing_areas = session.get("missing_areas", [])
    resolved_areas = session.get("resolved_areas", [])
    out_of_scope_areas = session.get("out_of_scope_areas", [])
    last_user_message = _get_last_user_message(session)

    prompt = f"""
You are Jeffrey, the professional onboarder.

The previous question was too generic, weak, or repetitive.

You need to ask a better one.

Stay friendly, natural, and slightly playful, but be sharper this time.
Your job is to ask one specific question that improves project understanding.

Requirements:
- It must connect to what the user already said.
- It must reduce a real uncertainty that matters.
- It must not ask for vague elaboration.
- It must not be filler.
- It must not say things like "tell me more about that" or "can you elaborate".
- It must not reopen an area that is already resolved.
- It must not reopen an area explicitly marked out of scope.
- It should feel natural, but still move the onboarding forward meaningfully.

Recent conversation:
{json.dumps(recent_turns, indent=2)}

Current working summary:
{working_summary}

Missing areas:
{json.dumps(missing_areas, indent=2)}

Resolved areas:
{json.dumps(resolved_areas, indent=2)}

Out-of-scope areas:
{json.dumps(out_of_scope_areas, indent=2)}

Last user message:
{last_user_message}

Output rules:
- Ask one question only.
- Output plain text only.
- Do not include explanation.

Better next question:
""".strip()

    raw = call_ollama(prompt)
    debug_log(f"[ONBOARDING] RAW REGENERATED QUESTION RESPONSE: {raw}")

    question = raw.strip()

    if _is_bad_onboarding_question(question):
        return _build_open_but_specific_fallback(session)

    return question


def _is_bad_onboarding_question(question: str) -> bool:
    q = (question or "").strip().lower()

    if not q:
        return True

    banned_fragments = [
        "can you tell me a bit more about that",
        "can you tell me more about that",
        "could you tell me a bit more about that",
        "could you tell me more about that",
        "tell me more about that",
        "can you elaborate",
        "could you elaborate",
        "can you expand on that",
        "could you expand on that",
        "can you give me more detail",
        "could you give me more detail",
        "can you clarify that",
        "could you clarify that",
    ]

    return any(fragment in q for fragment in banned_fragments)


def _build_open_but_specific_fallback(session: dict) -> str:
    missing_areas = session.get("missing_areas", [])
    last_user_message = _get_last_user_message(session).strip()
    structured_project = session.get("structured_project", {})

    if missing_areas:
        area = str(missing_areas[0]).strip()
        if last_user_message:
            shortened = last_user_message.replace("\n", " ").strip()
            if len(shortened) > 120:
                shortened = shortened[:117].rstrip() + "..."
            return f"You mentioned '{shortened}'. What do I still need to understand about {area.lower()} to be genuinely useful on this project?"
        return f"What do I still need to understand about {area.lower()} to be genuinely useful on this project?"

    if structured_project.get("current_objective", "").strip() == "":
        return "What are you trying to get this project to do for you in practice right now?"

    if structured_project.get("workflow_context", "").strip() == "":
        return "How does this currently work in the real world from your side?"

    if structured_project.get("constraints", "").strip() == "":
        return "What realities or limits do I need to keep in mind so my help stays useful here?"

    return "What is the most important thing I still need to understand about this project to be genuinely useful?"


def _get_last_user_message(session: dict) -> str:
    history = session.get("conversation_history", [])
    for turn in reversed(history):
        if turn.get("role") == "user":
            return turn.get("message", "")
    return ""


def _should_move_to_confirmation(session: dict) -> bool:
    readiness = session.get("readiness", {})
    is_ready = bool(readiness.get("is_ready", False))
    confidence = str(readiness.get("confidence", "low")).lower()
    readiness_streak = int(session.get("readiness_streak", 0))

    return is_ready and confidence in ["medium", "high"] and readiness_streak >= 2


def _generate_final_summary(session: dict) -> str:
    prompt = f"""
You are preparing a final onboarding summary for user confirmation.

Use the conversation understanding below.
Create a clean review version that is easy for the user to verify.
Do not add anything that was not explicitly stated.

Working summary:
{session.get("working_summary", "")}

Key points:
{json.dumps(session.get("key_points", []), indent=2)}

Resolved areas:
{json.dumps(session.get("resolved_areas", []), indent=2)}

Out-of-scope areas:
{json.dumps(session.get("out_of_scope_areas", []), indent=2)}

Structured project draft:
{json.dumps(session.get("structured_project", {}), indent=2)}

Output plain text only.
""".strip()

    return call_ollama(prompt).strip()


def _revise_summary(current_summary: str, correction_feedback: str) -> str:
    prompt = f"""
You are revising an onboarding summary based on user correction feedback.

Current summary:
{current_summary}

User correction feedback:
{correction_feedback}

Rules:
- Update the summary to reflect the user's correction.
- Do not invent any new detail.
- Keep it clean and easy to review.
- Output plain text only.
""".strip()

    return call_ollama(prompt).strip()


def _write_onboarding_files(session: dict) -> None:
    os.makedirs(MEMORY_DIR, exist_ok=True)

    structured = session.get("structured_project", {})

    _write_file(
        "project-definition.md",
        f"""# Project Definition

## Project Name
{structured.get("project_name", "")}

## Project Purpose
{structured.get("project_purpose", "")}

## Current Stage
{structured.get("current_stage", "")}
""",
    )

    _write_file(
        "current-objective.md",
        f"""# Current Objective

{structured.get("current_objective", "")}
""",
    )

    _write_file(
        "workflow-context.md",
        f"""# Workflow Context

{structured.get("workflow_context", "")}
""",
    )

    _write_file(
        "constraints.md",
        f"""# Constraints

{structured.get("constraints", "")}
""",
    )

    _write_file(
        "support-preferences.md",
        f"""# Support Preferences

{structured.get("support_preferences", "")}
""",
    )

    _write_file(
        "onboarding-summary.md",
        f"""# Onboarding Summary

## Working Summary
{session.get("working_summary", "")}

## Key Points
{_format_bullets(session.get("key_points", []))}

## Resolved Areas
{_format_bullets(session.get("resolved_areas", []))}

## Out Of Scope Areas
{_format_bullets(session.get("out_of_scope_areas", []))}

## Remaining Unknowns At Time Of Confirmation
{_format_bullets(session.get("missing_areas", []))}
""",
    )


def _format_bullets(items: List[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return "- None noted"
    return "\n".join(f"- {item}" for item in cleaned)


def _clean_string_list(items, max_items: int) -> List[str]:
    cleaned = []
    seen = set()

    for item in items:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= max_items:
            break

    return cleaned


def _remove_overlaps(primary: List[str], blockers: List[str]) -> List[str]:
    blocker_keys = {str(item).strip().lower() for item in blockers if str(item).strip()}
    result = []

    for item in primary:
        key = str(item).strip().lower()
        if key and key not in blocker_keys:
            result.append(item)

    return result


def _write_file(filename: str, content: str) -> None:
    file_path = os.path.join(MEMORY_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content.strip() + "\n")


def _save_session(session: dict) -> None:
    session["updated_at"] = datetime.now().astimezone().isoformat()
    os.makedirs(MEMORY_DIR, exist_ok=True)

    with open(ONBOARDING_SESSION_PATH, "w", encoding="utf-8") as file:
        json.dump(session, file, indent=2)


def _load_session() -> dict:
    with open(ONBOARDING_SESSION_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def _delete_session() -> None:
    if os.path.exists(ONBOARDING_SESSION_PATH):
        os.remove(ONBOARDING_SESSION_PATH)