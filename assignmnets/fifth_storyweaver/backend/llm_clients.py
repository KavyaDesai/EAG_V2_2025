# backend/llm_client.py
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")

class GeminiClient:
    """
    Supports either:
      - google-genai (new SDK: from google import genai)
      - google-generativeai (older SDK: import google.generativeai as genai)

    We pick what's installed, so your classroom/dev machines won't break.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise EnvironmentError("GEMINI_API_KEY missing. Put it in your .env.")

        self.provider = None
        self.client = None

        # Try new SDK first
        try:
            from google import genai  # type: ignore
            self.provider = "genai"
            self.client = genai.Client(api_key=self.api_key)
        except Exception:
            # Fallback to older SDK
            import google.generativeai as genai  # type: ignore
            self.provider = "generativeai"
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "genai":
            # New SDK style
            resp = self.client.models.generate_content(
                model=self.model,
                contents=[{
                    "role": "user",
                    "parts": [{"text": system_prompt.strip() + "\n\n" + user_prompt.strip()}],
                }],
                config={"temperature": 0.2, "top_p": 0.9},
            )
            return resp.text
        else:
            # Older SDK style
            text = system_prompt.strip() + "\n\n" + user_prompt.strip()
            resp = self.client.generate_content(text)
            return resp.text
