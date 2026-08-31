# Personal Investment OS

A single-user Portfolio Management + Equity Research + Investment Analytics
system for tracking Taiwan-market individual stock positions and a global
ETF / robo-invest allocation. See the architecture review (chat history /
PRD) for full product scope. This README tracks what's actually built.

## Status: Phase 6 complete — Taiwan Chip Data + Technical Analysis

Full stack usable end-to-end from a browser. Beyond price/fundamentals/
dividends/valuation (Phase 5B), the app now ingests institutional-investor
flow and margin trading data, populates monthly revenue, and computes a
deterministic technical-indicator layer (SMA/EMA/RSI/MACD/Bollinger/KD) on
demand from price history — all exposed on the Research page alongside a
candlestick + volume chart.

## Market Data

- **Provider**: [FinMind](https://finmind.github.io/) (`backend/app/providers/finmind_provider.py`),
  chosen after a documented discovery/comparison pass over TWSE/TPEx
  official OpenAPIs, Fugle, Yahoo Finance/yfinance, TEJ, and CMoney (see the
  Phase 5 Discovery Report in project history for the full comparison and
  reasoning). Official TWSE/TPEx OpenAPI access is the documented fallback
  if FinMind ever becomes unavailable.
- **Data-use constraint**: FinMind's own project terms restrict the *data*
  (not the client code, which is Apache-2.0) to educational/non-commercial
  use. **This app is personal, single-user, and non-commercial — do not
  add any feature that redistributes or monetizes data pulled through this
  integration** without first revisiting FinMind's terms directly.
- **How to update data**: Settings → "Update Market Data" (manual only —
  no daily cron job in this phase). Pulls prices, fundamentals, dividends,
  valuation ratios (P/E, P/B, dividend yield), institutional flow, margin
  trading, and monthly revenue for every STOCK/ETF asset; a seeded demo
  asset automatically flips `is_demo_data` to `false` the first time real
  data lands for it, while its old `MOCK`-sourced rows stay in place
  (distinguished by `source`, never deleted).
- **Known data-source limitation**: `TaiwanStockMarketValue` (market cap /
  shares outstanding) requires a paid FinMind tier — the free tier used
  here returns those fields as `null` rather than failing the whole update.
- **Optional**: set `FINMIND_API_TOKEN` in `backend/.env` (free registration
  at finmindtrade.com) to raise the rate limit from 300/hr to 600/hr. Works
  unauthenticated too, just at the lower limit.

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

## What's implemented (Phase 5B)

- **`FinMindProvider`** (`app/providers/finmind_provider.py`): implements
  the full `MarketDataProvider` interface against FinMind's real API (field
  mappings verified against live responses, not guessed from docs) — the
  only file in the codebase that knows FinMind's response shapes.
- **Interface extended** with `get_dividends()` and `get_valuation()`;
  `MockMarketDataProvider` (still what every ordinary read in the app uses)
  implements both from the local DB, so the provider boundary stays clean —
  no FinMind-specific structures leak into services or repositories.
- **Schema**: `dividends` table (market-wide ex-dividend calendar, distinct
  from a user's own DIVIDEND transactions); `price_history` gained
  `adjusted_close`, `trading_value`, `pe_ratio`, `pb_ratio`, `dividend_yield`;
  `assets` gained `shares_outstanding` and `listing_status`.
- **`MarketDataIngestionService`** (`app/services/market_data_service.py`):
  the manual half of the hybrid ingestion architecture (Settings → API →
  FinMind → validation → normalization → repositories → SQLite). One
  ticker failing never aborts the batch; a rate-limit stops fetching more
  but explicitly reports every remaining ticker as skipped, never a silent
  drop; re-ingesting the same date/period/ex-dividend-date upserts instead
  of duplicating.
- **Validation** (`app/services/market_data_validation.py`): OHLC sanity
  checks applied before every DB write, independent of `app.analytics`.
- **Settings UI**: "Update Market Data" button showing status, assets
  processed, succeeded/failed tickers with reasons, validation warnings,
  latest data date, and source.
- **62 new tests** (56 backend, bringing the backend total to 193; 6
  frontend, bringing the frontend total to 41 — 234 tests overall).

## What's implemented (Phase 6)

- **Institutional flow** (`institutional_flows` table): daily 三大法人
  buy/sell/net in shares, keyed by `(asset, date)`. FinMind's five raw
  categories (`Foreign_Investor`, `Foreign_Dealer_Self`, `Investment_Trust`,
  `Dealer_self`, `Dealer_Hedging`) are grouped into the conventional
  three-way foreign/investment-trust/dealer split — see
  `InstitutionalFlowDTO`'s docstring for exactly how, and note that a bucket
  missing one of its categories comes back `None` rather than a partial sum.
- **Margin trading** (`margin_trading` table): daily 融資融券, keyed by
  `(asset, date)`. **All fields are in 張 (board lots, 1,000 shares)**,
  confirmed against FinMind's live API by cross-checking against TWSE's own
  published 融資餘額 for the same ticker/date (see `MarginTradingDTO`'s
  docstring) — do not assume shares.
- **Monthly revenue** (`monthly_revenue` table): keyed by `(asset,
  revenue_year, revenue_month)` — the *covered* month, not FinMind's `date`
  field (which is the announcement month). YoY/MoM growth is computed on
  read (`ResearchService._revenue_growth`), never persisted; `None` when the
  comparison period is missing or would divide by zero, never a fake 0%.
- **Technical indicators** (`app/analytics/technical.py`): SMA, EMA,
  Wilder's RSI, MACD, Bollinger Bands, Taiwan-convention KD (2/3-previous +
  1/3-new smoothing, not the textbook stochastic), and ATR (implemented, not
  yet wired into the API response). Pure functions — no DB/HTTP/FastAPI
  imports, enforced by an automated test
  (`tests/unit/test_analytics_independence.py`), same independence
  guarantee as the Phase 2 calculation engine. Every function is
  index-aligned and look-ahead-safe: `result[i]` depends only on
  `input[0..i]`, verified by a dedicated no-look-ahead test per indicator.
  Computed on demand from `price_history` — no caching table.
- **Research API extended**: `GET /api/research/{ticker}/institutional`,
  `/margin`, `/revenue`, and `/technical` (the last accepts an optional
  `as_of` date to compute indicators as of a historical date, still without
  look-ahead). Every response carries `source` (`FINMIND` or `CALCULATED`)
  so a calculated indicator is never presented as if it came from the data
  provider.
- **Screener extended**: `foreign_net_buy_gt`, `rsi_lt`/`rsi_gt`, and
  `above_sma_20` filters, alongside `foreign_net_buy`/`rsi_14`/`above_sma_20`
  fields on every result. `None` (not a fabricated value) whenever the
  underlying data isn't there yet.
- **Ingestion extended**: `MarketDataIngestionService` gained three more
  best-effort blocks (institutional/margin/revenue), same pattern as
  fundamentals/dividends — one dataset failing never blocks the others, and
  `RateLimitError` still stops the whole batch rather than being absorbed as
  a per-ticker warning.
- **Research page**: candlestick + volume chart (`lightweight-charts`,
  replacing the Phase 4 line chart), plus new Technical Indicators,
  Institutional Flow, and Margin Trading/Monthly Revenue sections — all
  reachable from the existing ticker selector, no navigation changes.
- **88 new backend tests** (bringing the total to 281) and **12 new
  frontend tests** (bringing the total to 53 — 334 overall). New Alembic
  migration (`b1e14c304976`) verified from a clean DB.

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

No scheduled/automatic market-data ingestion (manual "Update Market Data"
only), AI/notifications/trading of any kind, historical time-series
performance, market-cap/dividend-yield screener filters (schema now has
`shares_outstanding`, but the free FinMind tier can't populate it), CSV
import/export UI (the endpoints exist, no frontend for them yet), account
creation/editing UI. Fubon Nano Investment has no official API/export/Open
Banking path (confirmed in the Phase 5 Discovery Report) — its holdings are
tracked via the existing `MANUAL_MARKET_VALUE` pattern, same as the Global
ETF fund.

As of Phase 6: no composite/regime-aware scoring, no signal engine, no
alerts/notifications, no backtesting, no AI research/narrative layer, no
MOPS material-announcement data (FinMind doesn't have this dataset — needs
a second provider against TWSE/TPEx's own OpenAPI, per the Phase 5
Discovery Report's documented fallback), no real-time data, no securities
lending/industry-chain/ETF-specific datasets. See the Phase 6 report in
project history for the full priority ranking and rationale for what's
deferred and why.
