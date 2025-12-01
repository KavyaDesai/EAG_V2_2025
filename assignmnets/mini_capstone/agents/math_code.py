"""Math and code execution agent."""

from typing import Dict, Any
from core.code_agent import CodeAgent
from core.gemini_client import GeminiClient
from core.conversation import ConversationState
from core.logger import get_logger
from core.prompts import Prompts

logger = get_logger()


class MathAndCodeAgent:
    """Agent for mathematical calculations and code execution."""
    
    def __init__(self, code_agent: CodeAgent, gemini_client: GeminiClient):
        """Initialize MathAndCodeAgent."""
        self.code_agent = code_agent
        self.gemini_client = gemini_client
        logger.info("Initialized MathAndCodeAgent", component="MathAndCodeAgent")
    
    def handle(self, query: str, state: ConversationState) -> str:
        """
        Handle math/code query.
        
        Args:
            query: User query
            state: Conversation state
            
        Returns:
            Calculation result or explanation
        """
        logger.info(f"Processing math/code query: {query[:100]}...", component="MathAndCodeAgent")
        
        try:
            # Generate code using Gemini
            code_prompt = Prompts.code_generation(query)

            generated_code = self.gemini_client.generate(code_prompt, temperature=0.3)
            
            # Clean code (remove markdown code blocks if present)
            import re
            code_match = re.search(r'```python\n(.*?)\n```', generated_code, re.DOTALL)
            if code_match:
                code = code_match.group(1)
            else:
                code_match = re.search(r'```\n(.*?)\n```', generated_code, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                else:
                    code = generated_code.strip()
            
            logger.debug(f"Generated code: {code[:200]}...", component="MathAndCodeAgent")
            
            # Execute code
            result = self.code_agent.execute(code)
            
            if result["success"]:
                # Format output
                output = result.get("output", "").strip()
                calculated_result = result.get("result")
                
                if calculated_result is not None:
                    response = f"Result: {calculated_result}"
                    if output:
                        response += f"\n\nOutput:\n{output}"
                elif output:
                    response = output
                else:
                    response = "Code executed successfully, but no result was returned."
                
                # Update state
                state.update_context(task_type="math")
                
                logger.info("Math/code query processed successfully", component="MathAndCodeAgent")
                
                return response
            else:
                error = result.get("error", "Unknown error")
                logger.error(
                    f"Code execution failed: {error}",
                    component="MathAndCodeAgent",
                    error_type="CODE_EXECUTION_ERROR"
                )
                return f"Calculation failed: {error}"
                
        except Exception as e:
            logger.error(
                f"Math/code query failed: {str(e)}",
                component="MathAndCodeAgent",
                error_type="MATH_CODE_ERROR"
            )
            return f"Unable to process calculation. Please try rephrasing your query. Error: {str(e)}"

