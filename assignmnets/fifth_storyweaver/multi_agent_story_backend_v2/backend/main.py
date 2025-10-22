# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import StoryRequest, StoryResponse
from .orchestrator import StoryGenerator
from .llm_clients import GeminiClient

app = FastAPI(title="Multi-Agent Story Backend", version="2.0")

# CORS: keep permissive or restrict to your frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_generator = StoryGenerator()

@app.get("/health")
def health():
    return {"status": "ok", "service": "multi-agent-story-backend"}

@app.get("/health/llm")
def health_llm():
    try:
        client = GeminiClient()
        txt = client.generate_text("You are a short echo.", "return the word OK only", json_expect=False)
        return {"llm_ok": True, "sample": txt[:100]}
    except Exception as e:
        return {"llm_ok": False, "error": str(e)}

@app.post("/stories/generate", response_model=StoryResponse)
def generate_story(req: StoryRequest):
    try:
        return _generator.generate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
