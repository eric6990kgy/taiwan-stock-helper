"""Unattended entrypoint for the daily "Update Market Data" run, invoked by
a Windows Task Scheduler task (registered separately, see README's
"Automated daily update" section) rather than a click in the Settings UI.

Deliberately zero new business logic -- constructs the exact same
MarketDataIngestionService the API route uses and calls .update_all() with
no ticker filter, so a scheduled run behaves identically to clicking the
button with the ticker box empty (all eligible STOCK/ETF assets, which as
of Phase 8 also triggers the daily recommendation scan and any LINE
alerts). Only added concern here: an unattended run's failure must never
be silent, so every run appends one entry to logs/daily_update.log
regardless of outcome, including an uncaught exception's traceback.

Run manually to test:
    cd backend
    .venv/Scripts/python -m scripts.daily_update
"""

import logging
import traceback
from pathlib import Path

from app.database.session import SessionLocal
from app.providers.finmind_provider import FinMindProvider
from app.services.market_data_service import MarketDataIngestionService

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "daily_update.log"


def _configure_logging() -> None:
    """INFO on the root logger would also capture httpx/httpcore's own
    per-request logging -- which includes the full request URL, and
    FINMIND_API_TOKEN is sent as a URL query param (see
    FinMindProvider._request). That would leak the token into a plaintext
    log file. Configure only this script's own logger at INFO, and pin
    httpx/httpcore to WARNING explicitly so their request logs never
    reach the handler."""
    LOG_DIR.mkdir(exist_ok=True)
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger("daily_update").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


log = logging.getLogger("daily_update")


def run() -> None:
    _configure_logging()
    db = SessionLocal()
    provider = FinMindProvider()
    try:
        service = MarketDataIngestionService(db, provider)
        result = service.update_all()
        log.info(
            "status=%s assets_processed=%d succeeded=%d failed=%d warnings=%d latest_data_date=%s",
            result.status,
            result.assets_processed,
            len(result.succeeded),
            len(result.failed),
            len(result.validation_warnings),
            result.latest_data_date,
        )
        for f in result.failed:
            log.warning("failed ticker=%s reason=%s", f.ticker, f.reason)
        for w in result.validation_warnings:
            log.info("warning ticker=%s reason=%s", w.ticker, w.reason)
    except Exception:
        log.error("daily_update crashed:\n%s", traceback.format_exc())
        raise
    finally:
        provider.close()
        db.close()


if __name__ == "__main__":
    run()
