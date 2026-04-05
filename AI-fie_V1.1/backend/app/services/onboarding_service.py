import json
import os
import re
from datetime import datetime
from typing import Dict, List

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
        first_question = _generate_next_question(session)
        first_question = _enforce_specific_question(
            session=session,
            candidate_question=first_question,
            target_field_key="",
            user_message="",
        )
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
        first_question = _generate_next_question(session)
        first_question = _enforce_specific_question(
            session=session,
            candidate_question=first_question,
            target_field_key="",
            user_message="",
        )
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
            first_question = _generate_next_question(session)
            first_question = _enforce_specific_question(
                session=session,
                candidate_question=first_question,
                target_field_key="",
                user_message="",
            )
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
        "active_module_key": "project_definition",
        "current_followup_count": 0,
        "awaiting_confirmation": False,
        "final_summary": "",
        "created_at": now,
        "updated_at": now,
        "conversation_history": [],
        "modules": [
            {
                "key": "project_definition",
                "title": "Project Definition",
                "required_fields": [
                    {
                        "key": "project_name",
                        "description": "The name of the project or working label",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "project_purpose",
                        "description": "What the project is trying to achieve",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "current_stage",
                        "description": "What stage the project is currently in",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "why_it_matters",
                        "description": "Why this project matters right now",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                ],
                "module_summary": "",
            },
            {
                "key": "current_objective",
                "title": "Current Objective",
                "required_fields": [
                    {
                        "key": "phase_goal",
                        "description": "The main goal of the current phase",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "definition_of_done",
                        "description": "What done looks like for this phase",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "key_deliverables",
                        "description": "The main deliverables to produce in this phase",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "next_move",
                        "description": "The single most important next move",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                ],
                "module_summary": "",
            },
            {
                "key": "workflow_context",
                "title": "Workflow Context",
                "required_fields": [
                    {
                        "key": "current_workflow",
                        "description": "How the work currently gets done",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "tools_used",
                        "description": "What tools, platforms, or systems are involved",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "key_inputs",
                        "description": "What inputs the workflow usually starts from",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "desired_outputs",
                        "description": "What outputs the agent should help produce",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                ],
                "module_summary": "",
            },
            {
                "key": "constraints",
                "title": "Constraints",
                "required_fields": [
                    {
                        "key": "current_constraints",
                        "description": "Current constraints, limits, or conditions to respect",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "out_of_scope",
                        "description": "What should be treated as out of scope",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "risks_or_blockers",
                        "description": "Known blockers, risks, or friction points",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                ],
                "module_summary": "",
            },
            {
                "key": "support_preferences",
                "title": "Support Preferences",
                "required_fields": [
                    {
                        "key": "support_role",
                        "description": "How the agent should behave in this project",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "response_style",
                        "description": "Preferred response style",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "challenge_level",
                        "description": "How directly the agent should challenge weak thinking",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                    {
                        "key": "optimisation_priority",
                        "description": "Whether to optimise for speed, depth, simplicity, or quality",
                        "value": "",
                        "confidence": "low",
                        "status": "missing",
                        "source_notes": [],
                    },
                ],
                "module_summary": "",
            },
        ],
    }


def _process_onboarding_message(session: dict, source: str, message: str) -> dict:
    module = _get_active_module(session)

    log_message_with_context(
        source=source,
        role="user",
        message=message,
        mode="onboarding",
        module=module["key"],
        question_key="dynamic",
        message_type="interview_answer",
    )

    _append_conversation_turn(session, "user", message)

    extraction_result = _extract_and_update_fields(session, message)
    module = _get_active_module(session)

    if _is_module_complete(module):
        session["current_followup_count"] = 0
        module["module_summary"] = _generate_module_summary(module)

        moved = _advance_to_next_module(session)

        if moved:
            next_question = _generate_next_question(session)
            next_question = _enforce_specific_question(
                session=session,
                candidate_question=next_question,
                target_field_key="",
                user_message=message,
            )
            reply = f"Module summary:\n\n{module['module_summary']}\n\n{next_question}"
            _append_conversation_turn(session, "assistant", reply)

            return {
                "action": "captured_onboarding_message",
                "reply": reply,
            }

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

    if extraction_result.get("needs_followup", True) and session["current_followup_count"] < 2:
        session["current_followup_count"] += 1
        next_question = extraction_result.get("followup_question", "")
        target_field_key = str(extraction_result.get("target_field_key", "")).strip()
    else:
        session["current_followup_count"] = 0
        next_question = _generate_next_question(session)
        target_field_key = ""

    next_question = _enforce_specific_question(
        session=session,
        candidate_question=next_question,
        target_field_key=target_field_key,
        user_message=message,
    )

    _append_conversation_turn(session, "assistant", next_question)

    return {
        "action": "captured_onboarding_message",
        "reply": next_question,
    }


def _get_active_module(session: dict) -> dict:
    active_key = session["active_module_key"]
    for module in session["modules"]:
        if module["key"] == active_key:
            return module
    raise ValueError(f"Active module not found: {active_key}")


def _append_conversation_turn(session: dict, role: str, message: str, max_turns: int = 10) -> None:
    session.setdefault("conversation_history", []).append(
        {
            "role": role,
            "message": message,
        }
    )

    if len(session["conversation_history"]) > max_turns:
        session["conversation_history"] = session["conversation_history"][-max_turns:]


def _get_last_user_message(session: dict) -> str:
    history = session.get("conversation_history", [])
    for turn in reversed(history):
        if turn.get("role") == "user":
            return turn.get("message", "")
    return ""


def _get_missing_fields(module: dict) -> List[dict]:
    missing = []
    for field in module.get("required_fields", []):
        if not (
            field.get("status") == "filled"
            and field.get("confidence") in ["medium", "high"]
        ):
            missing.append(field)
    return missing


def _is_module_complete(module: dict) -> bool:
    return len(_get_missing_fields(module)) == 0


def _advance_to_next_module(session: dict) -> bool:
    module_keys = [module["key"] for module in session["modules"]]
    current_key = session["active_module_key"]

    try:
        idx = module_keys.index(current_key)
    except ValueError:
        return False

    if idx < len(module_keys) - 1:
        session["active_module_key"] = module_keys[idx + 1]
        session["current_followup_count"] = 0
        return True

    return False


def _extract_and_update_fields(session: dict, user_message: str) -> dict:
    module = _get_active_module(session)

    fields_for_prompt = []
    for field in module["required_fields"]:
        fields_for_prompt.append(
            {
                "key": field["key"],
                "description": field["description"],
                "current_value": field["value"],
                "current_confidence": field["confidence"],
                "status": field["status"],
            }
        )

    recent_turns = session.get("conversation_history", [])[-6:]

    prompt = f"""
You are updating a structured onboarding session for a project-specific AI assistant.

Current module:
{module['title']}

Required fields:
{json.dumps(fields_for_prompt, indent=2)}

Recent conversation:
{json.dumps(recent_turns, indent=2)}

Latest user message:
{user_message}

Your job:
1. Extract useful facts from the user's latest message.
2. Update any fields that now have enough information.
3. Leave fields unchanged if the message does not clearly support them.
4. Mark confidence as low, medium, or high.
5. Mark each field status as either missing or filled.
6. Decide whether a follow-up is still needed in this module.
7. If a follow-up is needed, it MUST be specific.
8. The follow-up question MUST clearly connect to something the user just said or to an obviously missing project detail.
9. When possible, start from something the user already mentioned and extend it into the next missing detail.
10. Do NOT ask vague questions like "Can you tell me a bit more about that?"
11. Do NOT repeat information already known with medium or high confidence.
12. Prefer asking about the single most important missing field.
13. Stay grounded in the user's wording.
14. Return valid JSON only.

Return JSON in this schema:
{{
  "field_updates": [
    {{
      "key": "example_field",
      "value": "example value",
      "confidence": "medium",
      "status": "filled",
      "source_note": "Short note about why this field was updated."
    }}
  ],
  "needs_followup": true,
  "followup_question": "One specific natural next question.",
  "target_field_key": "the_main_field_this_question_is_trying_to_fill",
  "reasoning_note": "Short note about what is still missing."
}}
""".strip()

    raw = call_ollama(prompt)

    try:
        parsed = json.loads(raw)
    except Exception:
        debug_log("[ONBOARDING] Failed to parse field extraction JSON")
        return {
            "field_updates": [],
            "needs_followup": True,
            "followup_question": _build_specific_fallback_question(
                module=module,
                target_field_key="",
                user_message=user_message,
            ),
            "target_field_key": "",
            "reasoning_note": "Fallback due to JSON parse failure.",
        }

    updates_by_key = {u["key"]: u for u in parsed.get("field_updates", []) if u.get("key")}

    for field in module["required_fields"]:
        update = updates_by_key.get(field["key"])
        if not update:
            continue

        new_value = str(update.get("value", field["value"])).strip()
        if new_value:
            field["value"] = new_value

        confidence = str(update.get("confidence", field["confidence"])).lower().strip()
        if confidence in ["low", "medium", "high"]:
            field["confidence"] = confidence

        status = str(update.get("status", field["status"])).lower().strip()
        if status in ["missing", "filled"]:
            field["status"] = status

        source_note = str(update.get("source_note", "")).strip()
        if source_note:
            field.setdefault("source_notes", []).append(source_note)

    followup_question = str(parsed.get("followup_question", "")).strip()
    target_field_key = str(parsed.get("target_field_key", "")).strip()

    if parsed.get("needs_followup", True):
        parsed["followup_question"] = _enforce_specific_question(
            session=session,
            candidate_question=followup_question,
            target_field_key=target_field_key,
            user_message=user_message,
        )

    return parsed


def _generate_next_question(session: dict) -> str:
    module = _get_active_module(session)
    missing_fields = _get_missing_fields(module)

    required_fields = []
    for field in module["required_fields"]:
        required_fields.append(
            {
                "key": field["key"],
                "description": field["description"],
                "value": field["value"],
                "confidence": field["confidence"],
                "status": field["status"],
            }
        )

    prompt_missing_fields = []
    for field in missing_fields:
        prompt_missing_fields.append(
            {
                "key": field["key"],
                "description": field["description"],
                "value": field["value"],
                "confidence": field["confidence"],
                "status": field["status"],
            }
        )

    recent_turns = session.get("conversation_history", [])[-6:]

    prompt = f"""
You are guiding a conversational onboarding flow for a project-specific AI assistant.

Current module:
{module['title']}

All required fields:
{json.dumps(required_fields, indent=2)}

Missing or weak fields:
{json.dumps(prompt_missing_fields, indent=2)}

Recent conversation:
{json.dumps(recent_turns, indent=2)}

Your job:
- Ask the single best next question for this module.
- Make it specific.
- Make it sound natural and conversational.
- Link it to what the user has already said where possible.
- When possible, start from something the user already mentioned and extend it into the next missing detail.
- Focus on the most important missing field.
- Do not sound like a generic form.
- Do not ask vague questions like "Can you tell me a bit more about that?"
- Do not repeat information already known with medium or high confidence.
- Ask one question only.
- Output plain text only.

Next question:
""".strip()

    question = call_ollama(prompt).strip()

    primary_missing_key = ""
    if missing_fields:
        primary_missing_key = missing_fields[0]["key"]

    return _enforce_specific_question(
        session=session,
        candidate_question=question,
        target_field_key=primary_missing_key,
        user_message=_get_last_user_message(session),
    )


def _is_generic_question(question: str) -> bool:
    q = (question or "").strip().lower()

    if not q:
        return True

    generic_patterns = [
        r"^can you tell me a bit more about that\??$",
        r"^can you tell me more about that\??$",
        r"^could you tell me a bit more about that\??$",
        r"^could you tell me more about that\??$",
        r"^tell me more about that\??$",
        r"^can you expand on that\??$",
        r"^could you expand on that\??$",
        r"^can you elaborate\??$",
        r"^could you elaborate\??$",
        r"^can you give me more detail\??$",
        r"^could you give me more detail\??$",
        r"^can you explain that a bit more\??$",
        r"^could you explain that a bit more\??$",
        r"^can you clarify that\??$",
        r"^could you clarify that\??$",
        r"^what do you mean by that\??$",
    ]

    for pattern in generic_patterns:
        if re.match(pattern, q):
            return True

    vague_fragments = [
        "tell me more about that",
        "bit more about that",
        "expand on that",
        "elaborate on that",
        "give me more detail",
        "clarify that",
        "explain that a bit more",
    ]

    if any(fragment in q for fragment in vague_fragments):
        return True

    return False


def _enforce_specific_question(
    session: dict,
    candidate_question: str,
    target_field_key: str = "",
    user_message: str = "",
) -> str:
    module = _get_active_module(session)

    if not _is_generic_question(candidate_question):
        return candidate_question.strip()

    return _build_specific_fallback_question(
        module=module,
        target_field_key=target_field_key,
        user_message=user_message,
    )


def _build_specific_fallback_question(
    module: dict,
    target_field_key: str = "",
    user_message: str = "",
) -> str:
    missing_fields = _get_missing_fields(module)

    if not missing_fields:
        return "What is the most important thing I still need to understand about this project?"

    target_field = None

    if target_field_key:
        for field in missing_fields:
            if field["key"] == target_field_key:
                target_field = field
                break

    if target_field is None:
        target_field = missing_fields[0]

    key = target_field["key"]
    user_text = (user_message or "").strip()

    fallback_map = {
        "project_name": "What are you calling this project at the moment?",
        "project_purpose": "What is this project trying to achieve overall?",
        "current_stage": "Where is this project up to right now?",
        "why_it_matters": "Why does this project matter to you right now?",
        "phase_goal": "What is the main goal of the current phase?",
        "definition_of_done": "What would 'done' look like for this phase?",
        "key_deliverables": "What are the main things you want produced in this phase?",
        "next_move": "What is the single most important next step from here?",
        "current_workflow": "How are you currently doing this work from start to finish?",
        "tools_used": "What tools or platforms are already part of this workflow?",
        "key_inputs": "What do you usually start with when this workflow begins?",
        "desired_outputs": "What outputs do you want the agent to help create?",
        "current_constraints": "What constraints or limits do I need to respect here?",
        "out_of_scope": "What should I treat as out of scope for this phase?",
        "risks_or_blockers": "What is currently slowing this down or getting in the way?",
        "support_role": "How do you want me to help in this project — more like a strategist, operator, reviewer, or thought partner?",
        "response_style": "Do you want short answers, detailed breakdowns, or step-by-step help for this project?",
        "challenge_level": "Should I challenge weak logic directly when I see it in this project?",
        "optimisation_priority": "Should I optimise more for speed, depth, simplicity, or quality here?",
    }

    base_question = fallback_map.get(
        key,
        f"What can you tell me about {target_field['description'].lower()}?",
    )

    if user_text:
        shortened = user_text.replace("\n", " ").strip()
        if len(shortened) > 120:
            shortened = shortened[:117].rstrip() + "..."

        anchored_templates = {
            "project_purpose": f"You mentioned '{shortened}'. What is the overall outcome this project is trying to achieve?",
            "current_stage": f"Based on what you just said — '{shortened}' — where is the project up to right now?",
            "phase_goal": f"You mentioned '{shortened}'. What is the main goal of the current phase?",
            "definition_of_done": f"From what you just said — '{shortened}' — what would a successful result look like for this phase?",
            "current_workflow": f"You mentioned '{shortened}'. How does this workflow currently run from start to finish?",
            "tools_used": f"You mentioned '{shortened}'. What tools or platforms are already part of that process?",
            "desired_outputs": f"You mentioned '{shortened}'. What outputs do you want the agent to help create from that?",
            "current_constraints": f"You mentioned '{shortened}'. What constraints or limits do I need to respect here?",
            "risks_or_blockers": f"You mentioned '{shortened}'. What is the main thing making this harder or slowing it down?",
        }

        if key in anchored_templates:
            return anchored_templates[key]

    return base_question


def _generate_module_summary(module: dict) -> str:
    field_lines = []
    for field in module["required_fields"]:
        if field.get("value"):
            field_lines.append(f"{field['description']}: {field['value']}")

    prompt = f"""
You are summarising one onboarding module.

Module: {module['title']}

Collected field values:
{chr(10).join(field_lines)}

Rules:
- Be concise.
- Be factual.
- Stay close to the user's wording.
- Do not invent detail.
- Output plain text only.
""".strip()

    return call_ollama(prompt).strip()


def _generate_final_summary(session: dict) -> str:
    parts = []
    for module in session["modules"]:
        parts.append(f"{module['title']}:\n{module.get('module_summary', '')}")

    prompt = f"""
You are preparing a final onboarding summary for user confirmation.

Use the module summaries below.
Create a clean review version that is easy for the user to verify.
Do not add anything that was not explicitly stated.

{chr(10).join(parts)}

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
    modules = {module["key"]: module for module in session["modules"]}

    def get_field(module_key: str, field_key: str) -> str:
        module = modules[module_key]
        for field in module["required_fields"]:
            if field["key"] == field_key:
                return field.get("value", "")
        return ""

    _write_file(
        "project-definition.md",
        f"""# Project Definition

## Project Name
{get_field("project_definition", "project_name")}

## Project Purpose
{get_field("project_definition", "project_purpose")}

## Current Stage
{get_field("project_definition", "current_stage")}

## Why It Matters
{get_field("project_definition", "why_it_matters")}
""",
    )

    _write_file(
        "current-objective.md",
        f"""# Current Objective

## Phase Goal
{get_field("current_objective", "phase_goal")}

## Definition of Done
{get_field("current_objective", "definition_of_done")}

## Key Deliverables
{get_field("current_objective", "key_deliverables")}

## Next Move
{get_field("current_objective", "next_move")}
""",
    )

    _write_file(
        "workflow-context.md",
        f"""# Workflow Context

## Current Workflow
{get_field("workflow_context", "current_workflow")}

## Tools Used
{get_field("workflow_context", "tools_used")}

## Key Inputs
{get_field("workflow_context", "key_inputs")}

## Desired Outputs
{get_field("workflow_context", "desired_outputs")}
""",
    )

    _write_file(
        "constraints.md",
        f"""# Constraints

## Current Constraints
{get_field("constraints", "current_constraints")}

## Out of Scope
{get_field("constraints", "out_of_scope")}

## Risks or Blockers
{get_field("constraints", "risks_or_blockers")}
""",
    )

    _write_file(
        "support-preferences.md",
        f"""# Support Preferences

## Support Role
{get_field("support_preferences", "support_role")}

## Response Style
{get_field("support_preferences", "response_style")}

## Challenge Level
{get_field("support_preferences", "challenge_level")}

## Optimisation Priority
{get_field("support_preferences", "optimisation_priority")}
""",
    )


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