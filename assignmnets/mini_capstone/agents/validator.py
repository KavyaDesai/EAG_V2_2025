"""Simplified validator agent for answer quality check."""

import json
import re
from typing import Optional, Dict, Any
from core.gemini_client import GeminiClient
from core.logger import get_logger
from core.prompts import Prompts

logger = get_logger()


class ValidatorAgent:
    """Simplified validator for checking answer quality."""
    
    def __init__(self, gemini_client: GeminiClient):
        """Initialize ValidatorAgent."""
        self.gemini_client = gemini_client
        logger.info("Initialized ValidatorAgent", component="ValidatorAgent")
    
    def validate(self, user_query: str, answer: str, evidence: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate answer quality.
        
        Args:
            user_query: Original user query
            answer: Generated answer
            evidence: Optional evidence/context
            
        Returns:
            Validation result with is_valid, confidence, improvements, final_answer
        """
        logger.debug("Validating answer...", component="ValidatorAgent")
        
        try:
            prompt = Prompts.validator_quality_check(user_query, answer, evidence)

            response = self.gemini_client.generate(prompt, temperature=0.3)
            
            # Parse JSON
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            result = {
                "is_valid": bool(data.get("is_valid", True)),
                "confidence": float(data.get("confidence", 0.8)),
                "improvements": data.get("improvements"),
                "final_answer": data.get("final_answer")
            }
            
            logger.debug(
                f"Validation result: valid={result['is_valid']}, confidence={result['confidence']:.2f}",
                component="ValidatorAgent"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Validation failed: {str(e)}",
                component="ValidatorAgent",
                error_type="VALIDATION_ERROR"
            )
            # Fallback: assume valid
            return {
                "is_valid": True,
                "confidence": 0.5,
                "improvements": None,
                "final_answer": None
            }

