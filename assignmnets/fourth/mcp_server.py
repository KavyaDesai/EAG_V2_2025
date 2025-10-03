# basic import 
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import math
import sys
from pywinauto.application import Application
from pywinauto import mouse

import win32gui
import win32con
import time
from win32api import GetSystemMetrics

# instantiate an MCP server client
mcp = FastMCP("Calculator")

# DEFINE TOOLS

#addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print("CALLED: add(a: int, b: int) -> int:")
    return int(a + b)

@mcp.tool()
def add_list(l: list) -> int:
    """Add all numbers in a list"""
    print("CALLED: add(l: list) -> int:")
    return sum(l)

# subtraction tool
@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract two numbers"""
    print("CALLED: subtract(a: int, b: int) -> int:")
    return int(a - b)

# multiplication tool
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    print("CALLED: multiply(a: int, b: int) -> int:")
    return int(a * b)

#  division tool
@mcp.tool() 
def divide(a: int, b: int) -> float:
    """Divide two numbers"""
    print("CALLED: divide(a: int, b: int) -> float:")
    return float(a / b)

# power tool
@mcp.tool()
def power(a: int, b: int) -> int:
    """Power of two numbers"""
    print("CALLED: power(a: int, b: int) -> int:")
    return int(a ** b)

# square root tool
@mcp.tool()
def sqrt(a: int) -> float:
    """Square root of a number"""
    print("CALLED: sqrt(a: int) -> float:")
    return float(a ** 0.5)

# cube root tool
@mcp.tool()
def cbrt(a: int) -> float:
    """Cube root of a number"""
    print("CALLED: cbrt(a: int) -> float:")
    return float(a ** (1/3))

# factorial tool
@mcp.tool()
def factorial(a: int) -> int:
    """factorial of a number"""
    print("CALLED: factorial(a: int) -> int:")
    return int(math.factorial(a))

# log tool
@mcp.tool()
def log(a: int) -> float:
    """log of a number"""
    print("CALLED: log(a: int) -> float:")
    return float(math.log(a))

# remainder tool
@mcp.tool()
def remainder(a: int, b: int) -> int:
    """remainder of two numbers divison"""
    print("CALLED: remainder(a: int, b: int) -> int:")
    return int(a % b)

# sin tool
@mcp.tool()
def sin(a: int) -> float:
    """sin of a number"""
    print("CALLED: sin(a: int) -> float:")
    return float(math.sin(a))

# cos tool
@mcp.tool()
def cos(a: int) -> float:
    """cos of a number"""
    print("CALLED: cos(a: int) -> float:")
    return float(math.cos(a))

# tan tool
@mcp.tool()
def tan(a: int) -> float:
    """tan of a number"""
    print("CALLED: tan(a: int) -> float:")
    return float(math.tan(a))

# mine tool
@mcp.tool()
def mine(a: int, b: int) -> int:
    """special mining tool"""
    print("CALLED: mine(a: int, b: int) -> int:")
    return int(a - b - b)

@mcp.tool()
def create_thumbnail(image_path: str) -> Image:
    """Create a thumbnail from an image"""
    print("CALLED: create_thumbnail(image_path: str) -> Image:")
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png")

@mcp.tool()
def strings_to_chars_to_int(string: str) -> list[int]:
    """Return the ASCII values of the characters in a word"""
    print("CALLED: strings_to_chars_to_int(string: str) -> list[int]:")
    return [int(ord(char)) for char in string]

@mcp.tool()
def int_list_to_exponential_sum(int_list: list) -> float:
    """Return sum of exponentials of numbers in a list"""
    print("CALLED: int_list_to_exponential_sum(int_list: list) -> float:")
    return sum(math.exp(i) for i in int_list)

@mcp.tool()
def fibonacci_numbers(n: int) -> list:
    """Return the first n Fibonacci Numbers"""
    print("CALLED: fibonacci_numbers(n: int) -> list:")
    if n <= 0:
        return []
    fib_sequence = [0, 1]
    for _ in range(2, n):
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence[:n]


# --- at top of file (ensure these imports exist) ---
# from pywinauto import Application, mouse, keyboard
# from pywinauto.findwindows import ElementNotFoundError

# @mcp.tool()
# async def draw_rectangle(x1: int, y1: int, x2: int, y2: int) -> dict:
#     """
#     Draw a rectangle in Paint from (x1,y1) to (x2,y2), using UIA only and no regex filters.
#     Works on single-monitor setups (e.g., 1600x600) by using canvas-relative coordinates.
#     """
#     global paint_app
#     try:
#         if not paint_app:
#             return {"content": [TextContent(type="text", text="Paint is not open. Please call open_paint first.")]}
        
#         # Resolve the main Paint window handle from the existing (win32) app, then reconnect via UIA.
#         main_win = paint_app.window(class_name='MSPaintApp')
#         if not main_win.exists(timeout=2):
#             return {"content": [TextContent(type="text", text="Could not find Paint main window.")]}
#         hwnd = main_win.handle

#         # Reconnect via UIA for robust control discovery
#         uia_app = Application(backend="uia").connect(handle=hwnd, timeout=5.0)
#         uia_win = uia_app.window(handle=hwnd)
#         if not uia_win.exists(timeout=3):
#             return {"content": [TextContent(type="text", text="UIA connection to Paint failed.")]}

#         # Bring Paint to front/focus
#         try:
#             uia_win.set_focus()
#         except Exception:
#             pass

#         # ---- Find the Canvas (UIA, no regex) ----
#         # Strategy: (1) exact title "Canvas"; (2) any control whose window_text() contains "Canvas";
#         #           (3) largest descendant heuristic.
#         descendants = uia_win.descendants()
#         canvas_rect = None

#         # (1) exact title
#         exact = [c for c in descendants if (c.window_text() or "").strip() == "Canvas"]
#         if exact:
#             r = exact[0].rectangle()
#             canvas_rect = (r.left, r.top, r.right, r.bottom)
#         else:
#             # (2) contains "Canvas" (case-insensitive)
#             cand = [c for c in descendants if "canvas" in (c.window_text() or "").lower()]
#             if cand:
#                 r = cand[0].rectangle()
#                 canvas_rect = (r.left, r.top, r.right, r.bottom)
#             else:
#                 # (3) largest descendant heuristic
#                 if descendants:
#                     cand = max(descendants, key=lambda c: c.rectangle().width() * c.rectangle().height())
#                     r = cand.rectangle()
#                     canvas_rect = (r.left, r.top, r.right, r.bottom)

#         if not canvas_rect:
#             return {"content": [TextContent(type="text", text="Unable to locate Paint canvas via UIA.")]}

#         # ---- Select Rectangle tool (no regex) ----
#         # Try to click a button whose text contains "Rectangle", else fallback to Alt+H then some arrows/tabs.
#         buttons = [c for c in descendants if getattr(c, "friendly_class_name", lambda: "")() == "Button"]
#         rect_btn = None
#         for b in buttons:
#             title = (b.window_text() or "").strip()
#             if title and "rectangle" in title.lower():
#                 rect_btn = b
#                 break

#         try:
#             if rect_btn:
#                 rect_btn.click_input()
#             else:
#                 # Keyboard fallback: Alt+H to open Home tab, then nudge focus into Shapes grid
#                 uia_win.type_keys("%h")
#                 time.sleep(0.2)
#                 uia_win.type_keys("{TAB}{TAB}{RIGHT}{RIGHT}")
#         except Exception:
#             # Even if tool selection fails, try drawing (in case Rectangle was already selected previously)
#             pass

#         # ---- Compute absolute coords from canvas + requested offsets, clamp to bounds ----
#         left, top, right, bottom = canvas_rect
#         sx = max(left + 1, min(left + x1, right - 2))
#         sy = max(top + 1,  min(top + y1, bottom - 2))
#         ex = max(left + 1, min(left + x2, right - 2))
#         ey = max(top + 1,  min(top + y2, bottom - 2))

#         # ---- Draw ----
#         mouse.press(coords=(sx, sy))
#         mouse.move(coords=(ex, ey))
#         mouse.release(coords=(ex, ey))

#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Rectangle drawn canvas-rel ({x1},{y1})→({x2},{y2}). Canvas abs={canvas_rect}"
#                 )
#             ]
#         }

#     except Exception as e:
#         return {"content": [TextContent(type="text", text=f"Error (UIA) drawing rectangle: {str(e)}")]}

# ensure this import exists near the top of mcp_server.py
from pywinauto import mouse

@mcp.tool()
async def draw_rectangle(x1: int, y1: int, x2: int, y2: int) -> dict:
    """
    Minimal + robust:
      - Finds Paint canvas via UIA (resolution independent, single monitor)
      - Selects 'Pencil' if available (does NOT open any dropdowns)
      - Draws a rectangle outline with four pencil strokes
    No use of 'Size' / 'Outline' / 'Fill' menus (avoids 'Resize and Skew' dialog).
    Coordinates (x1,y1,x2,y2) are CANVAS-relative.
    """
    import time
    from pywinauto.application import Application

    global paint_app
    try:
        if not paint_app:
            return {"content": [TextContent(type="text", text="Paint is not open. Please call open_paint first.")]}
        
        # Get HWND from existing app and reconnect via UIA for stable element search
        main_win = paint_app.window(class_name="MSPaintApp")
        if not main_win.exists(timeout=2):
            return {"content": [TextContent(type="text", text="Could not find Paint main window.")]}
        hwnd = main_win.handle

        uia_app = Application(backend="uia").connect(handle=hwnd, timeout=5.0)
        win = uia_app.window(handle=hwnd)
        if not win.exists(timeout=3):
            return {"content": [TextContent(type="text", text="UIA connection to Paint failed.")]}
        try:
            win.set_focus()
        except Exception:
            pass

        # Helpers
        def snapshot():
            return win.descendants()

        def find_canvas_rect():
            ds = snapshot()
            # exact "Canvas"
            for c in ds:
                try:
                    if (c.window_text() or "").strip() == "Canvas":
                        r = c.rectangle()
                        return (r.left, r.top, r.right, r.bottom)
                except Exception:
                    pass
            # contains "canvas"
            for c in ds:
                try:
                    if "canvas" in (c.window_text() or "").strip().lower():
                        r = c.rectangle()
                        return (r.left, r.top, r.right, r.bottom)
                except Exception:
                    pass
            # biggest descendant heuristic (last resort)
            if ds:
                big = max(ds, key=lambda c: c.rectangle().width() * c.rectangle().height())
                r = big.rectangle()
                return (r.left, r.top, r.right, r.bottom)
            return None

        def clamp_to(rect, px, py, pad=4):
            L, T, R, B = rect
            return (
                max(L + pad, min(px, R - pad)),
                max(T + pad, min(py, B - pad)),
            )

        # ---- locate canvas
        canvas_rect = find_canvas_rect()
        if not canvas_rect:
            return {"content": [TextContent(type="text", text="Unable to locate Paint canvas via UIA.")]}


        time.sleep(0.05)

        # ---- compute absolute coords (canvas-relative → screen)
        L, T, R, B = canvas_rect
        sx, sy = clamp_to(canvas_rect, L + x1, T + y1)
        ex, ey = clamp_to(canvas_rect, L + x2, T + y2)

        # normalize (support any order of x1/x2, y1/y2)
        x_min, x_max = sorted([sx, ex])
        y_min, y_max = sorted([sy, ey])
        
        #x_max, y_max = 500, 500
        # ---- draw four edges (repeat a couple times for visibility)
        def drag(a, b):
            mouse.press(coords=a); mouse.move(coords=b); mouse.release(coords=b)

        reps = 1  # thickness by 2 passes, no menus involved
        for d in range(reps):
            # top
            drag((x_min, y_min + d), (x_max, y_min + d))
            # bottom
            drag((x_min, y_max - d), (x_max, y_max - d))
            # left
            drag((x_min + d, y_min), (x_min + d, y_max))
            # right
            drag((x_max - d, y_min), (x_max - d, y_max))

        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Rectangle (pencil-outline) drawn canvas-rel ({x1},{y1})→({x2},{y2}). Canvas abs={canvas_rect} now the new ones are {x_min, y_min} to {x_max, y_max}"
                )
            ]
        }

    except Exception as e:
        return {"content": [TextContent(type="text", text=f"Error drawing rectangle (minimal): {str(e)}")]}

# @mcp.tool()
# async def add_text_in_paint(text: str, x: int = 80, y: int = 80) -> dict:
#     """
#     Add text inside Microsoft Paint at a CANVAS-relative position.
#     - Uses UI Automation (UIA), no hard-coded toolbar coordinates.
#     - (x, y) are offsets from the top-left of the canvas, in pixels.
#     """
#     import time
#     from pywinauto.application import Application

#     # If the global wasn't created yet, avoid NameError.
#     paint_app_local = globals().get("paint_app", None)

#     try:
#         if not paint_app_local:
#             return {
#                 "content": [
#                     TextContent(
#                         type="text",
#                         text="Paint is not open. Please call open_paint first."
#                     )
#                 ]
#             }

#         # Get the legacy handle and reconnect via UIA for robust element finding
#         legacy_win = paint_app_local.window(class_name="MSPaintApp")
#         if not legacy_win.exists(timeout=2):
#             return {"content": [TextContent(type="text", text="Could not find Paint main window.")]}
#         hwnd = legacy_win.handle

#         uia_app = Application(backend="uia").connect(handle=hwnd, timeout=5.0)
#         win = uia_app.window(handle=hwnd)
#         if not win.exists(timeout=3):
#             return {"content": [TextContent(type="text", text="UIA connection to Paint failed.")]}

#         # Focus Paint
#         try:
#             win.set_focus()
#         except Exception:
#             pass
#         time.sleep(0.1)

#         # ---- Find Canvas rect (prefer element named 'Canvas', fallbacks included)
#         def find_canvas_rect():
#             ds = win.descendants()
#             # exact "Canvas"
#             for c in ds:
#                 try:
#                     if (c.window_text() or "").strip() == "Canvas":
#                         r = c.rectangle()
#                         return (r.left, r.top, r.right, r.bottom)
#                 except Exception:
#                     pass
#             # contains "canvas"
#             for c in ds:
#                 try:
#                     if "canvas" in (c.window_text() or "").lower():
#                         r = c.rectangle()
#                         return (r.left, r.top, r.right, r.bottom)
#                 except Exception:
#                     pass
#             # largest child heuristic (last resort)
#             if ds:
#                 big = max(ds, key=lambda z: z.rectangle().width() * z.rectangle().height())
#                 r = big.rectangle()
#                 return (r.left, r.top, r.right, r.bottom)
#             return None

#         canvas_rect = find_canvas_rect()
#         if not canvas_rect:
#             return {"content": [TextContent(type="text", text="Unable to locate Paint canvas via UIA.")]}

#         L, T, R, B = canvas_rect

#         # Clamp a point inside canvas with a small pad to avoid edges
#         def clamp(px, py, pad=4):
#             return (
#                 max(L + pad, min(L + x, R - pad)),
#                 max(T + pad, min(T + y, B - pad)),
#             )

#         tx, ty = clamp(L + x, T + y)

#         # ---- Select the Text tool
#         # Try to find a button with name containing "Text"
#         text_btn = None
#         for c in win.descendants():
#             try:
#                 # Friendly class name check avoids misclicking non-buttons
#                 if getattr(c, "friendly_class_name", lambda: "")() == "Button":
#                     title = (c.window_text() or "").strip().lower()
#                     if title == "text" or "text" in title:
#                         text_btn = c
#                         break
#             except Exception:
#                 continue

#         try:
#             if text_btn:
#                 text_btn.click_input()
#             else:
#                 # Fallback: open Home tab and try 'T' which commonly selects Text tool
#                 win.type_keys("%h")   # Alt+H = Home
#                 time.sleep(0.15)
#                 win.type_keys("t")
#         except Exception:
#             # Even if we failed to click the tool, attempt to type (it can still work if Text tool was active)
#             pass

#         time.sleep(0.1)

#         # ---- Click on canvas to create a text box and type
#         from pywinauto import mouse
#         mouse.click(coords=(tx, ty))
#         time.sleep(0.1)

#         # Type text (with spaces), slight pause improves reliability
#         win.type_keys(text, with_spaces=True, pause=0.02)

#         # Optional: click slightly outside to finalize the text box
#         mouse.click(coords=(tx + 10, ty + 10))

#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Text added at canvas offset ({x}, {y}). Canvas abs={canvas_rect}, and text is '{text}'"
#                 )
#             ]
#         }

#     except Exception as e:
#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Error adding text: {str(e)}"
#                 )
#             ]
#         }

@mcp.tool()
async def add_text_in_paint(text: str, x: int = 80, y: int = 80) -> dict:
    """
    Add text inside Microsoft Paint at a canvas-relative offset.
    - Forces the Text tool via Alt+H then T (works on Win10/11 Paint).
    - (x, y) are offsets from the top-left of the canvas, in pixels.
    """
    import time
    from pywinauto.application import Application
    from pywinauto import mouse

    paint_app_local = globals().get("paint_app", None)
    if not paint_app_local:
        return {
            "content": [TextContent(type="text", text="Paint is not open. Please call open_paint first.")]
        }

    try:
        # Get Paint main window via legacy handle
        legacy_win = paint_app_local.window(class_name="MSPaintApp")
        if not legacy_win.exists(timeout=2):
            return {"content": [TextContent(type="text", text="Could not find Paint main window.")]}
        hwnd = legacy_win.handle

        # Reconnect with UIA for robust control discovery
        uia_app = Application(backend="uia").connect(handle=hwnd, timeout=5.0)
        win = uia_app.window(handle=hwnd)
        if not win.exists(timeout=3):
            return {"content": [TextContent(type="text", text="UIA connection to Paint failed.")]}

        # Bring Paint to foreground
        try:
            win.set_focus()
        except Exception:
            pass
        time.sleep(0.15)

        # --- FORCE SELECT TEXT TOOL (reliable even if Eraser/Pencil is active)
        # Alt+H = Home tab, then 'T' = Text tool
        win.type_keys("%h", set_foreground=True)
        time.sleep(0.15)
        win.type_keys("t", set_foreground=True)
        time.sleep(0.25)

        # --- Locate canvas rectangle
        def find_canvas_rect():
            # 1) Try element titled exactly 'Canvas'
            try:
                cand = win.child_window(title="Canvas")
                if cand.exists():
                    r = cand.rectangle()
                    return (r.left, r.top, r.right, r.bottom)
            except Exception:
                pass

            # 2) Any element with name containing 'canvas'
            for c in win.descendants():
                try:
                    name = (c.window_text() or "").strip().lower()
                    if "canvas" in name:
                        r = c.rectangle()
                        return (r.left, r.top, r.right, r.bottom)
                except Exception:
                    continue

            # 3) Fallback: pick the largest descendant (usually the canvas area)
            ds = win.descendants()
            if ds:
                big = max(ds, key=lambda z: z.rectangle().width() * z.rectangle().height())
                r = big.rectangle()
                return (r.left, r.top, r.right, r.bottom)

            return None

        canvas_rect = find_canvas_rect()
        if not canvas_rect:
            return {"content": [TextContent(type="text", text="Unable to locate Paint canvas via UIA.")]}

        L, T, R, B = canvas_rect

        # Clamp click inside the canvas with a small padding
        pad = 4
        cx = max(L + pad, min(L + x, R - pad))
        cy = max(T + pad, min(T + y, B - pad))

        # Click to create a text box and type
        mouse.click(coords=(cx, cy))
        time.sleep(0.1)

        # Type the text (allow spaces)
        win.type_keys(text, with_spaces=True, pause=0.02)

        # Optional: click slightly aside to finalize the text box
        mouse.click(coords=(min(cx + 10, R - pad), min(cy + 10, B - pad)))

        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Text added at canvas offset ({x}, {y}). Canvas abs rect={canvas_rect}"
                )
            ]
        }

    except Exception as e:
        return {"content": [TextContent(type="text", text=f"Error adding text: {e}")]}

@mcp.tool()
async def open_paint() -> dict:
    """Open Microsoft Paint maximized on secondary monitor"""
    global paint_app
    try:
        paint_app = Application().start('mspaint.exe')
        time.sleep(0.2)
        
        # Get the Paint window
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        # Get primary monitor width
        #primary_width = GetSystemMetrics(0)
        
        # First move to secondary monitor without specifying size
        win32gui.SetWindowPos(
            paint_window.handle,
            win32con.HWND_TOP,
            0, 0,  # Position it on secondary monitor
            0, 0,  # Let Windows handle the size
            win32con.SWP_NOSIZE  # Don't change the size
        )
        
        # Now maximize the window
        win32gui.ShowWindow(paint_window.handle, win32con.SW_MAXIMIZE)
        time.sleep(0.2)
        
        return {
            "content": [
                TextContent(
                    type="text",
                    text="Paint opened successfully on primary monitor and maximized"
                )
            ]
        }
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error opening Paint: {str(e)}"
                )
            ]
        }
# DEFINE RESOURCES

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    print("CALLED: get_greeting(name: str) -> str:")
    return f"Hello Hi, {name}!"


# DEFINE AVAILABLE PROMPTS
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"
    print("CALLED: review_code(code: str) -> str:")


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
