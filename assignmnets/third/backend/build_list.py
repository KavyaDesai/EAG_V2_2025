# build_lists.py
from pathlib import Path
import time
import requests
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

def get_html(url: str, tries: int = 3, backoff: float = 1.5) -> str:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last = e
            time.sleep(backoff ** i)
    raise RuntimeError(f"Failed to GET {url}: {last}")

def save_series(series: pd.Series, path: Path):
    series = series.dropna().astype(str).str.strip()
    series = series[series != ""]
    path.write_text("\n".join(series) + "\n", encoding="utf-8")
    print(f"Wrote {len(series)} symbols to {path}")

def build_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = get_html(url)
    tables = pd.read_html(html)
    # find the table with 'Symbol'
    for t in tables:
        if "Symbol" in t.columns:
            syms = (
                t["Symbol"]
                .astype(str)
                .str.replace(".", "-", regex=False)  # BRK.B -> BRK-B (Yahoo format)
                .str.strip()
            )
            save_series(syms, DATA_DIR / "sp500.csv")
            return
    raise RuntimeError("Could not find 'Symbol' column for S&P 500")

def build_nifty50():
    url = "https://en.wikipedia.org/wiki/NIFTY_50"
    html = get_html(url)
    tables = pd.read_html(html)
    target = None
    for t in tables:
        cols = {str(c).lower(): c for c in t.columns}
        for key in ("symbol", "ticker"):
            if key in cols:
                target = t[cols[key]]
                break
        if target is not None:
            break
    if target is None:
        raise RuntimeError("Could not find NIFTY 50 symbols")

    syms = (
        target.astype(str)
        .str.strip()
        .str.replace(".", "-", regex=False)  # normalize
        + ".NS"  # Yahoo suffix for NSE
    )
    save_series(syms, DATA_DIR / "nifty50.csv")

if __name__ == "__main__":
    build_sp500()
    build_nifty50()
