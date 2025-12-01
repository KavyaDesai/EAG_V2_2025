"""Local RAG agent for querying documents via FAISS."""

from typing import List, Dict, Any
from core.mcp_client import MCPClient
from core.gemini_client import GeminiClient
from core.conversation import ConversationState
from core.logger import get_logger
from core.prompts import Prompts

logger = get_logger()


class LocalRAGAgent:
    """Agent for querying local documents using FAISS RAG."""
    
    def __init__(self, mcp_client: MCPClient, gemini_client: GeminiClient):
        """Initialize LocalRAGAgent."""
        self.mcp_client = mcp_client
        self.gemini_client = gemini_client
        logger.info("Initialized LocalRAGAgent", component="LocalRAGAgent")
    
    async def handle(self, query: str, state: ConversationState) -> str:
        """
        Handle RAG query.
        
        Args:
            query: User query
            state: Conversation state
            
        Returns:
            Answer based on documents
        """
        logger.info(f"Processing RAG query: {query[:100]}...", component="LocalRAGAgent")
        
        try:
            # Search documents via MCP
            chunks = await self.mcp_client.search_documents(query)
            
            if not chunks:
                logger.warning("No documents found for query", component="LocalRAGAgent")
                return "No relevant documents found for your query. Please try rephrasing or check if documents are indexed."
            
            logger.info(f"Retrieved {len(chunks)} document chunks", component="LocalRAGAgent")
            
            # Build RAG prompt
            context = "\n\n".join([f"[Chunk {i+1}]\n{chunk}" for i, chunk in enumerate(chunks[:5])])
            
            prompt = Prompts.rag_answer(context, query)

            # Generate answer using Gemini
            answer = self.gemini_client.generate(prompt, temperature=0.7)
            
            # Update state
            state.update_context(task_type="local_rag")
            
            logger.info("RAG query processed successfully", component="LocalRAGAgent")
            
            return answer
            
        except Exception as e:
            logger.error(
                f"RAG query failed: {str(e)}",
                component="LocalRAGAgent",
                error_type="RAG_ERROR"
            )
            return f"Unable to search documents. The document service may be unavailable. Please try again in a moment. Error: {str(e)}"

