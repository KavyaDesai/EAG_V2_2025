from .schemas import CognitiveState, StoryPreferences

class DecisionLayer:
    def decide(self, state: CognitiveState) -> StoryPreferences:
        p = state.preferences
        tw = p.target_words
        # tiny heuristic based on taste
        if (p.taste or "").lower() in {"adventurous", "curious", "funny", "calm"}:
            tw = min(max(tw + 50, 150), 1200)

        return StoryPreferences(
            likes=p.likes,
            location=p.location,
            taste=p.taste,
            favorite_topics=p.favorite_topics,
            target_words=tw,
            reading_level=p.reading_level,
            avoid_themes=p.avoid_themes,
            required_moral=p.required_moral,
            required_words=p.required_words,
            protagonist_name=p.protagonist_name,
        )
