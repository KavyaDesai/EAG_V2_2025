from .schemas import PreferencesUpsert, StoryPreferences, CognitiveState

DEFAULT_AVOID = ["violence", "horror", "bullying", "romance"]

class PerceptionLayer:
    def bootstrap(self, intake: PreferencesUpsert) -> tuple[str, StoryPreferences]:
        user_id = intake.user_id
        p = intake.preferences

        # Normalize avoid_themes, required_words, protagonist_name
        avoid = list(dict.fromkeys((p.avoid_themes or []) + DEFAULT_AVOID))
        prefs = StoryPreferences(
            likes=p.likes or [],
            location=(p.location or None),
            taste=(p.taste or None),
            favorite_topics=p.favorite_topics or [],
            target_words=p.target_words or 500,
            reading_level=p.reading_level or "A2",
            avoid_themes=avoid,
            required_moral=(p.required_moral or None),
            required_words=[w.strip() for w in (p.required_words or []) if w.strip()],
            protagonist_name=(p.protagonist_name.strip() if p.protagonist_name else None),
        )
        return user_id, prefs

    def build_cognitive_state(self, user_id: str, preferences: StoryPreferences, topic: str) -> CognitiveState:
        return CognitiveState(user_id=user_id, preferences=preferences, topic=topic)
