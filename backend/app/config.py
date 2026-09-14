import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_ROOT / 'investment_os.db'}")

# FinMind (Phase 5B). Registering for a free token raises the rate limit
# from 300/hr to 600/hr (Phase 5 Discovery Report Sec.4) -- optional, the
# adapter works unauthenticated too, just at the lower limit.
FINMIND_API_URL = os.getenv("FINMIND_API_URL", "https://api.finmindtrade.com/api/v4/data")
FINMIND_API_TOKEN = os.getenv("FINMIND_API_TOKEN")  # None is fine -- see above

# Individual-stock signal engine -- risk hard constraints (個股訊號引擎規格書
# Sec.05/07, confirmed with the user 2026-09-14). All expressed as fractions
# of total portfolio market value. Engineering defaults for a small-capital,
# risk-tolerant-but-wants-discipline profile -- not personalized investment
# advice, and adjustable per-deployment via env vars without a code change.
RISK_POSITION_LIMIT_PCT = Decimal(os.getenv("RISK_POSITION_LIMIT_PCT", "0.15"))
RISK_SECTOR_LIMIT_PCT = Decimal(os.getenv("RISK_SECTOR_LIMIT_PCT", "0.30"))
RISK_DRAWDOWN_PAUSE_PCT = Decimal(os.getenv("RISK_DRAWDOWN_PAUSE_PCT", "0.15"))
RISK_DRAWDOWN_STOP_PCT = Decimal(os.getenv("RISK_DRAWDOWN_STOP_PCT", "0.25"))

# Passive benchmark for the alpha/excess-return calculation (spec Goal:
# individual-stock activity is only worth the extra risk if it beats what
# the user already holds passively). Must exist as an Asset row with
# ingested price_history for /api/analytics/benchmark to return a value --
# see README "Benchmark setup" for the one-time steps.
BENCHMARK_TICKER = os.getenv("BENCHMARK_TICKER", "0050")
