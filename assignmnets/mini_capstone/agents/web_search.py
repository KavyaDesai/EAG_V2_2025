"""Web search agent using DuckDuckGo."""

from typing import List, Dict, Any
from core.code_agent import CodeAgent
from core.gemini_client import GeminiClient
from agents.web_page import WebPageAgent
from core.conversation import ConversationState
from core.logger import get_logger

logger = get_logger()


class WebSearchAgent:
    """Agent for web search operations."""
    
    def __init__(self, code_agent: CodeAgent, gemini_client: GeminiClient, 
                 web_page_agent: WebPageAgent):
        """Initialize WebSearchAgent."""
        self.code_agent = code_agent
        self.gemini_client = gemini_client
        self.web_page_agent = web_page_agent
        logger.info("Initialized WebSearchAgent", component="WebSearchAgent")
    
    async def handle(self, query: str, state: ConversationState) -> str:
        """
        Handle web search query.
        
        Args:
            query: User query
            state: Conversation state
            
        Returns:
            Search results or processed content
        """
        logger.info(f"Processing web search query: {query[:100]}...", component="WebSearchAgent")
        
        try:
            # Extract search query
            search_query = self._extract_search_query(query)
            
            # Generate search code (DDGS is already imported in namespace)
            code = f"""
# DDGS is already available in the namespace
search_query = '{search_query}'
ddgs = DDGS()
results = list(ddgs.text(search_query, max_results=5))

# Format results
formatted_results = []
for r in results:
    formatted_results.append({{
        'title': r.get('title', ''),
        'url': r.get('href', ''),
        'snippet': r.get('body', '')
    }})

result = formatted_results
print(f"Found {{len(formatted_results)}} results")
"""
            
            # Execute search
            result = self.code_agent.execute(code)
            
            if not result["success"]:
                logger.error(
                    f"Web search failed: {result.get('error')}",
                    component="WebSearchAgent",
                    error_type="SEARCH_ERROR"
                )
                return f"Web search failed: {result.get('error', 'Unknown error')}"
            
            search_results = result.get("result", [])
            
            # Check if result is a list
            if not isinstance(search_results, list):
                # Try to get from output
                output = result.get("output", "")
                if "Found" in output and "results" in output:
                    # Results might be in output but not captured in result variable
                    logger.warning("Search executed but results format unexpected", component="WebSearchAgent")
                    return f"Search executed but no results returned. Output: {output[:200]}"
                return "No search results found. Please try a different query."
            
            if not search_results or len(search_results) == 0:
                return "No search results found. Please try a different query."
            
            logger.info(f"Found {len(search_results)} search results", component="WebSearchAgent")
            
            # Check if user wants summarization
            query_lower = query.lower()
            if "summarize" in query_lower or "summarise" in query_lower:
                # Summarize top results
                summaries = []
                for i, res in enumerate(search_results[:3], 1):
                    try:
                        summary = await self.web_page_agent._summarize_page(
                            res.get("url", ""),
                            f"Summarize: {res.get('title', '')}",
                            state
                        )
                        summaries.append(f"\n{i}. {res.get('title', 'No title')}\n{summary}")
                    except Exception as e:
                        logger.warning(f"Failed to summarize {res.get('url')}: {e}", component="WebSearchAgent")
                        summaries.append(f"\n{i}. {res.get('title', 'No title')}\n{res.get('snippet', 'No snippet')}")
                
                state.update_context(task_type="web_search", search_query=search_query)
                return f"Search results for '{search_query}':\n" + "\n".join(summaries)
            else:
                # Return search results
                formatted = []
                for i, res in enumerate(search_results, 1):
                    formatted.append(
                        f"{i}. {res.get('title', 'No title')}\n"
                        f"   URL: {res.get('url', 'No URL')}\n"
                        f"   {res.get('snippet', 'No snippet')[:200]}..."
                    )
                
                state.update_context(task_type="web_search", search_query=search_query)
                return f"Search results for '{search_query}':\n\n" + "\n\n".join(formatted)
                
        except Exception as e:
            logger.error(
                f"Web search query failed: {str(e)}",
                component="WebSearchAgent",
                error_type="WEB_SEARCH_ERROR"
            )
            return f"Unable to perform web search. Please try again. Error: {str(e)}"
    
    def _extract_search_query(self, query: str) -> str:
        """Extract search query from user input."""
        # Remove common prefixes
        prefixes = ["search the web for", "search for", "google", "find", "look up"]
        query_lower = query.lower()
        
        for prefix in prefixes:
            if query_lower.startswith(prefix):
                return query[len(prefix):].strip()
        
        return query.strip()

