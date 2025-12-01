"""Simplified planner agent for multi-step tasks."""

import json
import re
from typing import List, Dict, Any
from core.gemini_client import GeminiClient
from core.logger import get_logger
from core.prompts import Prompts

logger = get_logger()


class PlannerAgent:
    """Simplified planner for breaking down multi-step tasks."""
    
    def __init__(self, gemini_client: GeminiClient):
        """Initialize PlannerAgent."""
        self.gemini_client = gemini_client
        logger.info("Initialized PlannerAgent", component="PlannerAgent")
    
    def plan(self, query: str, task_type: str) -> List[Dict[str, Any]]:
        """
        Create execution plan for multi-step task.
        
        Args:
            query: User query
            task_type: Task type from router
            
        Returns:
            List of execution steps
        """
        logger.info(f"Creating plan for: {query[:100]}...", component="PlannerAgent")
        
        try:
            prompt = Prompts.planner_task_decomposition(query, task_type)

            response = self.gemini_client.generate(prompt, temperature=0.3)
            
            # Parse JSON - try multiple strategies
            data = None
            # Strategy 1: Try to find JSON object in response
            json_match = re.search(r'\{.*?"steps".*?\}', response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except:
                    pass
            
            # Strategy 2: Try to extract JSON from code blocks
            if not data:
                code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if code_block_match:
                    try:
                        data = json.loads(code_block_match.group(1))
                    except:
                        pass
            
            # Strategy 3: Try parsing entire response
            if not data:
                try:
                    data = json.loads(response)
                except:
                    pass
            
            # Strategy 4: Try to fix common JSON issues and parse
            if not data:
                try:
                    # Remove markdown formatting, fix trailing commas, etc.
                    cleaned = response.strip()
                    # Remove markdown code blocks
                    cleaned = re.sub(r'```[a-z]*\s*', '', cleaned)
                    cleaned = re.sub(r'```\s*', '', cleaned)
                    # Try to extract just the JSON part
                    json_start = cleaned.find('{')
                    json_end = cleaned.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        cleaned = cleaned[json_start:json_end]
                    data = json.loads(cleaned)
                except:
                    pass
            
            steps = data.get("steps", [])
            
            # Limit to 3 steps
            steps = steps[:3]
            
            logger.info(f"Created plan with {len(steps)} steps", component="PlannerAgent")
            
            return steps
            
        except Exception as e:
            logger.error(
                f"Planning failed: {str(e)}",
                component="PlannerAgent",
                error_type="PLANNING_ERROR"
            )
            # Fallback: single step
            return [{
                "step": 1,
                "agent": "GeneralQAAgent",
                "action": "Answer query",
                "input": query
            }]

