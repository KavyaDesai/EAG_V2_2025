"""Router agent with enhanced heuristics for task classification."""

import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from core.gemini_client import GeminiClient
from core.conversation import ConversationState
from core.logger import get_logger
from core.prompts import Prompts

logger = get_logger()


@dataclass
class RouterDecision:
    """Router decision output."""
    task_type: str  # web_page_ops | web_search | local_rag | math | general | mixed
    confidence: float  # 0.0-1.0
    needs_planning: bool
    tool_hints: list
    reasoning: str


class RouterAgent:
    """Enhanced router with rule-based heuristics + LLM fallback."""
    
    def __init__(self, gemini_client: GeminiClient):
        """Initialize RouterAgent."""
        self.gemini_client = gemini_client
        logger.info("Initialized RouterAgent", component="RouterAgent")
    
    def route(self, query: str, state: ConversationState) -> RouterDecision:
        """
        Route query to appropriate agent.
        
        Args:
            query: User query
            state: Conversation state
            
        Returns:
            RouterDecision
        """
        logger.debug(f"Routing query: {query[:100]}...", component="RouterAgent")
        
        # Try rule-based heuristics first
        heuristic_result = self._rule_based_routing(query, state)
        
        # If confidence is high, use heuristic result
        if heuristic_result.confidence >= 0.8:
            logger.info(
                f"Route decision (heuristics): {heuristic_result.task_type} "
                f"(confidence: {heuristic_result.confidence:.2f})",
                component="RouterAgent"
            )
            return heuristic_result
        
        # Otherwise, use LLM classification
        logger.debug("Using LLM classification (heuristics uncertain)", component="RouterAgent")
        llm_result = self._llm_routing(query, state, heuristic_result)
        
        # Combine results
        final_decision = RouterDecision(
            task_type=llm_result.task_type,
            confidence=max(heuristic_result.confidence, llm_result.confidence),
            needs_planning=llm_result.needs_planning,
            tool_hints=llm_result.tool_hints,
            reasoning=f"Heuristics: {heuristic_result.reasoning}. LLM: {llm_result.reasoning}"
        )
        
        logger.info(
            f"Route decision (LLM): {final_decision.task_type} "
            f"(confidence: {final_decision.confidence:.2f})",
            component="RouterAgent"
        )
        
        return final_decision
    
    def _rule_based_routing(self, query: str, state: ConversationState) -> RouterDecision:
        """Rule-based routing using heuristics."""
        query_lower = query.lower()
        confidence = 0.0
        task_type = "general"
        reasoning = ""
        
        # URL pattern (highest priority - check first)
        url_pattern = r'https?://[^\s]+'
        has_url = bool(re.search(url_pattern, query))
        
        # Web page operations (check URL first, then keywords)
        page_keywords = ["this page", "current page", "the page", "page"]
        page_actions = ["summarize", "summarise", "count", "extract", "find", "get", "show"]
        
        if has_url:
            # URL detected - high confidence for web_page_ops
            task_type = "web_page_ops"
            confidence = 0.95
            reasoning = "Detected URL in query - web page operation"
        elif any(keyword in query_lower for keyword in page_keywords) and \
           any(action in query_lower for action in page_actions):
            task_type = "web_page_ops"
            confidence = 0.9
            reasoning = "Detected page operation keywords"
        
        # Local RAG - check BEFORE web search and math (highest priority for explicit RAG requests)
        # Explicit RAG indicators (check FIRST - highest priority)
        explicit_rag_keywords = ["rag", "rag search", "using rag", "check using rag", "use rag",
                                "search documents", "local documents", "my documents", "documents search"]
        # Document location indicators
        location_keywords = ["in my notes", "in my documents", "in the folder", "in files", "in docs", "in documents"]
        # Document-specific question patterns (facts that might be in documents)
        document_question_patterns = [
            "how much", "how many", "what did", "who paid", "when did", 
            "which file", "what document", "according to", "in the document"
        ]
        
        has_explicit_rag = any(kw in query_lower for kw in explicit_rag_keywords)
        has_location_keywords = any(kw in query_lower for kw in location_keywords)
        has_document_pattern = any(pattern in query_lower for pattern in document_question_patterns)
        
        # RAG detection - check BEFORE other classifications
        if has_explicit_rag:
            task_type = "local_rag"
            confidence = 0.95
            reasoning = "Explicit RAG request detected"
        elif has_location_keywords:
            task_type = "local_rag"
            confidence = 0.9
            reasoning = "Query references local documents/notes"
        elif has_document_pattern and not any(kw in query_lower for kw in ["search the web", "google", "find article"]):
            # Document-specific question without web search keywords
            task_type = "local_rag"
            confidence = 0.8
            reasoning = "Query asks about specific facts that might be in documents"
        elif state.last_folder and "same folder" in query_lower:
            task_type = "local_rag"
            confidence = 0.85
            reasoning = "Context suggests local RAG"
        
        # Web search (only if no URL, not RAG, not math, and not already classified)
        if task_type == "general":
            search_keywords = ["search the web", "google", "find article", "search for", "look up", "current", "latest", "today"]
            # General question patterns that suggest web search
            general_question_patterns = ["what is", "who is", "where is", "when is", "why is", "how is", 
                                        "relationship", "between", "related to", "connection"]
            
            # Don't route to web_search if RAG indicators are present
            has_rag_indicators = has_explicit_rag or has_location_keywords or has_document_pattern
            
            # Check if it's a general question that needs web search
            is_general_question = any(pattern in query_lower for pattern in general_question_patterns)
            
            if any(keyword in query_lower for keyword in search_keywords) and not has_rag_indicators:
                task_type = "web_search"
                confidence = 0.9
                reasoning = "Detected web search keywords for general/public information"
            elif is_general_question and not has_rag_indicators:
                # General questions about relationships, definitions, etc. should use web search
                task_type = "web_search"
                confidence = 0.8
                reasoning = "General question about relationships/concepts - likely needs web search"
        
        # Math/Code (only if not already classified and has STRONG math indicators)
        if task_type == "general":
            math_operators = ["+", "-", "*", "/", "^", "sqrt", "integral", "derivative", "="]
            math_keywords = ["calculate", "compute", "solve", "what is"]  # "what is" only for math if followed by numbers/expressions
            # Only classify as math if:
            # 1. Has math operators, OR
            # 2. Has math keywords AND (numbers OR math expressions), AND not a general question
            has_operators = any(op in query for op in math_operators)
            has_math_keywords = any(kw in query_lower for kw in math_keywords)
            has_numbers = any(char.isdigit() for char in query)
            is_general_question = query_lower.startswith(("what is", "who is", "where is", "when is", "why is", "how is"))
            
            # Don't classify as math if:
            # - It's a general "what is" question about relationships/concepts (not math)
            # - It has no numbers and no operators
            # - It's asking about relationships, definitions, or concepts
            relationship_keywords = ["relationship", "between", "related", "connection", "difference", "similarity"]
            has_relationship_context = any(kw in query_lower for kw in relationship_keywords)
            
            if has_operators:
                task_type = "math"
                confidence = 0.9
                reasoning = "Detected math operators"
            elif has_math_keywords and has_numbers and not is_general_question and not has_relationship_context:
                task_type = "math"
                confidence = 0.85
                reasoning = "Detected math keywords with numbers"
            elif has_math_keywords and has_operators:
                task_type = "math"
                confidence = 0.9
                reasoning = "Detected math keywords with operators"
        
        # Check for multi-step
        needs_planning = self._detect_multi_step(query_lower)
        tool_hints = []
        if needs_planning:
            if "search" in query_lower and "summarize" in query_lower:
                tool_hints = ["web_search", "web_page"]
            elif "search" in query_lower and "in" in query_lower:
                tool_hints = ["web_search", "local_rag"]
        
        return RouterDecision(
            task_type=task_type,
            confidence=confidence,
            needs_planning=needs_planning,
            tool_hints=tool_hints,
            reasoning=reasoning or "No strong heuristic match"
        )
    
    def _detect_multi_step(self, query_lower: str) -> bool:
        """Detect if query requires multiple steps."""
        step_indicators = ["then", "and then", "after", "next", "also", "and"]
        action_verbs = ["search", "find", "get", "extract", "summarize", "count"]
        
        step_count = sum(1 for indicator in step_indicators if indicator in query_lower)
        action_count = sum(1 for verb in action_verbs if verb in query_lower)
        
        return step_count >= 1 or action_count >= 2
    
    def _llm_routing(self, query: str, state: ConversationState, 
                    heuristic_result: RouterDecision) -> RouterDecision:
        """LLM-based routing when heuristics are uncertain."""
        try:
            context_summary = state.get_context_summary()
            
            prompt = Prompts.router_classification(
                query,
                context_summary,
                {
                    "task_type": heuristic_result.task_type,
                    "confidence": heuristic_result.confidence
                }
            )

            response = self.gemini_client.generate(prompt, temperature=0.3)
            
            # Parse JSON response
            import json
            # Extract JSON from response (might have markdown code blocks)
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Fallback: try to parse entire response
                data = json.loads(response)
            
            return RouterDecision(
                task_type=data.get("task_type", "general"),
                confidence=float(data.get("confidence", 0.5)),
                needs_planning=bool(data.get("needs_planning", False)),
                tool_hints=data.get("tool_hints", []),
                reasoning=data.get("reasoning", "LLM classification")
            )
            
        except Exception as e:
            logger.error(
                f"LLM routing failed: {str(e)}",
                component="RouterAgent",
                error_type="LLM_ROUTING_ERROR"
            )
            # Fallback to heuristic result
            return heuristic_result

