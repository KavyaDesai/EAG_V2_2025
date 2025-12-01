# How to Run the Chatbot

## Quick Start (Windows)

### Step 1: Create Virtual Environment

```powershell
# Create venv
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 2: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

### Step 3: Set Up Environment Variables

Create a `.env` file in the project root with your Gemini API key:

```env
GOOGLE_API_KEY=your_api_key_here
LOG_LEVEL=INFO
CODE_TIMEOUT=10
MAX_HISTORY=20
```

**Get your API key from:** https://makersuite.google.com/app/apikey

### Step 4: Verify MCP Server

Make sure your MCP server is set up:
- `mcp_servers/mcp_server_2.py` exists
- `mcp_servers/faiss_index/` has the index files
- `mcp_servers/documents/` has your documents

### Step 5: Run the Chatbot

```powershell
python main.py
```

## Troubleshooting

### "Module not found" errors
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### "API key is invalid"
- Check `.env` file exists and has `GOOGLE_API_KEY=your_key`
- Make sure no extra spaces around the `=`

### "MCP server not found"
- Verify `mcp_servers/mcp_server_2.py` exists
- Check the path in `config.py` is correct

### Execution Policy Error (PowerShell)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Example Session

```
> python main.py
============================================================
Chatbot System - Multi-Agent Architecture
============================================================
Type 'help' for commands, 'exit' to quit
============================================================

> Search my notes for RAG architecture
[LocalRAGAgent] Searching FAISS index...
[Response] Based on your documents: ...

> What is 37^5?
[MathAndCodeAgent] Processing math/code query...
[Response] Result: 69343957

> exit
Goodbye!
```

