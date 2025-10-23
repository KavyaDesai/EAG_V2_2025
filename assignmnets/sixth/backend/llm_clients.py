# app/llm_clients.py
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

def _extract_text(resp: Any) -> str:
    if hasattr(resp, "text") and isinstance(resp.text, str) and resp.text.strip():
        return resp.text
    try:
        candidates = getattr(resp, "candidates", []) or []
        if candidates:
            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None)
            if parts:
                texts = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if isinstance(t, str) and t.strip():
                        texts.append(t)
                if texts:
                    return "\n".join(texts)
    except Exception:
        pass
    return str(resp)

class GeminiClient:
    def __init__(self, model: str | None = None):
        try:
            import google.generativeai as genai
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "google-generativeai is not installed. Run: pip install google-generativeai"
            ) from e

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or not api_key.strip():
            raise RuntimeError("GEMINI_API_KEY is missing/empty in .env")

        genai.configure(api_key=api_key.strip())
        self._genai = genai
        self.model_name = (model or os.getenv("GEMINI_MODEL_ID") or "gemini-2.0-flash").strip()
        self._model = genai.GenerativeModel(model_name=self.model_name)

    def generate_text(self, system_prompt: str, user_prompt: str, json_expect: bool = False) -> str:
        configured = self._genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.9,
        }
        # Only set this if SDK version supports it
        if json_expect:
            try:
                generation_config["response_mime_type"] = "application/json"
            except Exception:
                pass

        resp = configured.generate_content(
            user_prompt,
            generation_config=generation_config,
        )
        return _extract_text(resp)
