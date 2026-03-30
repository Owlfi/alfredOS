from email.mime import message
import json
import os
from datetime import datetime

from app.services.goal_service import get_system_mode, set_system_mode
from app.services.journal_service import log_message_with_context
from app.services.llm_service import call_ollama
from app.utils.logger import debug_log


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MEMORY_DIR = os.path.join(BASE_DIR, "data", "memory")
ONBOARDING_SESSION_PATH = os.path.join(MEMORY_DIR, "onboarding_session.json")

print("ONBOARDING SERVICE LOADED")

def handle_onboarding_mode(source: str, message: str) -> dict:
    debug_log("[ONBOARDING] FUNCTION HIT")
    """
    Main onboarding entry point for chat_orchestrator.

    Returns:
    {
        "action": str,
        "reply": str
    }
    """

    # FORCE onboarding mode (explicit command)
    if message.strip().lower() == "enter onboarding mode":
        debug_log("[ONBOARDING] Force entering onboarding mode")

        session = _create_onboarding_session()
        _save_session(session)
        set_system_mode("onboarding")

        first_question = _get_current_question(session)

        return {
            "action": "entered_onboarding_mode",
            "reply": first_question
        }

    current_mode = get_system_mode()

    debug_log(f"[ONBOARDING] Current system mode: {current_mode}")

    # Trigger onboarding mode manually
    if current_mode != "onboarding" and _is_onboarding_trigger(message):
        debug_log("[ONBOARDING] Entering onboarding mode")
        session = _create_onboarding_session()
        _save_session(session)
        set_system_mode("onboarding")

        first_question = _get_current_question(session)

        return {
            "action": "entered_onboarding_mode",
            "reply": first_question
        }

    # If onboarding mode is active, capture and continue flow
    if current_mode == "onboarding":
        debug_log("[ONBOARDING] Onboarding mode is active")

        if not os.path.exists(ONBOARDING_SESSION_PATH):
            debug_log("[ONBOARDING] No session found, creating a new onboarding session")
            session = _create_onboarding_session()
            _save_session(session)

            first_question = _get_current_question(session)

            return {
                "action": "entered_onboarding_mode",
                "reply": first_question
            }

        session = _load_session()

        # If awaiting confirmation
        if session.get("awaiting_confirmation", False):
            if message.strip().lower() == "confirm":
                debug_log("[ONBOARDING] Final confirmation received")
                _write_onboarding_files(session)
                set_system_mode("normal")
                _delete_session()

                return {
                    "action": "exited_onboarding_mode",
                    "reply": "Onboarding complete. Your onboarding files have been saved."
                }

            debug_log("[ONBOARDING] Revising final summary based on feedback")
            session["final_summary"] = _revise_summary(
                current_summary=session.get("final_summary", ""),
                correction_feedback=message
            )
            _save_session(session)

            return {
                "action": "captured_onboarding_message",
                "reply": (
                    f"{session['final_summary']}\n\n"
                    "Reply with 'confirm' to save it, or tell me what still needs changing."
                )
            }

        # Normal question flow
        result = _process_onboarding_answer(session, source, message)
        _save_session(session)
        return result

    return {
        "action": "no_action",
        "reply": ""
    }


def _is_onboarding_trigger(message: str) -> bool:
    trigger_phrases = [
        "start onboarding",
        "begin onboarding",
        "i want to do onboarding",
        "let's do onboarding",
        "setup my profile",
        "set up my profile"
    ]
    lowered = message.strip().lower()
    return lowered in trigger_phrases


def _create_onboarding_session() -> dict:
    now = datetime.now().astimezone().isoformat()

    return {
        "session_id": f"onboarding_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "mode": "onboarding",
        "status": "in_progress",
        "current_module_index": 0,
        "current_question_index": 0,
        "current_followup_count": 0,
        "awaiting_confirmation": False,
        "final_summary": "",
        "created_at": now,
        "updated_at": now,
        "modules": [
            {
                "key": "founder_profile",
                "title": "Founder Profile",
                "questions": [
                    {"key": "name", "text": "What is your name?"},
                    {"key": "current_situation", "text": "What are you currently doing?"},
                    {"key": "strengths", "text": "What are your main strengths?"},
                    {"key": "struggles", "text": "What do you tend to struggle with?"},
                    {"key": "identity_direction", "text": "What kind of person are you trying to become?"},
                ],
                "answers": [],
                "module_summary": ""
            },
            {
                "key": "goals",
                "title": "Goals",
                "questions": [
                    {"key": "top_goals", "text": "What are your top 3 goals right now?"},
                    {"key": "twelve_month_outcome", "text": "What are you trying to achieve in the next 12 months?"},
                    {"key": "what_matters_now", "text": "What matters most to you right now?"},
                ],
                "answers": [],
                "module_summary": ""
            },
            {
                "key": "current_focus",
                "title": "Current Focus",
                "questions": [
                    {"key": "active_work", "text": "What are you currently working on?"},
                    {"key": "weekly_priorities", "text": "What are your top 3 priorities this week?"},
                    {"key": "current_bottleneck", "text": "What is the biggest thing slowing you down right now?"},
                ],
                "answers": [],
                "module_summary": ""
            },
            {
                "key": "help_preferences",
                "title": "Help Preferences",
                "questions": [
                    {"key": "advice_style", "text": "Do you want direct advice or softer guidance?"},
                    {"key": "response_style", "text": "Do you prefer short answers or detailed breakdowns?"},
                    {"key": "challenge_level", "text": "Should I challenge weak thinking when I see it?"},
                    {"key": "preferred_support", "text": "What kind of help is most useful to you?"},
                ],
                "answers": [],
                "module_summary": ""
            }
        ]
    }


def _process_onboarding_answer(session: dict, source: str, message: str) -> dict:
    module = session["modules"][session["current_module_index"]]
    question = module["questions"][session["current_question_index"]]

    log_message_with_context(
        source=source,
        role="user",
        message=message,
        mode="onboarding",
        module=module["key"],
        question_key=question["key"],
        message_type="interview_answer"
    )

    answer_record = _get_or_create_answer_record(module, question)

    if not answer_record.get("raw_answer"):
        answer_record["raw_answer"] = message
    else:
        answer_record.setdefault("followups", []).append(message)

    combined_answer = _combine_answer_record(answer_record)
    evaluation = _evaluate_answer(question["text"], combined_answer)
    answer_record["evaluation"] = evaluation

    if evaluation.get("needs_followup") and session["current_followup_count"] < 2:
        session["current_followup_count"] += 1
        followup = evaluation.get("followup_question") or "Can you give me a bit more detail on that?"

        return {
            "action": "captured_onboarding_message",
            "reply": followup
        }

    session["current_followup_count"] = 0

    # Move to next question or module
    if session["current_question_index"] < len(module["questions"]) - 1:
        session["current_question_index"] += 1
        next_question = _get_current_question(session)

        return {
            "action": "captured_onboarding_message",
            "reply": next_question
        }

    # Module complete
    module["module_summary"] = _generate_module_summary(module)

    if session["current_module_index"] < len(session["modules"]) - 1:
        session["current_module_index"] += 1
        session["current_question_index"] = 0
        next_question = _get_current_question(session)

        return {
            "action": "captured_onboarding_message",
            "reply": f"Module summary:\n\n{module['module_summary']}\n\n{next_question}"
        }

    # Final summary
    session["awaiting_confirmation"] = True
    session["final_summary"] = _generate_final_summary(session)

    return {
        "action": "captured_onboarding_message",
        "reply": (
            f"{session['final_summary']}\n\n"
            "Does this accurately reflect your current situation and direction? "
            "Reply with 'confirm' to save it, or tell me what needs changing."
        )
    }


def _get_current_question(session: dict) -> str:
    module = session["modules"][session["current_module_index"]]
    question = module["questions"][session["current_question_index"]]
    return question["text"]


def _get_or_create_answer_record(module: dict, question: dict) -> dict:
    for answer in module["answers"]:
        if answer["question_key"] == question["key"]:
            return answer

    new_record = {
        "question_key": question["key"],
        "question_text": question["text"],
        "raw_answer": "",
        "followups": [],
        "evaluation": {}
    }
    module["answers"].append(new_record)
    return new_record


def _combine_answer_record(answer_record: dict) -> str:
    parts = []
    if answer_record.get("raw_answer"):
        parts.append(answer_record["raw_answer"])
    parts.extend(answer_record.get("followups", []))
    return "\n".join(parts).strip()


def _evaluate_answer(question_text: str, answer_text: str) -> dict:
    prompt = f"""
You are evaluating a user's answer in an onboarding interview.

Question:
{question_text}

User answer:
{answer_text}

Your job:
1. Decide whether the answer actually addresses the question.
2. Judge whether it is specific enough to be useful.
3. Judge whether it is complete enough to move on.
4. If not complete, propose one short follow-up question.
5. Extract the factual points given by the user.

Rules:
- Do not give advice.
- Do not rewrite the user's intent.
- Stay grounded in the user's wording.
- Be conservative with follow-ups.
- Return valid JSON only.

Return JSON with this schema only:
{{
  "answered_question": true,
  "specificity": "high",
  "completeness": "medium",
  "confidence_to_move_on": "medium",
  "needs_followup": true,
  "followup_question": "Can you give me one or two specific examples?",
  "extracted_facts": ["example fact 1", "example fact 2"]
}}
""".strip()

    raw = call_ollama(prompt)

    try:
        return json.loads(raw)
    except Exception:
        return {
            "answered_question": True,
            "specificity": "medium",
            "completeness": "medium",
            "confidence_to_move_on": "medium",
            "needs_followup": False,
            "followup_question": "",
            "extracted_facts": []
        }


def _generate_module_summary(module: dict) -> str:
    qa_lines = []
    for answer in module["answers"]:
        qa_lines.append(f"Q: {answer['question_text']}\nA: {_combine_answer_record(answer)}")

    prompt = f"""
You are summarising one onboarding module.

Module: {module['title']}

Questions and answers:
{chr(10).join(qa_lines)}

Rules:
- Be concise.
- Be factual.
- Stay close to the user's wording.
- Do not invent detail.
- Do not over-interpret.
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

    founder = modules["founder_profile"]
    goals = modules["goals"]
    current_focus = modules["current_focus"]
    help_preferences = modules["help_preferences"]

    founder_answers = {a["question_key"]: _combine_answer_record(a) for a in founder["answers"]}
    goals_answers = {a["question_key"]: _combine_answer_record(a) for a in goals["answers"]}
    current_answers = {a["question_key"]: _combine_answer_record(a) for a in current_focus["answers"]}
    help_answers = {a["question_key"]: _combine_answer_record(a) for a in help_preferences["answers"]}

    _write_file(
        "founder-profile.md",
        f"""# Founder Profile

## Name
{founder_answers.get('name', '')}

## Current Situation
{founder_answers.get('current_situation', '')}

## Strengths
- {founder_answers.get('strengths', '')}

## Struggles
- {founder_answers.get('struggles', '')}

## Identity Direction
{founder_answers.get('identity_direction', '')}
"""
    )

    _write_file(
        "goals.md",
        f"""# Goals

## Top Goals
1. {goals_answers.get('top_goals', '')}

## 12-Month Outcome
{goals_answers.get('twelve_month_outcome', '')}

## What Matters Most Now
{goals_answers.get('what_matters_now', '')}
"""
    )

    _write_file(
        "current-focus.md",
        f"""# Current Focus

## Active Work
{current_answers.get('active_work', '')}

## Weekly Priorities
1. {current_answers.get('weekly_priorities', '')}

## Current Bottleneck
{current_answers.get('current_bottleneck', '')}
"""
    )

    _write_file(
        "help-preferences.md",
        f"""# Help Preferences

## Advice Style
{help_answers.get('advice_style', '')}

## Response Style
{help_answers.get('response_style', '')}

## Challenge Level
{help_answers.get('challenge_level', '')}

## Preferred Support
{help_answers.get('preferred_support', '')}
"""
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