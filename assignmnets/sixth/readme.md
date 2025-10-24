# 📚 Agent Fable - A Kids Story Maker with Multi-Agent Cognitive System (Planner • Author • Critic)

Kid-safe story generator for ages **6–10** using a **4-layer cognitive architecture**:
- **Perception** → normalize user preferences
- **Memory** → store last preferences/topic per user (in-process)
- **Decision** → adjust strategy (e.g., word count by taste)
- **Action** → run Planner → Author → Critic pipeline

The **Planner** designs a plan (JSON), the **Author** writes, and the **Critic** validates safety & constraints (and can rewrite).

---

## ⚙️ Requirements
- **Windows**
- **Python 3.11** installed and on PATH (accessible as `python3.11`)
- Internet access (for Google Gemini API)

---

## 🔐 Environment (.env)
Create a `.env` file in project root:

```dotenv
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL_ID=gemini-2.0-flash
▶️ Quick Start (Windows)
From the project root (where backend/, frontend/, requirements.txt, and run.bat live):

bat
Copy code
run.bat install   # first time: creates venv with Python 3.11 + installs deps + launches
Next runs:

bat
Copy code
run.bat
Backend (FastAPI): http://127.0.0.1:8000

Frontend (Streamlit): http://127.0.0.1:8501

The script auto-creates a venv/ using Python 3.11 if missing.

📁 Project Layout
bash
Copy code
project-root/
│
├─ backend/
│  ├─ __init__.py
│  ├─ main.py           # FastAPI app (routes: /bootstrap/preferences, /stories/generate, /health, /health/llm)
│  ├─ schemas.py        # Pydantic v2 models (pattern= instead of regex=)
│  ├─ llm_clients.py    # Gemini client (reads .env)
│  ├─ prompts.py        # Planner/Author/Critic prompts (strict JSON schemas)
│  ├─ orchestrator.py   # Planner → (enforce constraints) → Author → Critic (+1 revision pass)
│  ├─ agents.py         # Agents (PlannerAgent, AuthorAgent, CriticAgent)
│  ├─ perception.py     # Perception layer
│  ├─ memory.py         # In-process memory (last prefs/topic per user)
│  ├─ decision.py       # Decision layer
│  └─ action.py         # Action layer (invokes orchestrator)
│
├─ frontend/
│  └─ streamlit_app.py  # UI: save preferences → generate story → show plan/critic
│
├─ requirements.txt
├─ .env
├─ run.bat
└─ README.md
🔄 Typical Flow
Open Streamlit (auto from run.bat)

Fill Preferences (location, reading level, required moral, required words, protagonist name)

Click 💾 Save Preferences (stores them in backend memory for your user)

Enter Topic and click ✨ Generate Story

Pipeline:

bash
Copy code
Planner → (Orchestrator enforces constraints in plan) → Author → Critic
     ↳ Critic can rewrite if required_words/protagonist are missing