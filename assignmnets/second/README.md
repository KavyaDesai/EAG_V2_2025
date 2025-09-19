# Release v1.0.0 — Daily Market Analyser

Release date: YYYY-MM-DD

## Summary
Initial stable release (v1.0.0) of Daily Market Analyser:
- Local FastAPI backend (yfinance + Google Gemini 2.0 Flash + SMTP)
- Chrome extension (Manifest V3) with popup UI
- Analytics endpoints for daily / 3mo / 6mo performance
- Top gainers / losers view and in-popup LLM summary preview
- APScheduler for daily emailed digests

## Files changed / highlights
- backend/main.py — full backend and analytics endpoints
- chrome-extension/* — UI and logic
- Added run_backend.ps1 for one-click start
- README.md / .env template / release notes

## Known issues & caveats
- Requires user-provided GEMINI_API_KEY and SMTP credentials.
- Yahoo Finance (yfinance) ticker availability depends on region — alternative: GLD/SLV ETFs.
- If packaging for Web Store or hosting backend publicly, secure/manage keys & TLS.

## Next steps (v1.x)
- Add CSV download of analytics
- Add OAuth support for Gmail
- Add optional hosted backend deploy instructions (Render / Cloud Run)
