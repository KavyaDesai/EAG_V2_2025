"""Configuration settings for the chatbot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / "logs"
MCP_SERVER_PATH = PROJECT_ROOT / "mcp_servers" / "mcp_server_2.py"

# Gemini API
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-exp"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Code Agent
CODE_TIMEOUT = int(os.getenv("CODE_TIMEOUT", "10"))

# Conversation
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))

# MCP
MCP_WORKING_DIR = PROJECT_ROOT / "mcp_servers"

# Validate configuration
if not GEMINI_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY or GEMINI_API_KEY environment variable must be set. "
        "Please create a .env file with your API key."
    )

