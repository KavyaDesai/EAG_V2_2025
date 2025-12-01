"""Test script to verify MCP server is working."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_servers.multiMCP import MultiMCP

async def test_mcp():
    """Test MCP server connection and tools."""
    print("Testing MCP server...")
    
    server_configs = [
        {
            "id": "rag_server",
            "script": "mcp_servers/mcp_server_2.py",
            "cwd": "mcp_servers"
        }
    ]
    
    mcp_client = MultiMCP(server_configs)
    
    try:
        print("Initializing MCP client...")
        await mcp_client.initialize()
        
        print("\nListing tools...")
        tools = await mcp_client.list_all_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        if len(tools) == 0:
            print("\n❌ ERROR: No tools found! MCP server is not exposing tools.")
            print("This is the root cause of RAG queries failing.")
        else:
            print("\n✅ MCP server is working correctly!")
            
            # Test calling a tool
            if "search_stored_documents_rag" in tools:
                print("\nTesting search_stored_documents_rag tool...")
                try:
                    result = await mcp_client.call_tool(
                        "search_stored_documents_rag",
                        {"input": {"query": "test"}}
                    )
                    print(f"✅ Tool call successful: {type(result)}")
                except Exception as e:
                    print(f"❌ Tool call failed: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp())

