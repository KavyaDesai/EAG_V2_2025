# app/orchestrator.py
from .llm_clients import GeminiClient
from .agents import PlannerAgent, AuthorAgent, CriticAgent
from .schemas import StoryRequest, StoryResponse, Plan, AuthoredStory, Critique

class StoryGenerator:
    def __init__(self, llm: GeminiClient | None = None):
        self.llm = llm or GeminiClient()
        self.planner = PlannerAgent(self.llm)
        self.author = AuthorAgent(self.llm)
        self.critic = CriticAgent(self.llm)

    def generate(self, req: StoryRequest) -> StoryResponse:
        plan: Plan = self.planner.run(req.topic, req.preferences)
        story: AuthoredStory = self.author.run(plan, req.preferences)
        critique: Critique = self.critic.run(plan, story)

        # One revision pass if not OK and a revised version exists
        if not critique.ok and critique.revised_story:
            story = critique.revised_story
            critique = self.critic.run(plan, story)  # final check

        return StoryResponse(plan=plan, story=story, critique=critique)
