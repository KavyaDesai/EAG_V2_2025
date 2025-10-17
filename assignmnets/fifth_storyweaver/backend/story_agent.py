# backend/story_agent.py
import json
from typing import Any, Dict

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .llm_clients import GeminiClient

class StoryWeaverAgent:
    def __init__(self, model: str | None = None):
        self.llm = GeminiClient(model=model) if model else GeminiClient()

    @staticmethod
    def _coerce_json(raw: str) -> Dict[str, Any]:
        txt = raw.strip()
        if txt.startswith("```"):
            txt = txt.strip("`")
            first_nl = txt.find("\n")
            if first_nl != -1:
                txt = txt[first_nl+1:]
        return json.loads(txt)

    @staticmethod
    def _basic_validate(data: Dict[str, Any]) -> None:
        for k in ["plan", "story", "moral", "self_check", "follow_up"]:
            if k not in data:
                raise ValueError(f"Missing key: {k}")
        sc = data["self_check"]
        if not isinstance(sc.get("length_ok"), bool) or not isinstance(sc.get("moral_present"), bool):
            raise ValueError("self_check.length_ok & moral_present must be boolean")

    def generate(self, topic: str, preferences: Dict[str, Any] | None = None) -> Dict[str, Any]:
        prompt = build_user_prompt(topic, preferences or {})
        raw = self.llm.generate_json(SYSTEM_PROMPT, prompt)
        data = self._coerce_json(raw)
        self._basic_validate(data)
        return data

