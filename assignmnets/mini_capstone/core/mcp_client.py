"""MCP client wrapper for interacting with MCP servers."""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from mcp_servers.multiMCP import MultiMCP
from core.logger import get_logger

logger = get_logger()


class MCPClient:
    """Wrapper for MCP client operations."""
    
    def __init__(self, mcp_server_path: Optional[str] = None):
        """
        Initialize MCP client.
        
        Args:
            mcp_server_path: Path to MCP server script (default: mcp_servers/mcp_server_2.py)
        """
        self.mcp_server_path = mcp_server_path or "mcp_servers/mcp_server_2.py"
        self.working_dir = Path(self.mcp_server_path).parent
        self.mcp_client: Optional[MultiMCP] = None
        self.initialized = False
        
        logger.info(f"Initialized MCP client for server: {self.mcp_server_path}", component="MCPClient")
    
    async def initialize(self):
        """Initialize MCP client and connect to server."""
        if self.initialized:
            return
        
        try:
            logger.info("Initializing MCP client...", component="MCPClient")
            
            server_configs = [
                {
                    "id": "rag_server",
                    "script": str(self.mcp_server_path),
                    "cwd": str(self.working_dir)
                }
            ]
            
            self.mcp_client = MultiMCP(server_configs)
            await self.mcp_client.initialize()
            self.initialized = True
            
            # List available tools for debugging
            try:
                tools = await self.list_tools()
                if len(tools) == 0:
                    logger.warning(
                        "MCP client initialized but found 0 tools. Server may not be exposing tools properly.",
                        component="MCPClient",
                        error_type="NO_TOOLS_FOUND"
                    )
                else:
                    logger.info(f"MCP client initialized with {len(tools)} tools: {tools}", component="MCPClient")
            except Exception as e:
                logger.warning(f"Could not list MCP tools: {str(e)}", component="MCPClient")
            
        except Exception as e:
            logger.error(
                f"Failed to initialize MCP client: {str(e)}",
                component="MCPClient",
                error_type="INITIALIZATION_ERROR"
            )
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            logger.log_tool_call(tool_name, arguments, "MCPClient")
            start_time = asyncio.get_event_loop().time()
            
            result = await self.mcp_client.call_tool(tool_name, arguments)
            
            duration = asyncio.get_event_loop().time() - start_time
            logger.log_execution_time(f"call_tool:{tool_name}", duration, "MCPClient")
            
            return result
            
        except Exception as e:
            error_type = "TOOL_ERROR"
            if "not found" in str(e).lower():
                error_type = "TOOL_NOT_FOUND"
            elif "timeout" in str(e).lower():
                error_type = "TIMEOUT"
            
            logger.error(
                f"MCP tool call failed: {tool_name} - {str(e)}",
                component="MCPClient",
                error_type=error_type,
                tool_name=tool_name
            )
            raise
    
    async def search_documents(self, query: str) -> List[str]:
        """
        Search documents using RAG.
        
        Args:
            query: Search query
            
        Returns:
            List of relevant document chunks
        """
        try:
            result = await self.call_tool(
                "search_stored_documents_rag",
                {"input": {"query": query}}
            )
            
            # Extract text content from MCP result
            if hasattr(result, 'content'):
                chunks = []
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        chunks.append(content_item.text)
                    elif isinstance(content_item, str):
                        chunks.append(content_item)
                return chunks
            elif isinstance(result, list):
                return result
            else:
                return [str(result)]
                
        except Exception as e:
            logger.error(
                f"Document search failed: {str(e)}",
                component="MCPClient",
                error_type="SEARCH_ERROR"
            )
            raise
    
    async def convert_webpage(self, url: str) -> str:
        """
        Convert webpage to markdown.
        
        Args:
            url: Webpage URL
            
        Returns:
            Markdown content
        """
        try:
            result = await self.call_tool(
                "convert_webpage_url_into_markdown",
                {"input": {"url": url}}
            )
            
            # Extract markdown from result
            if hasattr(result, 'content'):
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        # Parse JSON if needed
                        import json
                        try:
                            data = json.loads(content_item.text)
                            if isinstance(data, dict) and "markdown" in data:
                                return data["markdown"]
                        except:
                            return content_item.text
            elif isinstance(result, dict) and "markdown" in result:
                return result["markdown"]
            else:
                return str(result)
                
        except Exception as e:
            logger.error(
                f"Webpage conversion failed: {str(e)}",
                component="MCPClient",
                error_type="WEBPAGE_ERROR",
                url=url
            )
            raise
    
    async def list_tools(self) -> List[str]:
        """List available MCP tools."""
        if not self.initialized:
            await self.initialize()
        
        try:
            tools = await self.mcp_client.list_all_tools()
            return tools
        except Exception as e:
            logger.error(
                f"Failed to list tools: {str(e)}",
                component="MCPClient",
                error_type="LIST_TOOLS_ERROR"
            )
            return []

