# Multi-Agent Chatbot System

A terminal-based chatbot with multi-agent architecture supporting:
- **Local RAG** (FAISS vector store)
- **Web page operations** (summarize, count words, extract URLs)
- **Web search** (DuckDuckGo)
- **Math & code execution** (Python sandbox)
- **General Q&A** (Gemini 2.0 Flash)

## Architecture

See `ARCHITECTURE.md` and `ARCHITECTURE_DIAGRAMS.md` for detailed architecture documentation.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
LOG_LEVEL=INFO
CODE_TIMEOUT=10
MAX_HISTORY=20
```

Get your Gemini API key from: https://makersuite.google.com/app/apikey

### 3. Verify MCP Server

The MCP server should be in `mcp_servers/mcp_server_2.py` with:
- FAISS index in `mcp_servers/faiss_index/`
- Documents in `mcp_servers/documents/`

## Usage

### Run the Chatbot

```bash
python main.py
```

### Example Queries

**Local RAG:**
```
> Search my notes for RAG architecture
> What is cricket according to my documents?
> Which file mentions DLF?
```

**Math/Code:**
```
> What is 37^5?
> Compute the integral of x^2 from 0 to 1
```

**Web Page Operations:**
```
> Summarize https://example.com
> How many times is 'transformer' repeated on this page?
> Extract URLs related to 'semaris create' from https://example.com
```

**Web Search:**
```
> Search the web for Python tutorials
> Find information about RAG architecture and summarize the top 2 results
```

**General Q&A:**
```
> Explain RAG like I'm a beginner
> What is the difference between transformers and RNNs?
```

### Commands

- `help` - Show help message
- `clear` - Clear conversation history
- `debug` - Toggle debug mode (show routing decisions)
- `exit` / `quit` - Exit the chatbot

## Project Structure

```
new_architecture/
├── agents/              # Agent implementations
│   ├── router.py       # RouterAgent
│   ├── planner.py      # PlannerAgent
│   ├── validator.py    # ValidatorAgent
│   ├── local_rag.py    # LocalRAGAgent
│   ├── math_code.py    # MathAndCodeAgent
│   ├── web_page.py     # WebPageAgent
│   ├── web_search.py   # WebSearchAgent
│   └── general_qa.py   # GeneralQAAgent
├── core/               # Core components
│   ├── logger.py       # Structured logging
│   ├── gemini_client.py # Gemini API client
│   ├── mcp_client.py   # MCP client wrapper
│   ├── code_agent.py   # Code execution agent
│   └── conversation.py # Conversation state
├── terminal/           # Terminal interface
│   └── chat_loop.py    # TerminalChatLoop
├── mcp_servers/        # MCP server (existing)
├── logs/               # Log files (auto-created)
├── config.py           # Configuration
├── main.py             # Entry point
└── requirements.txt    # Dependencies
```

## Logging

Logs are stored in `logs/` directory:
- `chatbot_YYYY-MM-DD.log` - Daily log files
- `error_summary.json` - Aggregated error statistics

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Error Handling

The system includes comprehensive error handling:
- Automatic retries for transient errors
- User-friendly error messages
- Detailed logging for debugging
- Graceful degradation on failures

## Limitations

- **Routing**: May misclassify ambiguous queries
- **RAG**: Only searches indexed documents
- **Web Search**: Depends on DuckDuckGo API availability
- **Code Execution**: Sandboxed for security (moderate strictness)
- **Browser MCP**: Not available (requires explicit URLs)

## Development

### Debug Mode

Enable debug mode to see:
- Router decisions (task type, confidence)
- Execution plans for multi-step tasks
- Tool calls and execution times

```bash
# In chat, type: debug
> debug
```

### Testing

Test each agent with example queries from the "Example Queries" section above.

## Troubleshooting

**"API key is invalid"**
- Check your `.env` file has `GOOGLE_API_KEY` set correctly

**"MCP server not found"**
- Verify `mcp_servers/mcp_server_2.py` exists
- Check MCP server is working independently

**"No documents found"**
- Ensure FAISS index exists in `mcp_servers/faiss_index/`
- Check documents are in `mcp_servers/documents/`

**"Code execution failed"**
- Check code uses only allowed libraries
- Verify syntax is correct

## License

This is a learning project for understanding multi-agent architectures.

