from .orchestrator import StoryGenerator
from .schemas import CognitiveState, StoryPreferences, StoryResponse

class ActionLayer:
    def __init__(self, generator: StoryGenerator | None = None) -> None:
        self._generator = generator or StoryGenerator()

    def run_pipeline(self, state: CognitiveState) -> StoryResponse:
        req_like = type("Req", (), {})()
        req_like.topic = state.topic
        req_like.preferences = StoryPreferences(**state.preferences.dict())
        return self._generator.generate(req_like)
