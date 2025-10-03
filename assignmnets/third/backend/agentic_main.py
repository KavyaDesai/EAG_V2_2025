"""
Market Analyser backend (FastAPI) - v2.2 (agentic)
- Adds an agentic flow: LLM returns a JSON "plan" (list of allowed tool calls).
- Orchestrator validates & executes those tool calls (no arbitrary execution).
- Keeps all existing endpoints and functionality.
"""

import os
import json
import asyncio
import smtplib
import csv
import requests
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Literal
from pathlib import Path
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, ValidationError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from google import genai
from fastapi.middleware.cors import CORSMiddleware

# ---------- Constants ----------
CONFIG_FILE = "config.json"
TROY_OUNCE_GRAMS = 31.1034768
GRAMS_UNIT = 10  # we want per 10 grams, not per ounce
DATA_DIR = Path(__file__).parent / "data"

load_dotenv()
app = FastAPI(title="Market Analyser Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # easiest for local dev; tighten to chrome-extension://<your-id> for prod
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
scheduler = AsyncIOScheduler()
genai_client = None

# ---------- Models ----------
class EmailConfig(BaseModel):
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None

class ConfigModel(BaseModel):
    symbols: List[str]
    send_time: str
    email: EmailConfig

# ---------- Helpers ----------
def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"symbols": ["GC=F", "SI=F"], "send_time": "08:30", "email": {}}

def init_genai_client():
    """Initialize Google GenAI client using API key from env.

    Looks for GOOGLE_API_KEY first (official), then GEMINI_API_KEY for convenience.
    """
    global genai_client
    if genai_client is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing Google AI API key. Set GOOGLE_API_KEY (preferred) "
                "or GEMINI_API_KEY in your environment/.env"
            )
        genai_client = genai.Client(api_key=api_key)
    return genai_client


async def call_gemini(prompt: str, model: str = "gemini-2.0-flash") -> str:
    def _inner():
        client = init_genai_client()
        resp = client.models.generate_content(model=model, contents=prompt)
        return getattr(resp, "text", str(resp))
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _inner)

def send_email_smtp(smtp_server, smtp_port, sender, recipient, subject, body, password):
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, recipient
    msg.set_content(body)
    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as s:
        s.starttls()
        s.login(sender, password)
        s.send_message(msg)

# ---------- INR rate ----------
_usd_inr_cache = {"val": None, "ts": None}
def get_usd_inr_rate() -> Optional[float]:
    """Fetch USD/INR (cached 5 min)."""
    global _usd_inr_cache
    now = datetime.utcnow()
    if _usd_inr_cache["val"] and _usd_inr_cache["ts"] and now - _usd_inr_cache["ts"] < timedelta(minutes=5):
        return _usd_inr_cache["val"]
    try:
        fx = yf.Ticker("USDINR=X")
        hist = fx.history(period="1d", interval="5m")
        if hist is not None and not hist.empty:
            val = float(hist.iloc[-1]["Close"])
            _usd_inr_cache = {"val": val, "ts": now}
            print(f"[DEBUG] USD/INR={val}")
            return val
    except Exception as e:
        print("[DEBUG] USDINR fetch error:", e)
    return _usd_inr_cache["val"]

# ---------- Market data ----------
def resolve_symbol_via_yahoo(q: str) -> Optional[str]:
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(q)}"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
        quotes = data.get("quotes") or []
        if not quotes:
            return None
        for cand in quotes:
            if cand.get("quoteType", "").lower() in ("equity", "etf"):
                return cand["symbol"]
        return quotes[0].get("symbol")
    except Exception:
        return None

def fetch_for_symbol(symbol: str, period: str = "daily") -> dict:
    """
    period supports:
      - 'daily'  -> last close vs prior close (or open if only one bar)
      - '3mo'    -> first close of 3mo window vs last
      - '6mo'    -> first close of 6mo window vs last
      - any yfinance-compatible 'period' string (falls back to first vs last close)
    """
    try:
        t = yf.Ticker(symbol)
        if period == "daily":
            hist = t.history(period="5d", interval="1d")
            if hist is None or hist.empty:
                return {"symbol": symbol, "error": "no_data"}
            start = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else float(hist.iloc[-1]["Open"])
            end = float(hist.iloc[-1]["Close"])
        elif period == "3mo":
            hist = t.history(period="3mo", interval="1d")
            start, end = float(hist.iloc[0]["Close"]), float(hist.iloc[-1]["Close"])
        elif period == "6mo":
            hist = t.history(period="6mo", interval="1d")
            start, end = float(hist.iloc[0]["Close"]), float(hist.iloc[-1]["Close"])
        else:
            hist = t.history(period=period, interval="1d")
            start, end = float(hist.iloc[0]["Close"]), float(hist.iloc[-1]["Close"])

        pct = (end - start) / start * 100 if start else None
        usd_inr = get_usd_inr_rate()
        return {
            "symbol": symbol,
            "start_usd": start,
            "end_usd": end,
            "pct_change": round(pct, 2) if pct is not None else None,
            "end_inr": round(end * usd_inr, 2) if usd_inr else None,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

# ---------- Orchestrator ----------
async def orchestrator_run(symbols: List[str], period: str = "daily", email_send: bool = True):
    print(f"[DEBUG] Orchestrator run: {symbols}, period={period}")
    results: List[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch_for_symbol, s, period) for s in symbols]
        for f in futs:
            results.append(f.result())

    valid = [r for r in results if r.get("pct_change") is not None]
    valid.sort(key=lambda x: x["pct_change"], reverse=True)
    gainers, losers = valid[:5], valid[-5:][::-1]

    lines = [f"{r['symbol']} start={r['start_usd']} end={r['end_usd']} pct={r['pct_change']}" for r in gainers + losers]
    prompt = "Summarize market movers briefly and suggest Buy/Hold/Sell:\n" + "\n".join(lines)
    analysis = await call_gemini(prompt)

    body = f"Top Gainers:\n{gainers}\n\nTop Losers:\n{losers}\n\nGemini Analysis:\n{analysis}"
    with open("last_run.txt", "w", encoding="utf-8") as f:
        f.write(body)

    if email_send:
        cfg = load_config()
        ecfg = cfg.get("email", {})
        sender = ecfg.get("sender") or os.getenv("SMTP_SENDER")
        recipient = ecfg.get("recipient") or os.getenv("SMTP_RECIPIENT")
        pwd = os.getenv("SMTP_PASSWORD")
        if sender and recipient and pwd:
            try:
                send_email_smtp(
                    ecfg.get("smtp_server", "smtp.gmail.com"),
                    int(ecfg.get("smtp_port", 587)),
                    sender,
                    recipient,
                    f"Market Report {date.today().isoformat()}",
                    body,
                    pwd,
                )
            except Exception as e:
                print("[DEBUG] Email failed:", e)
    return {"gainers": gainers, "losers": losers, "analysis": analysis}

# ---------- Movers / Commodities ----------
def load_market_tickers(market: str) -> List[str]:
    if market == "us":
        fname = DATA_DIR / "sp50.csv"
        defaults = ["AAPL", "MSFT", "AMZN", "GOOGL", "TSLA"]
    elif market == "in":
        fname = DATA_DIR / "nifty50.csv"
        defaults = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]
    else:
        return []
    if fname.exists():
        with open(fname, newline="", encoding="utf-8") as f:
            return [row[0].strip() for row in csv.reader(f) if row]
    else:
        print(f("[DEBUG] No {market} list found, using default tickers."))
        return defaults

def fetch_metals(period: str) -> List[dict]:
    """Return Gold & Silver rows for the same period."""
    return [
        fetch_for_symbol("GC=F", period),  # Gold (COMEX)
        fetch_for_symbol("SI=F", period),  # Silver (COMEX)
    ]

def fetch_commodities(period: str):
    """Return key commodity prices for the same period."""
    symbols = {
        "Gold (GC)": "GC=F",
        "Silver (SI)": "SI=F",
        "Crude Oil WTI (CL)": "CL=F",
        "Crude Oil Brent (BZ)": "BZ=F",
        "Copper (HG)": "HG=F",
    }
    rows = []
    for label, sym in symbols.items():
        r = fetch_for_symbol(sym, period)
        r["name"] = label
        rows.append(r)
    return rows

@app.get("/movers")
def movers(market: str = "us", period: str = "daily", top: int = 10):
    syms = load_market_tickers(market)
    if not syms:
        raise HTTPException(400, f"No list for {market}")

    results = [fetch_for_symbol(s, period) for s in syms]
    valid = [r for r in results if r.get("pct_change") is not None]
    valid.sort(key=lambda x: x["pct_change"], reverse=True)
    commodities = fetch_commodities(period)

    return {
        "gainers": valid[:top],
        "losers": valid[-top:][::-1],
        "commodities": commodities,   # instead of "metals"
    }

# ---------- Agentic flow: schemas, registry, dispatcher ----------

# Allowed markets & periods for guardrails
ALLOWED_MARKETS = {"us", "in"}
ALLOWED_PERIODS = {"daily", "3mo", "6mo"}  # you can extend

# ---- Tool arg models ----
class GetMoversArgs(BaseModel):
    market: Literal["us", "in"] = "us"
    period: Literal["daily", "3mo", "6mo"] = "daily"
    top: int = Field(10, ge=1, le=50)

class GetCommoditiesArgs(BaseModel):
    period: Literal["daily", "3mo", "6mo"] = "daily"

class SendEmailArgs(BaseModel):
    subject: str = Field(..., max_length=200)
    body: str = Field(..., max_length=20000)

class RunFullReportArgs(BaseModel):
    period: Literal["daily", "3mo", "6mo"] = "daily"
    email_send: bool = True

# ---- Tool call & plan schema ----
AllowedToolName = Literal["get_movers", "get_commodities", "send_email", "run_full_report"]

class ToolCall(BaseModel):
    name: AllowedToolName
    args: Dict[str, Any] = Field(default_factory=dict)

class AgentPlan(BaseModel):
    steps: List[ToolCall]

# ---- Tool implementations (wrappers over your code) ----
def tool_get_movers(args: GetMoversArgs) -> Dict[str, Any]:
    syms = load_market_tickers(args.market)
    if not syms:
        raise HTTPException(400, f"No list for {args.market}")
    results = [fetch_for_symbol(s, args.period) for s in syms]
    valid = [r for r in results if r.get("pct_change") is not None]
    valid.sort(key=lambda x: x["pct_change"], reverse=True)
    return {"gainers": valid[:args.top], "losers": valid[-args.top:][::-1]}

def tool_get_commodities(args: GetCommoditiesArgs) -> Dict[str, Any]:
    return {"commodities": fetch_commodities(args.period)}

def tool_send_email(args: SendEmailArgs) -> Dict[str, Any]:
    cfg = load_config()
    ecfg = cfg.get("email", {})
    sender = ecfg.get("sender") or os.getenv("SMTP_SENDER")
    recipient = ecfg.get("recipient") or os.getenv("SMTP_RECIPIENT")
    pwd = os.getenv("SMTP_PASSWORD")
    if not (sender and recipient and pwd):
        raise HTTPException(500, "Email not configured (sender/recipient/password missing).")
    send_email_smtp(
        ecfg.get("smtp_server", "smtp.gmail.com"),
        int(ecfg.get("smtp_port", 587)),
        sender,
        recipient,
        args.subject,
        args.body,
        pwd,
    )
    return {"status": "email_sent", "to": recipient}

async def tool_run_full_report(args: RunFullReportArgs) -> Dict[str, Any]:
    cfg = load_config()
    syms = cfg.get("symbols", [])
    return await orchestrator_run(syms, period=args.period, email_send=args.email_send)

# Registry maps tool name -> (callable, arg_model, is_async)
TOOL_REGISTRY: Dict[str, Any] = {
    "get_movers": (tool_get_movers, GetMoversArgs, False),
    "get_commodities": (tool_get_commodities, GetCommoditiesArgs, False),
    "send_email": (tool_send_email, SendEmailArgs, False),
    "run_full_report": (tool_run_full_report, RunFullReportArgs, True),
}

# ---- LLM prompting ----
AGENT_SYSTEM_PROMPT = """You are a planner that outputs ONLY JSON with a list of tool calls.
Use these tools (names and JSON arg schemas):
1) get_movers: {"market": "us|in", "period": "daily|3mo|6mo", "top": 1-50}
2) get_commodities: {"period": "daily|3mo|6mo"}
3) send_email: {"subject": str, "body": str}
4) run_full_report: {"period":"daily|3mo|6mo","email_send": true|false}

Rules:
- Output ONLY valid JSON with shape {"steps":[{"name": "...", "args": {...}}, ...]}.
- Do not include commentary, markdown, or code fences.
- Prefer minimal steps to satisfy the request.
- If the user asks for an email, add a send_email step with a concise body.
"""

def make_agent_prompt(user_query: str) -> str:
    return f"{AGENT_SYSTEM_PROMPT}\nUser request:\n{user_query}\nReturn the plan now."

def _coerce_json(text: str) -> dict:
    """Attempt to parse LLM output into JSON plan robustly."""
    try:
        return json.loads(text)
    except Exception:
        # common case: fenced code block
        if "```" in text:
            parts = text.split("```")
            for p in parts:
                p = p.strip()
                if p.startswith("{") and p.endswith("}"):
                    try:
                        return json.loads(p)
                    except Exception:
                        pass
        # last resort: find first/last braces
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except Exception as e:
            raise ValueError(f"LLM did not return valid JSON. Raw: {text[:2000]}")

async def plan_with_llm(user_query: str) -> AgentPlan:
    raw = await call_gemini(make_agent_prompt(user_query))
    data = _coerce_json(raw)
    try:
        plan = AgentPlan(**data)
    except ValidationError as ve:
        # Single retry: tell LLM the error and ask for corrected JSON
        retry_prompt = (
            f"{AGENT_SYSTEM_PROMPT}\nYour previous JSON failed validation:\n{ve}\n"
            f"User request:\n{user_query}\nReturn corrected JSON ONLY."
        )
        raw2 = await call_gemini(retry_prompt)
        data2 = _coerce_json(raw2)
        plan = AgentPlan(**data2)
    #import pdb; pdb.set_trace()
    return plan

async def execute_plan(plan: AgentPlan) -> Dict[str, Any]:
    transcript: List[Dict[str, Any]] = []
    results: List[Any] = []
    for i, step in enumerate(plan.steps, start=1):
        name = step.name
        if name not in TOOL_REGISTRY:
            transcript.append({"step": i, "name": name, "status": "error", "error": "unknown_tool"})
            continue
        func, arg_model, is_async = TOOL_REGISTRY[name]
        try:
            validated_args = arg_model(**(step.args or {}))
            if is_async:
                out = await func(validated_args)
            else:
                # run sync tool in thread to avoid blocking
                loop = asyncio.get_running_loop()
                out = await loop.run_in_executor(None, func, validated_args)
            transcript.append({"step": i, "name": name, "status": "ok"})
            results.append({"name": name, "result": out})
        except Exception as e:
            transcript.append({"step": i, "name": name, "status": "error", "error": str(e)})
            results.append({"name": name, "error": str(e)})
    return {"transcript": transcript, "results": results}

# ---------- API endpoints for agent ----------
class AgentQuery(BaseModel):
    query: str = Field(..., max_length=4000)

@app.post("/agent")  
async def agent_endpoint(payload: AgentQuery):
    """
    Natural-language to plan -> validated execution.
    Returns the execution transcript and per-step results.
    """
    plan = await plan_with_llm(payload.query)
    exec_out = await execute_plan(plan)
    return {"plan": plan.model_dump(), "execution": exec_out}

# ---------- Config / Run / Status ----------
@app.post("/config")
async def set_config(cfg: ConfigModel):
    save_config(cfg.dict())
    schedule_daily_job(load_config())
    return {"status": "saved"}

@app.get("/config")
def get_config():
    return load_config()

@app.post("/run")
async def run_now(background: BackgroundTasks):
    cfg = load_config()
    background.add_task(orchestrator_run, cfg.get("symbols", []))
    return {"status": "scheduled"}

@app.get("/status")
def status():
    last = None
    if os.path.exists("last_run.txt"):
        with open("last_run.txt", "r", encoding="utf-8") as f:
            last = f.read()[:2000]
    return {"last_run_preview": last}

# ---------- Scheduler ----------
def schedule_daily_job(cfg: dict) -> None:
    try:
        scheduler.remove_all_jobs()
    except Exception:
        pass
    try:
        hh, mm = cfg.get("send_time", "08:30").split(":")
        hh, mm = int(hh), int(mm)
    except Exception:
        hh, mm = 8, 30
    trigger = CronTrigger(hour=hh, minute=mm)
    scheduler.add_job(lambda: asyncio.create_task(orchestrator_run(cfg.get("symbols", []))), trigger, id="daily_job")
    print("[DEBUG] Scheduled job at", hh, ":", mm)

@app.on_event("startup")
async def startup_event():
    cfg = load_config()
    scheduler.start()
    schedule_daily_job(cfg)
    print("[DEBUG] Jobs on startup:", scheduler.get_jobs())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agentic_main:app", host="127.0.0.1", port=8000, reload=True)
