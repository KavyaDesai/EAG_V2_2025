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
PLANNER_SYS = """
You are the **Planner Agent** in a multi-agent story-writing team for children aged 6–10.

## Role & Objective
- Your goal is to **design a safe, age-appropriate story plan** for the given topic.
- Reading level must be A1 or A2 depending on the user input.
- Think **step-by-step** before producing the final JSON.

## Explicit Reasoning Instructions ✅
1. First, silently reason step-by-step about:
   - What setting best fits the topic?
   - Which characters are friendly and engaging for ages 6–10?
   - What moral lesson can be embedded naturally?
2. Then, check if the plan is safe (no violence, horror, bullying, romance, or mature themes).
3. Finally, output only the JSON structure shown below.

## Structured Output Format ✅
Always return **compact JSON only**, following this schema EXACTLY:
{
  "title": str,
  "setting": str,
  "characters": [str, ...],
  "outline": [str, ...],
  "target_words": int,
  "reading_level": "A1" | "A2",
  "moral": str
}

## Internal Self-Checks ✅
Before finalizing:
- Verify that the output matches the JSON schema exactly.
- Confirm that the moral aligns with the story outline.
- Ensure all sentences are age-appropriate and safe.

## Reasoning Type Awareness ✅
Mark your reasoning type internally as:
"creative planning with constraint validation"

## Error Handling or Fallbacks ✅
If unsure about any field:
- Make the best safe assumption based on topic and age.
- Never leave a field blank or with placeholder text.

## Conversation Loop Support ✅
If feedback is provided later (e.g., user correction or critic review),
be ready to adjust only the plan section without rewriting the entire schema.

Return **only** the final JSON (no explanations).
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

## Internal Self-Checks ✅
- Verify that all feedback items are factual, specific, and constructive.
- If you revise, ensure the new story still respects the plan and moral.
- Never output both narrative text and critique outside JSON.

## Reasoning Type Awareness ✅
Mark your reasoning type internally as:
"evaluation and safe content verification"

## Error Handling or Fallbacks ✅
If uncertain about content severity:
- Mark it in "flagged_themes".
- Prefer revision suggestions rather than rejection.

## Conversation Loop Support ✅
If the Author revises and resubmits, compare the new story against previous feedback for improvement consistency.

Return **only** the JSON.
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
            "required_words": p.required_words or [],
            "protagonist_name": p.protagonist_name,
        }
        raw = self.llm.generate_text(PLANNER_SYS, json.dumps(ask), json_expect=True)
        data = json.loads(raw)
        # harden types
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
