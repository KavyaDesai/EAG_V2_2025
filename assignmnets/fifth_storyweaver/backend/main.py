# backend/main.py


import uvicorn
import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from .story_agent import StoryWeaverAgent

load_dotenv()

app = FastAPI(title="StoryWeaver API", version="1.0.0")

# Allow Streamlit (localhost) by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Preferences(BaseModel):
    child_name: Optional[str] = None
    favorite_animal: Optional[str] = None
    favorite_setting: Optional[str] = None
    tone: Optional[str] = None  # e.g., "funny", "adventurous"

class GenerateRequest(BaseModel):
    topic: str
    preferences: Optional[Preferences] = None
    model: Optional[str] = None  # if you want to switch to gemini-2.5-flash, etc.

@app.post("/generate")
def generate_story(req: GenerateRequest):
    try:
        agent = StoryWeaverAgent(model=req.model)
        prefs = req.preferences.model_dump() if req.preferences else {}
        data = agent.generate(req.topic, preferences=prefs)
        return {"ok": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
def health():
    return {"ok": True}


# === Local runner ===
def main():
    """Run FastAPI locally with uvicorn."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )


if __name__ == "__main__":
    main()