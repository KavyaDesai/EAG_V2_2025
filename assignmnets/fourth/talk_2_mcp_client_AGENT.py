import os
import re
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from concurrent.futures import TimeoutError

# ==============================
# Helpers
# ==============================

def extract_final_number(final_line: str) -> str:
    """Parse a numeric value from FINAL_ANSWER: [42] or FINAL_ANSWER: [3.14]."""
    m = re.search(r"FINAL_ANSWER:\s*\[\s*([+-]?\d+(?:\.\d+)?)\s*\]\s*$", final_line)
    if m:
        return m.group(1)
    m2 = re.search(r"([+-]?\d+(?:\.\d+)?)", final_line)
    if m2:
        return m2.group(1)
    raise ValueError(f"Could not parse numeric FINAL_ANSWER from: {final_line}")


async def generate_with_timeout(client, prompt, timeout=15):
    """Run Gemini generation with timeout, in executor thread."""
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
        ),
        timeout=timeout
    )


def coerce_arg(value: str, schema_type: str):
    """Convert string value to correct type based on schema type."""
    if schema_type == "integer":
        return int(value)
    if schema_type == "number":
        return float(value)
    if schema_type == "boolean":
        v = str(value).strip().lower()
        return v in ("1", "true", "yes", "y", "on")
    if schema_type == "array":
        # handle comma-separated values or [a,b,c]
        if isinstance(value, str):
            v = value.strip("[]")
            items = [s.strip() for s in v.split(",")] if v else []
        else:
            items = list(value)

        # Try to auto-convert items to int/float if possible
        converted = []
        for it in items:
            try:
                if "." in it:
                    converted.append(float(it))
                else:
                    converted.append(int(it))
            except Exception:
                converted.append(it)  # fallback keep string
        return converted
    return str(value)



def build_tools_description(tools):
    """Make readable description for all tools."""
    lines = []
    for i, tool in enumerate(tools):
        try:
            name = getattr(tool, "name", f"tool_{i}")
            desc = getattr(tool, "description", "No description")
            schema = getattr(tool, "inputSchema", {}) or {}
            props = schema.get("properties", {})
            parts = []
            for p_name, p_info in props.items():
                p_type = p_info.get("type", "string")
                required = p_name in (schema.get("required", []) or [])
                parts.append(f"{p_name}:{p_type}{'*' if required else ''}")
            sig = ", ".join(parts) if parts else "no parameters"
            lines.append(f"{name}({sig}) - {desc}")
        except Exception:
            lines.append(f"tool_{i}(unknown) - (schema error)")
    return "\n".join(lines)


def parse_model_line(text: str):
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    # strip leading '-' if present
    if line.startswith("- "):
        line = line[2:].strip()
    if line.startswith("FUNCTION_CALL:"):
        fn_spec = line.split(":", 1)[1].strip()
        parts = [p.strip() for p in fn_spec.split("|")]
        return ("CALL", parts[0], parts[1:])
    if line.startswith("FINAL_ANSWER:"):
        payload = line.split(":", 1)[1].strip()
        return ("FINAL", payload, [])
    return ("INVALID", line, [])



# ==============================
# Prompts
# ==============================

SYSTEM_MATH = """You are a math agent solving problems in iterations.

Available tools:
{TOOLS}

Respond with EXACTLY ONE line:
- FUNCTION_CALL: function_name|param1|param2|...
- FINAL_ANSWER: [number]

Rules:
- Only give FINAL_ANSWER when math is complete.
- Do not repeat function calls with the same parameters.
- Use the TOOL_RESULT history below instead of calling the same tool again.
"""

SYSTEM_PAINT = """You are a tool-using agent. You MUST draw the previously computed number in Microsoft Paint.

Available tools:
{TOOLS}

Respond with EXACTLY ONE line:
- FUNCTION_CALL: function_name|param1|param2|...
- FINAL_ANSWER: [done]

Rules:
- Call, in order:
  1) open_paint
  2) draw_rectangle|50|50|1600|500
  3) add_text_in_paint|{NUM}|120|160
- Do not repeat function calls with the same parameters.
- Only output FINAL_ANSWER: [done] after all three calls succeed.
"""


# ==============================
# Main
# ==============================

async def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    server_params = StdioServerParameters(command="python", args=["mcp_server.py"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tools = tools_result.tools
            tools_by_name = {t.name: t for t in tools}
            tools_description = build_tools_description(tools)

            # Phase state
            phase = "math"
            pending_number = None
            iteration = 0
            max_iterations = 15
            transcript = []

            query_math = """First convert 'kAVYA' into ASCII values, then calculate the sum of their exponentials. 
Do not call the same tool twice; use TOOL_RESULT history."""

            while iteration < max_iterations:
                print(f"\n--- Iteration {iteration+1} (phase={phase}) ---")

                if phase == "math":
                    system_prompt = SYSTEM_MATH.format(TOOLS=tools_description)
                    query = query_math
                else:
                    system_prompt = SYSTEM_PAINT.format(TOOLS=tools_description, NUM=pending_number)
                    query = f"Draw the number {pending_number} in Paint as specified."

                # Include transcript
                history = "\n".join(transcript) if transcript else "(no previous steps)"
                full_prompt = f"{system_prompt}\n\nTOOL_RESULT history:\n{history}\n\nQuery: {query}\n\nYour response:"

                try:
                    resp = await generate_with_timeout(client, full_prompt, timeout=20)
                    model_text = resp.text.strip()
                except Exception as e:
                    print(f"Model error: {e}")
                    break

                kind, head, args = parse_model_line(model_text)
                print(f"MODEL => {model_text}")

                if kind == "CALL":
                    fn_name = head
                    tool = tools_by_name.get(fn_name)
                    if not tool:
                        print(f"Unknown tool: {fn_name}")
                        break

                    schema = tool.inputSchema or {}
                    props = schema.get("properties", {}) or {}
                    arguments = {}

                    if props:
                        arg_list = list(args)
                        for p_name, p_info in props.items():
                            if not arg_list:
                                raise ValueError(f"Missing param {p_name} for {fn_name}")
                            raw = arg_list.pop(0)
                            arguments[p_name] = coerce_arg(raw, p_info.get("type", "string"))

                    print(f"Calling {fn_name} with {arguments}")
                    result = await session.call_tool(fn_name, arguments=arguments)

                    if hasattr(result, "content") and isinstance(result.content, list):
                        texts = [getattr(item, "text", str(item)) for item in result.content]
                        tool_out = " | ".join(texts)
                    else:
                        tool_out = str(result)

                    print(f"{fn_name} => {tool_out}")
                    transcript.append(f"TOOL_RESULT: {fn_name} => {tool_out}")

                    iteration += 1
                    continue

                if kind == "FINAL":
                    if phase == "math":
                        try:
                            pending_number = extract_final_number(model_text)
                            print(f"Parsed FINAL_ANSWER number: {pending_number}")
                        except ValueError as e:
                            print(f"Parse error: {e}")
                            break
                        # switch to paint phase
                        phase = "paint"
                        iteration += 1
                        continue
                    else:
                        print("\n=== COMPLETE ===")
                        print(model_text)
                        break

                if kind == "INVALID":
                    print(f"Invalid model response: {head}")
                    iteration += 1
                    continue


if __name__ == "__main__":
    asyncio.run(main())
