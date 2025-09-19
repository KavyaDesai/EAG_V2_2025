# backend/main.py
"""
Market Analyser backend (FastAPI) - updated for INR conversion and per-10g display for gold/silver.

Features:
- Loads/creates config.json on startup
- /config POST to save config, /config GET to read it
- /run POST to trigger immediate analysis+email
- /status GET to preview last run & current config
- /analytics GET to compute USD and INR prices and pct changes for given symbols over daily/3mo/6mo
- Uses yfinance for market data, google-genai (Gemini) for analysis, smtplib for SMTP.
"""

import os
import json
import asyncio
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, BackgroundTasks, Query
from pydantic import BaseModel
import yfinance as yf
import smtplib
from email.message import EmailMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Gemini import (google-genai)
from google import genai

# load .env if present
load_dotenv()

# constants
CONFIG_FILE = "config.json"
GEMINI_ENV_VAR = "GEMINI_API_KEY"
TROY_OUNCE_GRAMS = 31.1034768  # grams in one troy ounce

# default configuration - will be written to config.json if missing
default_config = {
    "symbols": ["AAPL", "MSFT", "GC=F", "SI=F"],
    "send_time": "08:30",
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "",
        "recipient": ""
    }
}

app = FastAPI(title="Market Analyser Backend")
scheduler = AsyncIOScheduler()
genai_client = None  # lazy init


# ----------------- Config file helpers -----------------
def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Failed to save config: {e}")


def load_config():
    """
    Loads config.json if present. If not present, writes default_config into config.json
    and returns it. Ensures config.json always exists after first call.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading config.json: {e} — rewriting defaults.")
            cfg = default_config.copy()
            save_config(cfg)
            return cfg
    else:
        cfg = default_config.copy()
        save_config(cfg)
        return cfg


# ----------------- Pydantic models -----------------
class EmailConfig(BaseModel):
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None


class ConfigModel(BaseModel):
    symbols: List[str]
    send_time: str   # "HH:MM"
    email: EmailConfig


# ----------------- Market helpers -----------------
def fetch_symbol_summary(symbol: str) -> str:
    """
    One-line summary for LLM prompt.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval="1d")
        if hist is None or hist.empty or len(hist) < 1:
            return f"{symbol}: no data"
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else None
        open_p = float(latest.get('Open', 0.0) or 0.0)
        close_p = float(latest.get('Close', 0.0) or 0.0)
        vol = int(latest.get('Volume', 0) or 0)
        pct = (close_p - open_p) / open_p * 100 if open_p and open_p != 0 else 0.0
        prev_close = float(prev['Close']) if prev is not None else None
        change_vs_prev = ((close_p - prev_close) / prev_close * 100) if prev_close else None

        summary = (f"{symbol}: open={open_p:.2f}, close={close_p:.2f}, "
                   f"change_today={pct:.2f}%, volume={vol}")
        if change_vs_prev is not None:
            summary += f", vs_prev_close={change_vs_prev:.2f}%"
        return summary
    except Exception as e:
        return f"{symbol}: error fetching data ({e})"


# ----------------- Gemini helpers -----------------
def init_genai_client():
    global genai_client
    if genai_client is None:
        genai_client = genai.Client()  # reads GEMINI_API_KEY from env
    return genai_client


def call_gemini_sync(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    try:
        client = init_genai_client()
        resp = client.models.generate_content(model=model_name, contents=prompt)
        return getattr(resp, "text", str(resp))
    except Exception as e:
        return f"LLM call error: {e}"


async def call_gemini(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, call_gemini_sync, prompt, model_name)


# ----------------- Email helper -----------------
def send_email_smtp(smtp_server: str, smtp_port: int, sender: str, recipient: str, subject: str, body: str, smtp_password: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as s:
        s.starttls()
        s.login(sender, smtp_password)
        s.send_message(msg)


# ----------------- Core pipeline -----------------
async def run_analysis_and_email(cfg: dict):
    symbols = cfg.get("symbols", [])
    lines = []
    for s in symbols:
        lines.append(fetch_symbol_summary(s))

    data_block = "\n".join(lines)
    prompt = (
        "You are a concise market analyst. Given the following market summary lines, produce a short (3-6 sentences) "
        "clear analysis for each symbol: mention price direction today, notable volume behavior, and one simple action (Buy/Hold/Sell) with 1-2 sentence rationale.\n\n"
        f"DATA:\n{data_block}\n\nOutput format:\nTICKER - short analysis\n"
    )

    try:
        analysis = await call_gemini(prompt, model_name="gemini-2.0-flash")
    except Exception as e:
        analysis = f"LLM call failed: {e}"

    # prepare email
    email_cfg = cfg.get("email", {})
    sender = email_cfg.get("sender") or os.getenv("SMTP_SENDER")
    recipient = email_cfg.get("recipient") or os.getenv("SMTP_RECIPIENT")
    smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(email_cfg.get("smtp_port", 587))
    smtp_password = os.getenv("SMTP_PASSWORD") or email_cfg.get("smtp_password")

    subject = f"Daily Market Analysis — {date.today().isoformat()}"
    body = f"Market data (raw):\n{data_block}\n\nAnalysis (LLM):\n{analysis}"

    if not all([sender, recipient, smtp_password]):
        # cannot send mail; persist last run to file and return
        with open("last_run.txt", "w", encoding="utf-8") as f:
            f.write("SKIPPED EMAIL - missing SMTP settings\n\n")
            f.write(body)
        return {"status": "skipped", "reason": "missing smtp settings", "analysis": analysis}

    try:
        send_email_smtp(smtp_server, smtp_port, sender, recipient, subject, body, smtp_password)
    except Exception as e:
        with open("last_run.txt", "w", encoding="utf-8") as f:
            f.write(f"EMAIL FAILED: {e}\n\n")
            f.write(body)
        return {"status": "email_failed", "error": str(e), "analysis": analysis}

    # persist last run
    with open("last_run.txt", "w", encoding="utf-8") as f:
        f.write(body)

    return {"status": "ok", "analysis_summary": analysis}


# ----------------- Forex & INR conversion helpers -----------------
def get_usd_inr_rate() -> Optional[float]:
    """
    Returns current USD->INR rate as float, or None on error.
    Uses Yahoo ticker 'USDINR=X' and falls back to 'INR=X'.
    """
    try:
        fx = yf.Ticker("USDINR=X")
        hist = fx.history(period="1d", interval="1d")
        if hist is not None and not hist.empty:
            return float(hist.iloc[-1]['Close'])
        # fallback
        fx2 = yf.Ticker("INR=X")
        hist2 = fx2.history(period="1d", interval="1d")
        if hist2 is not None and not hist2.empty:
            # Many providers show INR=X as USD/INR or inverse; treat as close value
            return float(hist2.iloc[-1]['Close'])
    except Exception:
        pass
    return None


def fetch_prices_for_period_with_inr(symbol: str, period_label: str):
    """
    Returns dict:
       start_usd, end_usd, currency, start_inr, end_inr, per10g_start_inr, per10g_end_inr
    Returns None on error.
    """
    try:
        ticker = yf.Ticker(symbol)
        # select historical range
        if period_label == 'daily':
            hist = ticker.history(period="5d", interval="1d")
            if hist is None or hist.empty or len(hist) < 1:
                return None
            if len(hist) >= 2:
                start = float(hist.iloc[-2]['Close'])
            else:
                start = float(hist.iloc[-1]['Open'])
            end = float(hist.iloc[-1]['Close'])
        elif period_label == '3mo':
            hist = ticker.history(period="3mo", interval="1d")
            if hist is None or hist.empty:
                return None
            start = float(hist.iloc[0]['Close'])
            end = float(hist.iloc[-1]['Close'])
        elif period_label == '6mo':
            hist = ticker.history(period="6mo", interval="1d")
            if hist is None or hist.empty:
                return None
            start = float(hist.iloc[0]['Close'])
            end = float(hist.iloc[-1]['Close'])
        else:
            hist = ticker.history(period=period_label, interval="1d")
            if hist is None or hist.empty:
                return None
            start = float(hist.iloc[0]['Close'])
            end = float(hist.iloc[-1]['Close'])

        # currency detection (best effort)
        currency = "USD"
        try:
            info = ticker.info
            if isinstance(info, dict) and info.get("currency"):
                currency = info.get("currency")
        except Exception:
            pass

        # prepare INR conversion if currency looks like USD
        start_inr = end_inr = per10g_start = per10g_end = None
        if str(currency).upper().startswith("USD"):
            usd_inr = get_usd_inr_rate()
            if usd_inr:
                start_inr = start * usd_inr
                end_inr = end * usd_inr
                if symbol.upper() in ("GC=F", "SI=F"):
                    per10g_start = start_inr * (10.0 / TROY_OUNCE_GRAMS)
                    per10g_end = end_inr * (10.0 / TROY_OUNCE_GRAMS)

        return {
            "start_usd": round(start, 6),
            "end_usd": round(end, 6),
            "currency": currency,
            "start_inr": round(start_inr, 4) if start_inr is not None else None,
            "end_inr": round(end_inr, 4) if end_inr is not None else None,
            "per10g_start_inr": round(per10g_start, 2) if per10g_start is not None else None,
            "per10g_end_inr": round(per10g_end, 2) if per10g_end is not None else None
        }
    except Exception:
        return None


# ----------------- API endpoints -----------------
@app.post("/config")
async def set_config(cfg: ConfigModel):
    out = cfg.dict()
    existing = load_config()
    existing.update(out)
    save_config(existing)
    schedule_daily_job(existing)
    return {"status": "saved", "config": existing}


@app.get("/config")
def get_config():
    return load_config()


@app.post("/run")
async def run_now(background: BackgroundTasks):
    cfg = load_config()
    background.add_task(run_analysis_and_email, cfg)
    return {"status": "scheduled"}


@app.get("/status")
def status():
    cfg = load_config()
    last = None
    if os.path.exists("last_run.txt"):
        with open("last_run.txt", "r", encoding="utf-8") as f:
            last = f.read()[:4000]
    return {"config": cfg, "last_run_preview": last}


@app.get("/analytics")
def analytics(symbols: str = Query(..., description="Comma-separated tickers"),
              period: str = Query("daily", description="daily | 3mo | 6mo")):
    """
    Example: GET /analytics?symbols=GC=F,SI=F,AAPL&period=3mo
    Returns:
    { "results": [ { symbol, start_usd, end_usd, currency, start_inr, end_inr, per10g_start_inr, per10g_end_inr, pct_change }, ... ] }
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    results = []
    for s in symbol_list:
        info = fetch_prices_for_period_with_inr(s, period)
        if info is None:
            results.append({
                "symbol": s, "start_usd": None, "end_usd": None, "currency": None,
                "start_inr": None, "end_inr": None, "per10g_start_inr": None,
                "per10g_end_inr": None, "pct_change": None
            })
            continue
        start = info.get("start_usd")
        end = info.get("end_usd")
        pct = None
        if start is not None and end is not None and start != 0:
            pct = round((end - start) / start * 100.0, 4)
        results.append({
            "symbol": s,
            "start_usd": info.get("start_usd"),
            "end_usd": info.get("end_usd"),
            "currency": info.get("currency"),
            "start_inr": info.get("start_inr"),
            "end_inr": info.get("end_inr"),
            "per10g_start_inr": info.get("per10g_start_inr"),
            "per10g_end_inr": info.get("per10g_end_inr"),
            "pct_change": pct
        })
    return {"results": results}


# ----------------- Scheduling -----------------
def schedule_daily_job(cfg):
    try:
        scheduler.remove_all_jobs()
    except Exception:
        pass
    try:
        hh, mm = cfg.get("send_time", "08:30").split(":")
        hh = int(hh); mm = int(mm)
    except Exception:
        hh, mm = 8, 30
    trigger = CronTrigger(hour=hh, minute=mm)
    scheduler.add_job(lambda: asyncio.create_task(run_analysis_and_email(cfg)), trigger, id="daily_job")
    print(f"Scheduled daily job at {hh:02d}:{mm:02d}")


@app.on_event("startup")
async def startup_event():
    cfg = load_config()
    if not os.getenv(GEMINI_ENV_VAR):
        print(f"Warning: {GEMINI_ENV_VAR} not set. Gemini calls will fail until you set it.")
    scheduler.start()
    schedule_daily_job(cfg)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
