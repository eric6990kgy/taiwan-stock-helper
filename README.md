# Personal Investment OS

A single-user Portfolio Management + Equity Research + Investment Analytics
system for tracking Taiwan-market individual stock positions and a global
ETF / robo-invest allocation. See the architecture review (chat history /
PRD) for full product scope. This README tracks what's actually built.

## Status: Phase 4 complete — Frontend Dashboard

Full stack is now usable end-to-end from a browser: React frontend →
FastAPI backend → SQLite, seeded with demo data.

## Backend setup

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

cp .env.example .env   # defaults to a local sqlite file, no edits needed

./.venv/Scripts/python -m alembic upgrade head     # create investment_os.db
./.venv/Scripts/python -m app.database.seed        # load demo dataset
./.venv/Scripts/python -m pytest tests/ -v         # run the test suite

./.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# then open http://127.0.0.1:8000/docs for interactive Swagger UI
```

## Frontend setup

```bash
cd frontend
npm install

cp .env.example .env   # set VITE_API_URL if the backend isn't on the default port

npm run dev             # http://127.0.0.1:5173, expects the backend running
npm run test             # vitest — component + API-integration tests
npm run build            # production build (tsc -b && vite build)
```

## What's implemented (Phase 1)

- **Schema** (`backend/app/models/`): `users`, `accounts`, `assets`,
  `transactions`, `watchlist`, `investment_thesis`, `price_history`,
  `fundamentals`, and a reserved-but-unused `fx_rates` table for future
  multi-currency support.
- **Migrations** (`backend/alembic/`): schema is managed via Alembic from
  day one — no direct `create_all()` against the real DB.
- **Seed data** (`backend/app/database/seed.py`): the PRD Sec.37 demo
  dataset — 7 TW tickers, the Global ETF fund, a cash account, mock price
  history + fundamentals, sample transactions covering every transaction
  type, one watchlist entry, one investment thesis. Every asset is flagged
  `is_demo_data=True`; every price/fundamentals row carries a `source`
  (`MOCK` or `MANUAL`) — this is fixture data, not real market data.
- **Tests** (`backend/tests/`): 29 tests covering every CHECK constraint,
  every UNIQUE constraint, FK enforcement, and seed-data integrity, against
  an in-memory SQLite DB built straight from the models.

## What's implemented (Phase 2)

- **Transaction replay** (`app/analytics/cost_basis.py`): `replay_transactions()`
  and `calculate_positions()` derive weighted-average cost, realized P&L,
  and remaining shares/cost purely from a list of `TransactionInput` —
  sorted chronologically internally, so backdated entries recalculate
  correctly regardless of insertion order.
- **Valuation** (`app/analytics/valuation.py`): market value, unrealized
  P&L, and return %, implementing both `TRANSACTION_BASED` and
  `MANUAL_MARKET_VALUE` conventions.
- **Portfolio aggregation** (`app/analytics/portfolio.py`): portfolio
  weight per position and a `PortfolioSummary` rollup (invested capital,
  market value, unrealized/realized P&L, dividends, fees, tax, total
  return).
- **67 tests total** (38 new in Phase 2) — see the Phase 2 report in
  conversation history for the full breakdown of formulas and edge cases
  covered.
- Zero imports from FastAPI, SQLAlchemy, or anything DB/HTTP-related
  anywhere in `app/analytics/` — verified by grep, not just by convention.

## What's implemented (Phase 3)

- **Layered backend** (`app/api/routes` → `app/services` → `app/repositories`
  / `app/analytics` / `app/providers` → `app/models`): routes are thin
  controllers, all business rules live in services, all financial math still
  comes from the untouched Phase 2 `app/analytics` package.
- **MarketDataProvider abstraction** (`app/providers/`): `MockMarketDataProvider`
  serves prices/fundamentals/company info from the local DB — swapping in a
  real vendor later touches one factory function in `app/api/deps.py`, no
  route or service code.
- **39 REST endpoints** across accounts, assets, transactions, portfolio,
  holdings, research, fundamentals, prices, watchlist, thesis, analytics
  (allocation/performance/risk), screener, and CSV import/export.
- **TWD-only validation and insufficient-shares protection** live in
  `TransactionService`, not in a DB constraint or a route — every
  create/update/delete replays the resulting transaction history through
  `app.analytics.cost_basis.replay_transactions()` before committing.
- **Decimal-safe serialization**: every money/quantity field serializes as a
  JSON string via a shared `DecimalStr` type, never a JS float.
- **133 tests total** (66 new API integration tests in Phase 3, on top of
  the 67 from Phases 1–2, all still passing unmodified).

## What's implemented (Phase 4)

- **6 pages** (`frontend/src/pages/`): Dashboard, Portfolio, Transactions,
  Research, Watchlist, Settings — routed with `react-router-dom`, all
  backed by the live FastAPI API via `@tanstack/react-query`.
- **Decimal-safe display** (`frontend/src/utils/decimal.ts`): every
  money/percent/share value is formatted through `decimal.js`, never
  `Number()`/`parseFloat` — the API's `DecimalStr` promise is honored all
  the way to the screen.
- **Zero financial calculations in React** — every number shown is either
  a raw API field or trivial formatting (rounding for display, thousands
  grouping). Cost basis, P&L, weights all come from the backend.
- **Shared components** (`frontend/src/components/`): `QueryState` (one
  consistent loading/error/empty pattern used by every page),
  `AllocationChart`/`PriceChart` (Recharts), `SummaryCard`, `Money`/
  `Percent`/`Shares`, demo-data and status badges, `Modal`.
- **35 frontend tests** (Vitest + Testing Library + MSW): formatting
  utilities, `QueryState`'s four render states, and page-level integration
  tests against a mocked API (including the insufficient-shares error
  path rendering in the Add Transaction form).
- Production build passes (`tsc -b && vite build`); all 133 backend tests
  still green, unmodified.

## Key architectural decisions locked in this phase

- **Positions are derived per `(account_id, asset_id)`**, never stored
  directly — `transactions` is the only source of truth (see
  `Transaction`'s docstring for the exact cost-basis arithmetic).
- **`Asset.valuation_method`** (`TRANSACTION_BASED` vs
  `MANUAL_MARKET_VALUE`) lets the Global ETF fund be represented without a
  second schema shape — see `Asset`'s docstring for the convention.
- **V1 is TWD-only.** `fx_rates` exists in the schema so V2 doesn't need a
  migration to add it, but nothing writes to it yet; single-currency is
  enforced at the service layer (Phase 3+), not the DB.
- **All money/quantity columns are `NUMERIC`**, mapped to Python
  `Decimal` — never `float`.
- The calculation engine (Phase 2) will import nothing from FastAPI or
  SQLAlchemy, so it stays reusable by a future rule/signal engine or a
  Claude-based analysis service without restructuring.

## Not built yet

Live market data (Mock only), AI/notifications/trading of any kind,
historical time-series performance, market-cap/dividend-yield screener
filters, CSV import/export UI (the endpoints exist, no frontend for them
yet), account creation/editing UI. See the architecture review's Phase
5–10 plan and the Phase 4 report's "known limitations" for specifics.
