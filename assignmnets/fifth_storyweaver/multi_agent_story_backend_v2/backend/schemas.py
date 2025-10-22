# app/schemas.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Request
class StoryPreferences(BaseModel):
    target_words: Optional[int] = Field(default=500, ge=150, le=1200)
    reading_level: Optional[str] = Field(default="A2")  # CEFR-ish: A1/A2
    avoid_themes: Optional[List[str]] = Field(default=["violence", "horror", "romance"])
    required_moral: Optional[str] = None
    required_words: Optional[List[str]] = None  # words to include
    protagonist_name: Optional[str] = None

class StoryRequest(BaseModel):
    topic: str = Field(..., min_length=3)
    preferences: Optional[StoryPreferences] = None

# Planner output
class Plan(BaseModel):
    title: str
    setting: str
    characters: List[str]
    outline: List[str]
    target_words: int
    reading_level: str
    moral: str

# Author output
class AuthoredStory(BaseModel):
    title: str
    story: str
    moral: str
    reading_level: str
    word_count: int

# Critic output
class Critique(BaseModel):
    ok: bool
    reasons: List[str] = []
    suggestions: List[str] = []
    flagged_themes: List[str] = []
    revised_story: Optional[AuthoredStory] = None

# Final response
class StoryResponse(BaseModel):
    plan: Plan
    story: AuthoredStory
    critique: Critique
