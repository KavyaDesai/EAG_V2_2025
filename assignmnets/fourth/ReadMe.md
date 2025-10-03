# MCP Agent Demo

This repo demonstrates how to use **Model Context Protocol (MCP) servers** with **Gemini** to build agentic workflows.  
We show two flows:

1. **Math agent with manual Paint automation**  
2. **Full agentic flow where Gemini decides when to call Paint tools**

---

## 📂 Files

### `mcp_server.py`
- Defines MCP tools for Paint automation:
  - `open_paint` → opens and maximizes Microsoft Paint
  - `draw_rectangle` → draws a rectangle on the canvas
  - `add_text_in_paint` → writes text inside the canvas at given coordinates  
- These tools are exposed over MCP so the client can call them.

---

### `talk_2_mcp_client.py` (manual flow)
- Connects to the MCP server.
- Runs a **math agent** using Gemini:
  - Example: compute ASCII values → sum of exponentials.
- After math is done, Paint automation is **manually invoked**:
  - Calls `open_paint`, `draw_rectangle`, and `add_text_in_paint` sequentially from Python.
- This shows a hybrid approach: **AI for math, manual code for Paint**.

---

### `talk_2_mcp_client_AGENT.py` (fully agentic flow)
- Connects to the MCP server.
- Uses a **two-phase agentic loop** driven entirely by Gemini:
  - **Phase 1 (Math)**: Gemini calls math tools until it produces `FINAL_ANSWER: [number]`.
  - **Phase 2 (Paint)**: Gemini is instructed (via system prompt) to call:
    1. `open_paint`  
    2. `draw_rectangle|50|50|1600|500`  
    3. `add_text_in_paint|<number>|120|160`  
  - Finally, it outputs `FINAL_ANSWER: [done]`.
- All Paint actions happen via **FUNCTION_CALLs from the LLM** (no manual orchestration).

---

## ▶️ Running

1. Make sure you have:
   - Python 3.9+  
   - `pywinauto`, `google-genai`, `python-dotenv`, `mcp` installed  
   - A `.env` file with your Gemini API key:  
     ```env
     GEMINI_API_KEY=your_key_here
     ```

2. In one terminal, start the MCP server:
   ```bash
   python mcp_server.py dev
3. In another terminal, run either client:

    1. Manual + math:

        python talk_2_mcp_client.py

            or 

    2. Full agentic flow:

        python talk_2_mcp_client_AGENT.py
