"""Main entry point for the chatbot."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import GEMINI_API_KEY, GEMINI_MODEL, LOG_DIR, MCP_SERVER_PATH, CODE_TIMEOUT
from core.logger import get_logger
from core.gemini_client import GeminiClient
from core.mcp_client import MCPClient
from core.code_agent import CodeAgent
from terminal.chat_loop import TerminalChatLoop


async def main():
    """Main function."""
    # Initialize logger
    logger = get_logger(log_dir=LOG_DIR, level="INFO")
    mcp_client = None
    
    try:
        logger.info("Starting chatbot system...", component="MAIN")
        
        # Initialize clients
        logger.info("Initializing Gemini client...", component="MAIN")
        gemini_client = GeminiClient(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
        
        logger.info("Initializing MCP client...", component="MAIN")
        mcp_client = MCPClient(mcp_server_path=str(MCP_SERVER_PATH))
        await mcp_client.initialize()
        
        logger.info("Initializing CodeAgent...", component="MAIN")
        code_agent = CodeAgent(timeout=CODE_TIMEOUT)
        
        # Initialize chat loop
        logger.info("Initializing TerminalChatLoop...", component="MAIN")
        chat_loop = TerminalChatLoop(
            gemini_client=gemini_client,
            mcp_client=mcp_client,
            code_agent=code_agent,
            debug_mode=False
        )
        
        # Run chat loop
        logger.info("Starting chat loop...", component="MAIN")
        await chat_loop.run()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user", component="MAIN")
        print("\nShutting down...")
    except Exception as e:
        logger.critical(
            f"Fatal error: {str(e)}",
            component="MAIN",
            error_type="FATAL_ERROR"
        )
        print(f"Fatal error: {str(e)}")
    finally:
        # Cleanup
        if mcp_client:
            try:
                await mcp_client.mcp_client.shutdown() if hasattr(mcp_client, 'mcp_client') else None
            except:
                pass
        logger.info("Shutdown complete", component="MAIN")


if __name__ == "__main__":
    asyncio.run(main())

