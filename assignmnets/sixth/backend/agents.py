# app/agents.py
import json
from typing import Dict, Any
from .llm_clients import GeminiClient
from .schemas import Plan, AuthoredStory, Critique, StoryPreferences

# # ---------- SYSTEM PROMPTS ----------
# PLANNER_SYS = """You are the Planner in a kid-safe multi-agent writing team.
# Audience: children aged 6–10. Reading level A1–A2. Keep concepts simple, warm, and positive.
# Never include violence, horror, bullying, romance, or mature themes.
# ALWAYS return compact JSON only, matching this schema EXACTLY:
# {
#   "title": str,
#   "setting": str,
#   "characters": [str, ...],
#   "outline": [str, ...],
#   "target_words": int,
#   "reading_level": "A1" | "A2",
#   "moral": str
# }
# """

# AUTHOR_SYS = """You are the Author in a kid-safe multi-agent writing team.
# Audience: children aged 6–10. Use simple vocabulary, short paragraphs, friendly tone.
# Do not include violence, horror, bullying, romance, or scary content.
# Write from the provided plan. Keep continuity of characters and setting.
# ALWAYS return JSON ONLY in this schema:
# {
#   "title": str,
#   "story": str,
#   "moral": str,
#   "reading_level": "A1" | "A2",
#   "word_count": int
# }
# """

# CRITIC_SYS = """You are the Critic in a kid-safe multi-agent writing team.
# Your job: check age-appropriateness (6–10), safety (no violence/horror/bullying/romance), clarity, and alignment with plan and moral.
# If issues exist, propose specific, actionable edits. You MAY provide a fully revised story (same schema as Author).
# ALWAYS return JSON ONLY in this schema:
# {
#   "ok": bool,
#   "reasons": [str, ...],
#   "suggestions": [str, ...],
#   "flagged_themes": [str, ...],
#   "revised_story": null | {
#     "title": str, "story": str, "moral": str, "reading_level": "A1" | "A2", "word_count": int
#   }
# }
# """

# ---------- SYSTEM PROMPTS ----------
PLANNER_SYS = """You are the **Planner Agent** in a kid-safe multi-agent writing team for ages 6–10.

## Role & Objective
Design a safe, age-appropriate, A1–A2 reading-level plan for the given topic and constraints.

## Constraints to Honor
- Prohibited themes: violence, horror, bullying, romance, mature content.
- If a **protagonist_name** is provided in constraints, include that name in the **characters** list and make it the main character.
- If **required_words** are provided in constraints, **weave ALL of them naturally into the plan**:
  - Prefer using them in **setting** and **outline** bullet points (not as a raw list).
  - Do NOT keyword-stuff; integrate them contextually.

## Output Format (JSON ONLY)
Return compact JSON exactly in this schema:
{
  "title": str,
  "setting": str,
  "characters": [str, ...],
  "outline": [str, ...],
  "target_words": int,
  "reading_level": "A1" | "A2",
  "moral": str
}

## Internal Self-Checks (silent)
- Verify the schema matches exactly.
- If constraints.protagonist_name exists, ensure it is present in 'characters'.
- If constraints.required_words exists, ensure each word appears in 'setting' or at least one 'outline' item, case-insensitive and naturally.
- Keep content safe and warm for ages 6–10.

Return ONLY the JSON.
"""


AUTHOR_SYS = """
You are the **Author Agent** in a kid-safe multi-agent storywriting system.

## Role & Objective
- Your task: Write a complete, engaging, and safe story **based on the given plan**.
- Maintain consistency with the plan's setting, characters, and moral.

## Explicit Reasoning Instructions ✅
1. Think step-by-step:
   - Follow the outline sequence logically.
   - Maintain simple A1–A2 sentence structures.
   - Keep vocabulary friendly, age-appropriate, and positive.
2. Validate coherence and safety after writing.

## Structured Output Format ✅
Always return **JSON ONLY**, in this exact schema:
{
  "title": str,
  "story": str,
  "moral": str,
  "reading_level": "A1" | "A2",
  "word_count": int
}

## Internal Self-Checks ✅
- Ensure every outline item is reflected in the story.
- Count approximate words and verify `word_count` matches.
- Double-check that the moral appears explicitly or implicitly in the story.

## Reasoning Type Awareness ✅
Mark your reasoning type internally as:
"narrative generation with coherence and safety validation"

## Error Handling or Fallbacks ✅
If something in the plan seems unclear:
- Fill it with a creative but safe detail consistent with age level.
- Never break format or introduce forbidden themes.

## Conversation Loop Support ✅
If the Critic later requests edits, you may rewrite specific paragraphs while keeping the schema intact.

Return only the JSON output.
"""


CRITIC_SYS = """
You are the **Critic Agent** in a kid-safe multi-agent storywriting team.

## Role & Objective
- Review the story for clarity, safety, and moral alignment.
- Detect inappropriate or advanced content.
- Suggest precise, actionable edits if needed.

## Explicit Reasoning Instructions ✅
1. Think step-by-step:
   - Check for forbidden content (violence, bullying, romance, etc.).
   - Compare story vs. plan: are setting, characters, and moral consistent?
   - Assess reading level: does it match A1–A2?
2. Decide if the story is acceptable or needs revision.

## Structured Output Format ✅
Always return JSON ONLY in this schema:
{
  "ok": bool,
  "reasons": [str, ...],
  "suggestions": [str, ...],
  "flagged_themes": [str, ...],
  "revised_story": null | {
    "title": str,
    "story": str,
    "moral": str,
    "reading_level": "A1" | "A2",
    "word_count": int
  }
}
"""


# ---------- AGENTS ----------
class PlannerAgent:
    def __init__(self, llm: GeminiClient):
        self.llm = llm

    def run(self, topic: str, prefs: StoryPreferences | None) -> Plan:
        p = prefs or StoryPreferences()
        ask = {
            "topic": topic,
            "target_words": p.target_words,
            "reading_level": p.reading_level or "A2",
            "avoid_themes": p.avoid_themes or [],
            "required_moral": p.required_moral,
            # NEW: pass constraints to planner so it can include them in plan
            "constraints": {
                "required_words": p.required_words or [],
                "protagonist_name": p.protagonist_name,
            }
        }
        raw = self.llm.generate_text(PLANNER_SYS, json.dumps(ask), json_expect=True)
        data = json.loads(raw)
        return Plan(
            title=str(data["title"]).strip(),
            setting=str(data["setting"]).strip(),
            characters=[str(x).strip() for x in data["characters"]],
            outline=[str(x).strip() for x in data["outline"]],
            target_words=int(data["target_words"]),
            reading_level=str(data["reading_level"]),
            moral=str(data["moral"]).strip(),
        )


class AuthorAgent:
    def __init__(self, llm: GeminiClient):
        self.llm = llm

    def run(self, plan: Plan, prefs: StoryPreferences | None) -> AuthoredStory:
        ask = {
            "plan": plan.dict(),
            "constraints": {
                "likes": (prefs.likes if prefs else None),
                "favorite_topics": (prefs.favorite_topics if prefs else None),
                "required_words": (prefs.required_words if prefs else None),
                "protagonist_name": (prefs.protagonist_name if prefs else None),
            },
        }
        raw = self.llm.generate_text(AUTHOR_SYS, json.dumps(ask), json_expect=True)
        data = json.loads(raw)
        return AuthoredStory(
            title=str(data["title"]).strip(),
            story=str(data["story"]).strip(),
            moral=str(data["moral"]).strip(),
            reading_level=str(data["reading_level"]),
            word_count=int(data["word_count"]),
        )

class CriticAgent:
    def __init__(self, llm: GeminiClient):
        self.llm = llm

    def run(self, plan: Plan, story: AuthoredStory) -> Critique:
        ask = {"plan": plan.dict(), "story": story.dict()}
        raw = self.llm.generate_text(CRITIC_SYS, json.dumps(ask), json_expect=True)
        data = json.loads(raw)
        revised = None
        if data.get("revised_story"):
            rs = data["revised_story"]
            revised = AuthoredStory(
                title=str(rs["title"]).strip(),
                story=str(rs["story"]).strip(),
                moral=str(rs["moral"]).strip(),
                reading_level=str(rs["reading_level"]),
                word_count=int(rs["word_count"]),
            )
        return Critique(
            ok=bool(data["ok"]),
            reasons=[str(x) for x in data.get("reasons", [])],
            suggestions=[str(x) for x in data.get("suggestions", [])],
            flagged_themes=[str(x) for x in data.get("flagged_themes", [])],
            revised_story=revised,
        )
