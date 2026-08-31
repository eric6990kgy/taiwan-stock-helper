"""FastAPI application entrypoint. Owns exactly one thing beyond wiring:
translating domain exceptions raised by services (or bubbled up from
app.analytics) into HTTP responses — so routes never need their own
try/except blocks (PRD Sec.39: clear errors, not "something went wrong").
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.analytics.exceptions import InsufficientSharesError, MixedPositionError
from app.api.routes import (
    accounts,
    analytics,
    assets,
    import_export,
    market_data,
    portfolio,
    research,
    screener,
    thesis,
    transactions,
    watchlist,
)
from app.providers.market_data_provider import AssetNotFoundError, ProviderError, RateLimitError
from app.services.exceptions import DuplicateError, InvalidAmountError, NotFoundError, UnsupportedCurrencyError

app = FastAPI(title="Personal Investment OS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # Matches any localhost/127.0.0.1 port, not just Vite's default 5173 --
    # Vite silently picks the next free port when 5173 is taken, and a
    # hardcoded single-port allowlist breaks (as a same-origin-looking CORS
    # failure) every time that happens. Still local-only, never a wildcard.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})


@app.exception_handler(NotFoundError)
@app.exception_handler(AssetNotFoundError)
async def not_found_handler(request: Request, exc: Exception):
    return _error(404, str(exc))


@app.exception_handler(DuplicateError)
async def duplicate_handler(request: Request, exc: DuplicateError):
    return _error(409, str(exc))


@app.exception_handler(InsufficientSharesError)
@app.exception_handler(MixedPositionError)
@app.exception_handler(UnsupportedCurrencyError)
@app.exception_handler(InvalidAmountError)
@app.exception_handler(ValueError)
async def bad_request_handler(request: Request, exc: Exception):
    return _error(400, str(exc))


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError):
    return _error(429, str(exc))


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    # 502: the request to us was fine, but our upstream (FinMind) failed --
    # never surfaced as a bare 500, per Sec.39's "clear errors" principle.
    return _error(502, str(exc))


for router in (
    accounts.router,
    assets.router,
    transactions.router,
    portfolio.router,
    research.router,
    watchlist.router,
    thesis.router,
    analytics.router,
    screener.router,
    import_export.router,
    market_data.router,
):
    app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
