from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    PreferencesUpsert, StoryRequest, StoryResponse,
    CognitiveState, StoryPreferences
)
from .perception import PerceptionLayer
from .memory import MemoryLayer
from .decision import DecisionLayer
from .action import ActionLayer
from .llm_clients import GeminiClient

app = FastAPI(title="Cognitive-Layered Story Agent", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_perception = PerceptionLayer()
_memory = MemoryLayer()
_decision = DecisionLayer()
_action = ActionLayer()

@app.get("/health")
def health():
    return {"status": "ok", "service": "cognitive-story-agent"}

@app.get("/health/llm")
def health_llm():
    try:
        client = GeminiClient()
        txt = client.generate_text("You are health probe.", "Return OK only.", json_expect=False)
        return {"llm_ok": txt.strip()[:10] == "OK", "sample": txt.strip()[:50]}
    except Exception as e:
        return {"llm_ok": False, "error": str(e)}

# 1) Save preferences BEFORE generation
@app.post("/bootstrap/preferences")
def bootstrap_preferences(payload: PreferencesUpsert):
    user_id, prefs = _perception.bootstrap(payload)
    _memory.upsert(user_id=user_id, prefs=prefs, last_topic=None)
    return {"ok": True, "message": "Preferences saved", "user_id": user_id, "preferences": prefs.dict()}

# 2) Generate story (requires saved preferences)
@app.post("/stories/generate", response_model=StoryResponse)
def generate_story(req: StoryRequest):
    rec = _memory.get(req.user_id)
    if not rec:
        raise HTTPException(400, "No preferences found for this user. Call /bootstrap/preferences first.")

    state = _perception.build_cognitive_state(req.user_id, rec.last_preferences, req.topic)
    decided_prefs = _decision.decide(state)
    state.preferences = decided_prefs

    out = _action.run_pipeline(state)
    _memory.upsert(user_id=req.user_id, prefs=decided_prefs, last_topic=req.topic)
    return out
