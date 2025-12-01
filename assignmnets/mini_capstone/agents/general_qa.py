"""General Q&A agent (fallback)."""

from core.gemini_client import GeminiClient
from core.conversation import ConversationState
from core.logger import get_logger

logger = get_logger()


class GeneralQAAgent:
    """General Q&A agent for fallback reasoning."""
    
    def __init__(self, gemini_client: GeminiClient):
        """Initialize GeneralQAAgent."""
        self.gemini_client = gemini_client
        logger.info("Initialized GeneralQAAgent", component="GeneralQAAgent")
    
    def handle(self, query: str, state: ConversationState) -> str:
        """
        Handle general Q&A query.
        
        Args:
            query: User query
            state: Conversation state
            
        Returns:
            Answer from LLM
        """
        logger.info(f"Processing general Q&A query: {query[:100]}...", component="GeneralQAAgent")
        
        try:
            # Build prompt with conversation history
            history = state.get_formatted_history(max_messages=10)
            
            # Use chat interface
            messages = history + [{"role": "user", "content": query}]
            
            response = self.gemini_client.chat(
                messages,
                system_instruction="You are a helpful AI assistant. Provide accurate and helpful responses.",
                temperature=0.7
            )
            
            state.update_context(task_type="general")
            
            logger.info("General Q&A query processed successfully", component="GeneralQAAgent")
            
            return response
            
        except Exception as e:
            logger.error(
                f"General Q&A query failed: {str(e)}",
                component="GeneralQAAgent",
                error_type="GENERAL_QA_ERROR"
            )
            return f"Unable to process query. Please try again. Error: {str(e)}"

