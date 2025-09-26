"""
Market Analyser backend (FastAPI) - v2.1
- Uses an orchestrator to fetch analytics, compute top movers, call Gemini, and email results.
- Supports daily scheduler with debug logs.
- Includes US (S&P 500) and India (Nifty 50) movers (CSV lists in backend/data/).
- INR conversion is live via USDINR=X.
- CHANGE: /movers now also returns Gold (GC=F) & Silver (SI=F) for the same period in `metals`.
"""

import os
import json
import asyncio
import smtplib
import csv
import requests
from datetime import date, datetime, timedelta
from typing import List, Optional
from pathlib import Path
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
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
        # "chrome-extension://gfjflonjnioohiocighhikhddfjpjgjf",  # example
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
    global genai_client
    if genai_client is None:
        genai_client = genai.Client()
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

# ---------- Movers endpoint ----------
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
        print(f"[DEBUG] No {market} list found, using default tickers.")
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
        r["name"] = label  # extra friendly label
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


# ---------- API endpoints ----------
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
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
