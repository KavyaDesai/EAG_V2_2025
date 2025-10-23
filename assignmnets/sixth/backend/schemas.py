from typing import List, Optional
from pydantic import BaseModel, Field

# ---------- Unified preferences (profile merged here) ----------
class StoryPreferences(BaseModel):
    # Long-term taste/context (formerly UserProfile)
    likes: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    taste: Optional[str] = None          # e.g., "adventurous", "curious", "calm", "funny"
    favorite_topics: List[str] = Field(default_factory=list)

    # Task-level knobs
    target_words: int = Field(default=500, ge=150, le=1200)
    reading_level: str = Field(default="A2", pattern="^(A1|A2)$")  # pydantic v2 uses 'pattern'
    avoid_themes: List[str] = Field(default_factory=lambda: ["violence", "horror", "bullying", "romance"])
    required_moral: Optional[str] = None
    required_words: List[str] = Field(default_factory=list)
    protagonist_name: Optional[str] = None

# Request to save preferences for a user BEFORE generation
class PreferencesUpsert(BaseModel):
    user_id: str = Field(..., min_length=1)
    preferences: StoryPreferences

# Request to generate a story (after preferences saved)
class StoryRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=3)

# Internal state carried across layers
class CognitiveState(BaseModel):
    user_id: str
    preferences: StoryPreferences
    topic: str

# Agent outputs
class Plan(BaseModel):
    title: str
    setting: str
    characters: List[str]
    outline: List[str]
    target_words: int
    reading_level: str
    moral: str

class AuthoredStory(BaseModel):
    title: str
    story: str
    moral: str
    reading_level: str
    word_count: int

class Critique(BaseModel):
    ok: bool
    reasons: List[str] = []
    suggestions: List[str] = []
    flagged_themes: List[str] = []
    revised_story: Optional[AuthoredStory] = None

class StoryResponse(BaseModel):
    plan: Plan
    story: AuthoredStory
    critique: Critique

# Memory record
class MemoryRecord(BaseModel):
    last_preferences: StoryPreferences
    last_topic: Optional[str] = None
