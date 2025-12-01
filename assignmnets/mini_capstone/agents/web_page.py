"""Web page operations agent."""

import re
from typing import Optional
from core.mcp_client import MCPClient
from core.gemini_client import GeminiClient
from core.code_agent import CodeAgent
from core.conversation import ConversationState
from core.logger import get_logger
from core.prompts import Prompts

logger = get_logger()


class WebPageAgent:
    """Agent for web page operations (summarize, count words, extract URLs)."""
    
    def __init__(self, mcp_client: MCPClient, gemini_client: GeminiClient, code_agent: CodeAgent):
        """Initialize WebPageAgent."""
        self.mcp_client = mcp_client
        self.gemini_client = gemini_client
        self.code_agent = code_agent
        logger.info("Initialized WebPageAgent", component="WebPageAgent")
    
    async def handle(self, query: str, state: ConversationState) -> str:
        """
        Handle web page operation.
        
        Args:
            query: User query
            state: Conversation state
            
        Returns:
            Operation result
        """
        logger.info(f"Processing web page query: {query[:100]}...", component="WebPageAgent")
        
        try:
            # Extract URL from query or use last URL
            url = self._extract_url(query) or state.last_url
            
            if not url:
                return "No URL provided. Please specify a URL or provide one in your query."
            
            # Determine operation type
            query_lower = query.lower()
            
            if "summarize" in query_lower or "summarise" in query_lower:
                return await self._summarize_page(url, query, state)
            elif "count" in query_lower:
                return await self._count_words(url, query, state)
            elif "extract" in query_lower and "url" in query_lower:
                return await self._extract_urls(url, query, state)
            else:
                # Default to summarize
                return await self._summarize_page(url, query, state)
                
        except Exception as e:
            logger.error(
                f"Web page operation failed: {str(e)}",
                component="WebPageAgent",
                error_type="WEBPAGE_ERROR"
            )
            return f"Unable to process web page. Please check the URL and try again. Error: {str(e)}"
    
    def _extract_url(self, query: str) -> Optional[str]:
        """Extract URL from query."""
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, query)
        return match.group(0) if match else None
    
    async def _summarize_page(self, url: str, query: str, state: ConversationState) -> str:
        """Summarize a web page."""
        logger.debug(f"Summarizing page: {url}", component="WebPageAgent")
        
        try:
            # Fetch page via MCP
            markdown = await self.mcp_client.convert_webpage(url)
        except Exception as e:
            logger.error(
                f"Failed to fetch webpage: {str(e)}",
                component="WebPageAgent",
                error_type="WEBPAGE_FETCH_ERROR"
            )
            # Fallback: try using requests directly
            try:
                import requests
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                # Use trafilatura if available
                try:
                    import trafilatura
                    markdown = trafilatura.extract(
                        response.text,
                        include_comments=False,
                        include_tables=True,
                        output_format='markdown'
                    ) or response.text[:5000]  # Fallback to first 5000 chars
                except:
                    markdown = response.text[:5000]
                logger.info("Used fallback method to fetch webpage", component="WebPageAgent")
            except Exception as e2:
                return f"Unable to fetch the webpage. Error: {str(e)}. Fallback also failed: {str(e2)}"
        
        # Generate summary
        prompt = Prompts.webpage_summarize(markdown, query)
        
        summary = self.gemini_client.generate(prompt, temperature=0.7)
        
        state.update_context(task_type="web_page_ops", url=url)
        
        return f"Summary of {url}:\n\n{summary}"
    
    async def _count_words(self, url: str, query: str, state: ConversationState) -> str:
        """Count word occurrences on a page."""
        logger.debug(f"Counting words on page: {url}", component="WebPageAgent")
        
        # Fetch page via MCP
        markdown = await self.mcp_client.convert_webpage(url)
        
        # Extract word to count from query
        word_match = re.search(r"['\"]([^'\"]+)['\"]", query)
        if not word_match:
            # Try to find word after "count" or "times"
            words = query.lower().split()
            try:
                count_idx = words.index("count") if "count" in words else words.index("times")
                if count_idx + 1 < len(words):
                    word = words[count_idx + 1].strip(".,!?")
                else:
                    return "Please specify which word to count. Example: 'How many times is 'transformer' repeated?'"
            except:
                return "Please specify which word to count. Example: 'How many times is 'transformer' repeated?'"
        else:
            word = word_match.group(1)
        
        # Count using code agent
        code = f"""
import re
text = '''{markdown}'''
word = '{word}'
# Case-insensitive count
count = len(re.findall(r'\\b{re.escape(word)}\\b', text, re.IGNORECASE))
result = count
print(f"The word '{{word}}' appears {{count}} times.")
"""
        
        result = self.code_agent.execute(code)
        
        if result["success"]:
            output = result.get("output", "").strip()
            count = result.get("result", 0)
            
            state.update_context(task_type="web_page_ops", url=url)
            
            return f"On the page {url}:\n{output}\n\nCount: {count}"
        else:
            return f"Unable to count words: {result.get('error', 'Unknown error')}"
    
    async def _extract_urls(self, url: str, query: str, state: ConversationState) -> str:
        """Extract URLs from a page, optionally filtered by topic."""
        logger.debug(f"Extracting URLs from page: {url}", component="WebPageAgent")
        
        # Fetch page via MCP
        markdown = await self.mcp_client.convert_webpage(url)
        
        # Extract topic filter from query
        topic = None
        if "related to" in query.lower():
            topic_match = re.search(r"related to ['\"]([^'\"]+)['\"]", query, re.IGNORECASE)
            if topic_match:
                topic = topic_match.group(1)
        
        # Extract URLs using code agent
        code = f"""
import re
text = '''{markdown}'''
# Extract URLs
url_pattern = r'https?://[^\\s\\)]+'
urls = re.findall(url_pattern, text)
# Remove duplicates
urls = list(set(urls))
result = urls
print(f"Found {{len(urls)}} URLs")
"""
        
        result = self.code_agent.execute(code)
        
        if result["success"]:
            urls = result.get("result", [])
            
            # Filter by topic if specified
            if topic:
                # Use Gemini to filter URLs
                prompt = Prompts.url_filter(urls, topic)
                
                filtered_response = self.gemini_client.generate(prompt, temperature=0.3)
                # Parse JSON response
                import json
                try:
                    filtered_urls = json.loads(filtered_response)
                    urls = filtered_urls if isinstance(filtered_urls, list) else urls
                except:
                    pass
            
            state.update_context(task_type="web_page_ops", url=url)
            
            url_list = "\n".join([f"- {u}" for u in urls[:20]])
            return f"URLs found on {url}:\n\n{url_list}"
        else:
            return f"Unable to extract URLs: {result.get('error', 'Unknown error')}"

