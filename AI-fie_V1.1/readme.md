# AI-fie V1.1

AI-fie V1.1 is a local-first personal AI system designed to act as a **Chief of Staff** for decision-making.

It captures inputs, processes them, and aligns outputs with user goals through a structured memory system.

---

## 🚧 Current Status

This is an **active build (V1.1)** focused on:

- Journaling system (raw input capture)
- Processing pipeline (LLM-based)
- Memory routing (working vs long-term)
- Onboarding + goal alignment system

The focus is on building a **clean, modular foundation**, not advanced AI behaviour yet.

---

## 🧠 Core Concept

The system follows a simple pipeline:


User Input → Raw Journal (JSONL) → Processing → Categorisation → Memory → Response


Key principles:

- Raw data is never modified
- Processing is separate from storage
- System is modular and replaceable
- Runs locally using a single LLM (Ollama)

---

## 🏗️ Project Structure (Example)


TBC


---

## ⚙️ Requirements

- Python 3.10+
- Git
- Ollama (for local LLM)

Install Ollama:
https://ollama.com

---

## 🚀 Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/AI-fie_V1.1.git
cd AI-fie_V1.1
2. Create virtual environment
python -m venv venv
venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt
4. Run Ollama model
ollama run llama3.1:8b
5. Start the app

(Adjust depending on your entry point)

python -m app.main

or

uvicorn app.main:app --reload
🔀 Branching Strategy
main → stable, working version
dev → active development

All new features should be built in dev and merged into main when stable.

🔐 Data & Privacy
All data is stored locally
No external APIs required (V1.1)
Raw journal logs are append-only
Sensitive files are excluded via .gitignore
📌 Notes

This project prioritises:

Simplicity over complexity
Control over automation
Structure over “magic”

It is intentionally constrained to:

Single LLM
No multi-agent systems
No over-optimisation
🛣️ Roadmap (High Level)
 Complete onboarding system
 Improve processing accuracy
 Memory optimisation
 Telegram integration
 Voice input/output pipeline

⚠️ Disclaimer

This is an experimental system under active development.

Expect:

breaking changes
incomplete features
rapid iteration
👤 Author

Alfred Carlson
Adelaide, South Australia