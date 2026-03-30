import json
import requests
from typing import Optional
from app.utils.logger import debug_log

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
MODEL_NAME = "llama3.1:8b"


def check_ollama_health() -> bool:
    """
    Check whether Ollama is running and reachable.
    """
    debug_log("[LLM] Checking Ollama health...")

    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
        debug_log(f"[LLM] Ollama health check status code: {response.status_code}")

        if response.status_code == 200:
            debug_log("[LLM] Ollama is reachable")
            return True

        debug_log("[LLM] Ollama responded, but not with status 200")
        return False

    except requests.RequestException as error:
        debug_log("[LLM] Ollama health check failed")
        debug_log(f"[LLM] Error: {error}")
        return False


def build_basic_prompt(user_message: str) -> str:
    """
    Build a very simple prompt for the local model.
    Later this will include memory, goals, rules, and founder profile context.
    """
    debug_log("[LLM] Building basic prompt...")

    prompt = (
        "You are AI-fie V1.1, a practical and concise personal chief of staff assistant.\n"
        "Respond clearly and directly.\n\n"
        f"User message: {user_message}\n\n"
        "Assistant response:"
    )

    debug_log("[LLM] Prompt built successfully")
    debug_log("[LLM] Prompt content:")
    debug_log(prompt)

    return prompt


def call_ollama(prompt: str, model: str = MODEL_NAME) -> Optional[str]:
    """
    Send a prompt to Ollama and return the model's response text.
    """
    debug_log("[LLM] Preparing to call Ollama...")
    debug_log(f"[LLM] Model: {model}")
    debug_log(f"[LLM] URL: {OLLAMA_GENERATE_URL}")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    debug_log("[LLM] Payload being sent:")
    debug_log(payload)

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=120
        )

        debug_log(f"[LLM] Ollama response status code: {response.status_code}")
        debug_log("[LLM] Raw response text:")
        debug_log(response.text)

        response.raise_for_status()

        data = response.json()
        model_response = data.get("response", "").strip()

        debug_log("[LLM] Extracted model response:")
        debug_log(model_response)

        return model_response

    except requests.RequestException as error:
        debug_log("[LLM] Request to Ollama failed")
        debug_log(f"[LLM] Error: {error}")
        return None

    except ValueError as error:
        debug_log("[LLM] Failed to parse Ollama JSON response")
        debug_log(f"[LLM] Error: {error}")
        return None


def generate_llm_response(user_message: str) -> str:
    """
    Main entry point for generating a response from Ollama.
    Falls back gracefully if Ollama is unavailable.
    """
    debug_log("\n[LLM] ===== Starting LLM response generation =====")
    debug_log(f"[LLM] Incoming user message: {user_message}")

    ollama_ok = check_ollama_health()

    if not ollama_ok:
        fallback = (
            "Ollama is not reachable right now. "
            "Please make sure Ollama is running and the model is installed."
        )
        debug_log("[LLM] Returning fallback response because Ollama is unavailable")
        debug_log("[LLM] ===== LLM response generation complete =====\n")
        return fallback

    prompt = build_basic_prompt(user_message)
    response = call_ollama(prompt)

    if not response:
        fallback = (
            "I could not generate a response from the local model. "
            "Check the terminal logs for the Ollama error."
        )
        debug_log("[LLM] Returning fallback response because model output was empty or failed")
        debug_log("[LLM] ===== LLM response generation complete =====\n")
        return fallback

    debug_log("[LLM] Final LLM response ready")
    debug_log("[LLM] ===== LLM response generation complete =====\n")
    return response


def check_ollama_health() -> bool:
    debug_log("[LLM] Checking Ollama health...")

    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
        debug_log(f"[LLM] Ollama health check status code: {response.status_code}")
        return response.status_code == 200
    except requests.RequestException as error:
        debug_log("[LLM] Ollama health check failed")
        debug_log(f"[LLM] Error: {error}")
        return False


def build_basic_prompt(user_message: str) -> str:
    debug_log("[LLM] Building basic prompt...")

    prompt = (
        "You are AI-fie V1.1, a practical and concise personal chief of staff assistant.\n"
        "Respond clearly and directly.\n\n"
        f"User message: {user_message}\n\n"
        "Assistant response:"
    )

    debug_log("[LLM] Prompt built successfully")
    debug_log(prompt)
    return prompt


def call_ollama(prompt: str, model: str = MODEL_NAME) -> Optional[str]:
    debug_log("[LLM] Preparing to call Ollama...")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=120
        )

        debug_log(f"[LLM] Ollama response status code: {response.status_code}")
        debug_log("[LLM] Raw response text:")
        debug_log(response.text)

        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    except requests.RequestException as error:
        debug_log("[LLM] Request to Ollama failed")
        debug_log(f"[LLM] Error: {error}")
        return None
    except ValueError as error:
        debug_log("[LLM] Failed to parse Ollama JSON response")
        debug_log(f"[LLM] Error: {error}")
        return None


def generate_llm_response(user_message: str) -> str:
    debug_log("\n[LLM] ===== Starting LLM response generation =====")
    debug_log(f"[LLM] Incoming user message: {user_message}")

    if not check_ollama_health():
        return (
            "Ollama is not reachable right now. "
            "Please make sure Ollama is running and the model is installed."
        )

    prompt = build_basic_prompt(user_message)
    response = call_ollama(prompt)

    if not response:
        return (
            "I could not generate a response from the local model. "
            "Check the terminal logs for the Ollama error."
        )

    debug_log("[LLM] ===== LLM response generation complete =====\n")
    return response


def build_processor_prompt(source: str, role: str, raw_message: str) -> str:
    """
    Prompt for structured processing.
    """
    debug_log("[LLM] Building processor prompt...")

    prompt = f"""
You are the processing layer for AI-fie V1.1.

Your job is to analyse one journal message and return a structured result.

Rules:
- Be practical and literal.
- Do not over-interpret.
- Simplify the message into a clean plain-English summary.
- Choose exactly one category from:
  goal-related, task, idea, reflection, general
- Assign:
  relevance_score: integer 0 to 100
  strategic_importance: integer 0 to 100
- Choose exactly one route from:
  current_focus, task_list, long_term_memory, ignore

Routing guidance:
- goal-related -> usually current_focus
- task -> usually task_list
- idea -> usually long_term_memory
- reflection -> usually long_term_memory
- general -> ignore unless clearly important

Message metadata:
- Source: {source}
- Role: {role}
- Raw message: {raw_message}

Return only the structured result.
""".strip()

    debug_log("[LLM] Processor prompt built successfully")
    debug_log(prompt)
    return prompt


def call_ollama_structured(prompt: str, model: str = MODEL_NAME) -> Optional[Dict[str, Any]]:
    """
    Call Ollama and ask for strict JSON output using a JSON schema.
    """
    debug_log("[LLM] Preparing structured Ollama call...")

    schema = {
        "type": "object",
        "properties": {
            "simplified_message": {"type": "string"},
            "category": {
                "type": "string",
                "enum": ["goal-related", "task", "idea", "reflection", "general"]
            },
            "relevance_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "strategic_importance": {"type": "integer", "minimum": 0, "maximum": 100},
            "route": {
                "type": "string",
                "enum": ["current_focus", "task_list", "long_term_memory", "ignore"]
            }
        },
        "required": [
            "simplified_message",
            "category",
            "relevance_score",
            "strategic_importance",
            "route"
        ]
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": schema
    }

    debug_log("[LLM] Structured payload being sent:")
    debug_log(payload)

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=120
        )

        debug_log(f"[LLM] Structured response status code: {response.status_code}")
        debug_log("[LLM] Raw structured response text:")
        debug_log(response.text)

        response.raise_for_status()
        outer_data = response.json()

        raw_model_output = outer_data.get("response", "").strip()
        debug_log("[LLM] Extracted structured model output string:")
        debug_log(raw_model_output)

        parsed = json.loads(raw_model_output)
        debug_log("[LLM] Parsed structured output:")
        debug_log(parsed)

        return parsed

    except requests.RequestException as error:
        debug_log("[LLM] Structured request to Ollama failed")
        debug_log(f"[LLM] Error: {error}")
        return None

    except ValueError as error:
        debug_log("[LLM] Failed to parse structured JSON output")
        debug_log(f"[LLM] Error: {error}")
        return None


def process_message_with_llm(source: str, role: str, raw_message: str) -> Optional[Dict[str, Any]]:
    """
    Main entry point for structured message processing.
    """
    debug_log("\n[LLM] ===== Starting structured message processing =====")
    debug_log(f"[LLM] Source: {source}")
    debug_log(f"[LLM] Role: {role}")
    debug_log(f"[LLM] Raw message: {raw_message}")

    if not check_ollama_health():
        debug_log("[LLM] Ollama not reachable for structured processing")
        return None

    prompt = build_processor_prompt(source, role, raw_message)
    result = call_ollama_structured(prompt)

    if result is None:
        debug_log("[LLM] Structured processing failed")
        return None

    debug_log("[LLM] ===== Structured message processing complete =====\n")
    return result