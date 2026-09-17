# Development Log

*[繁體中文版](DEVLOG.zh-TW.md)*

Chronological record of what was built, why, and what was learned — from
day one through the most recent working session. `README.md` documents
*what's built, as of now*; this file documents *how it got there and what
decisions were made along the way*, including operational work and
research that never became a feature and isn't in README at all.

Each phase below maps to a commit unless noted otherwise. Where a day's
work isn't a code commit (data cleanup, research, manual DB operations),
that's called out explicitly.

---

## 2026-08-28 — V1 foundation: Phases 1–4

**Commit:** [`a17fa82`](../../commit/a17fa82) — Personal Investment OS V1, Phases 1–4

Built the whole stack from scratch in one pass, following the PRD:

- **Schema + migrations** (Phase 1): `users`, `accounts`, `assets`,
  `transactions`, `watchlist`, `investment_thesis`, `price_history`,
  `fundamentals`, plus a reserved `fx_rates` table for future
  multi-currency support that nothing writes to yet. Alembic from day
  one — never `create_all()` against the real DB. Seeded with the PRD's
  demo dataset (7 TW tickers + a Global ETF fund), every row flagged
  `is_demo_data=True`/`source=MOCK` so fixture data is never confused
  with real market data later.
- **Calculation engine** (Phase 2): `app/analytics/` — cost basis
  (weighted-average, realized P&L via `replay_transactions()`),
  valuation, portfolio aggregation. Deliberately zero imports from
  FastAPI/SQLAlchemy, verified by grep — the explicit goal was to keep
  this reusable by "a future rule/signal engine" without restructuring
  (this promise is what made Phase 7's signal engine and Phase A's risk
  engine drop-in additions three weeks later, not rewrites).
- **API layer** (Phase 3): routes → services → repositories/analytics/
  providers → models. 39 endpoints. TWD-only + insufficient-shares
  validation in the service layer, not the DB. All money serialized as
  `DecimalStr` (string, never a JS float) end to end.
- **Frontend** (Phase 4): 6 pages, all money/percent routed through
  `decimal.js` — zero financial calculations in React, by design.
- Included a CORS fix (allow any localhost port, not a hardcoded 5173)
  with a regression test — the first of many "fix it, then write the
  test that would have caught it" moments in this project.

**Result:** 133 backend + 35 frontend tests, full stack usable end to
end from a browser, on day one.

---

## 2026-08-31 — Real market data + institutional/technical data: Phase 5B, Phase 6

**Commits:** [`0803b31`](../../commit/0803b31), [`65697f0`](../../commit/65697f0)

- **Provider research first, code second**: before writing any
  integration, compared TWSE/TPEx official OpenAPIs, FinMind, Fugle,
  Yahoo Finance/yfinance, TEJ, and CMoney, and documented the comparison
  ([`docs/Personal_Investment_OS_Integration_Report.pdf`](docs/Personal_Investment_OS_Integration_Report.pdf)
  plus a Phase 5 Discovery Report in project history). **Chose FinMind** —
  free tier viable, broad Taiwan-specific datasets (institutional flow,
  margin trading, monthly revenue) that Yahoo/yfinance don't cover at
  all. Explicitly noted FinMind's terms restrict the *data* (not the
  client code) to educational/non-commercial use — this app stays
  personal/single-user/non-commercial as a hard constraint because of
  that.
- **Phase 5B**: `FinMindProvider` implementing the existing
  `MarketDataProvider` interface (prices, fundamentals, dividends,
  valuation ratios) — the provider abstraction from Phase 3 meant this
  slotted in without touching services or routes. Manual ingestion via a
  new Settings "Update Market Data" button.
- **Phase 6**: institutional flow (三大法人), margin trading (融資融券),
  monthly revenue with YoY/MoM growth, and a from-scratch technical
  indicator module (SMA/EMA/Wilder's RSI/MACD/Bollinger/Taiwan-convention
  KD) — pure functions, look-ahead-safety verified per indicator (each
  `result[i]` depends only on `input[0..i]`). Research page gained a
  candlestick chart; Screener gained foreign-net-buy/RSI/SMA20 filters.
- A separate research report compared six external Taiwan-stock/quant
  GitHub projects to sanity-check the Phase 6 priority ranking before
  building it.

**Result:** 281 backend + 53 frontend tests.

---

## 2026-09-07 — Phase 6 code review: 8 real bugs found and fixed

**Commit:** [`b2964d7`](../../commit/b2964d7)

A dedicated diff review of Phase 6 (not new features) surfaced real bugs
that would have shipped silently:

- Valuation upsert could crash mid-batch on a missing required column,
  rolling back an entire ingestion run.
- Candlestick chart silently dropped MANUAL-source points instead of
  rendering them.
- Two **falsy-zero bugs** — `x or default` treating a legitimate `0` the
  same as missing data — fixed with explicit `is None` checks. (This
  exact bug class recurred conceptually two weeks later in the stale-TTM
  fundamentals issue below, though that one was a data problem, not a
  code one.)
- `RateLimitError` was being swallowed as a generic `ProviderError`
  instead of stopping the batch — silently corrupting the
  "rate-limited, stop and report" contract Phase 5B had just established.
- 4 near-identical repository classes collapsed into one
  `AssetDateRepository` base, which also closed an untyped-setattr typo
  gap that existed across all 4 copies.

**Result:** 289 backend + 53 frontend tests (6 new regression tests for
these exact bugs).

---

## 2026-09-14 — Phase A: risk limits, drawdown circuit breaker, benchmark

**Commit:** [`2a90492`](../../commit/2a90492)

First slice of the **個股訊號引擎規格書** (Individual Stock Signal Engine
spec), confirmed this day. Three new `/api/analytics` endpoints:

- **Risk limits** (`/risk`): position (15%) and sector (30%)
  concentration checks. **Deliberately scoped to the STOCK sleeve only**
  — an early version compared against the whole portfolio including cash
  and the Global ETF fund, which flagged the *deliberate* 65% passive ETF
  allocation as a "concentration risk." That's backwards: these limits
  exist to police the agent's own stock-picking, not the account as a
  whole, and the ETF position is the benchmark this system is supposed
  to beat, not something it should ever flag. Caught before shipping,
  regression-tested.
- **Drawdown** (`/drawdown`): a two-tier circuit breaker (-15% →
  `PAUSE_NEW_POSITIONS`, -25% → `HARD_STOP`) against an equity curve
  reconstructed retroactively from existing transactions + price
  history — no daily-snapshot job needed to start using it immediately.
- **Benchmark** (`/benchmark`): portfolio return vs. 0050 and the
  resulting alpha — the actual success metric for stock-picking activity,
  since broad-market exposure is already held passively.

**Result:** 28 new tests (all backend/API — no frontend yet for these
three endpoints).

---

## 2026-09-16 (morning) — Phase 7: composite scoring, signal engine, LINE alerts

**Commit:** [`55494fb`](../../commit/55494fb)

- **Composite scoring**: value/growth/momentum/quality sub-scores
  (0–100 or `null` — never a fabricated neutral 50), combined by a
  regime-aware weight table (TAIEX SMA50/SMA200 → BULL/BEAR/NEUTRAL).
  Every threshold/weight explicitly documented as a **V1 placeholder** —
  directionally sensible, not yet empirically validated. (This
  disclaimer turned out to matter a lot three weeks — actually the same
  day, evening — later; see below.)
- **8-signal deterministic engine**: SMA20/60, RSI, MACD (technical),
  foreign/investment-trust net buying (institutional), revenue growth
  positive/accelerating (fundamental), composite score. Computed on
  demand, never persisted. `overall_status` = unweighted majority vote.
  Explicitly **never** BUY/SELL vocabulary — BULLISH/BEARISH describe an
  indicator's own reading, not an instruction.
- **LINE alerts**: broadcasts a consolidated per-asset message when any
  signal is non-neutral, riding along on the existing manual "Update
  Market Data" trigger. Execution stays 100% manual.

**Result:** 432 backend + 69 frontend tests.

---

## 2026-09-16 (midday) — Phase 8: risk-gated recommendation engine

**Commit:** [`ac60120`](../../commit/ac60120)

Implements Phase B of the external spec directly in this app. 看盤台 (a
separate Claude-Artifact dashboard that re-queried Claude live per
refresh — exactly the recurring token cost this repo's deterministic
FinMind-API approach exists to avoid) is retired; its 20-ticker candidate
watchlist is pulled into this app's own `assets`/`watchlist` tables
(`scripts/seed_watchlist_20.py`).

- **Strategy versioning**: signal-engine parameters become a versioned,
  auditable record. A same-keys/different-values change auto-applies; an
  added/removed parameter queues for explicit confirmation with a
  before/after walk-forward backtest.
- **Daily change-only scan**: diffs each watchlist ticker's status
  against its last known snapshot — an unchanged ticker produces nothing,
  closing the "wall of 20 unchanged cards" problem the spec called out.
- **Risk gate before creation, not after**: every `CONSIDER_INCREASE` is
  checked against Phase A's risk/drawdown endpoints before the
  recommendation row is even written.
- New Recommendations and Strategy frontend pages.

**Result:** 469 backend + 79 frontend tests.

---

## 2026-09-16 (afternoon) — Unattended automation + a real UI bug

**Commit:** [`cad23fd`](../../commit/cad23fd)

Two independent problems solved together:

1. **The daily workflow was still "remember to click a button."** An
   in-process scheduler (APScheduler inside FastAPI) was rejected because
   the backend only runs as a dev server started manually each session —
   a scheduler would only fire while that happened to be up, defeating
   the point. Registered a **Windows Task Scheduler** task instead
   (`PersonalInvestmentOS-DailyUpdate`, daily 19:00 — late enough that
   FinMind's institutional-flow/margin datasets have usually settled)
   running a new unattended entrypoint (`backend/scripts/daily_update.py`)
   that reuses `MarketDataIngestionService` exactly as the button does.
   Every run logs to `backend/logs/daily_update.log` so a silent failure
   is never actually silent.
   - **Caught before shipping**: the naive logging setup
     (`logging.basicConfig(level=logging.INFO)` on the root logger) also
     captured httpx/httpcore's own request logging — which includes the
     full request URL, and `FINMIND_API_TOKEN` is sent as a URL query
     param. That would have written the API token to a plaintext log
     file on every run. Fixed by using a named logger and explicitly
     pinning `httpx`/`httpcore` to WARNING, and deleting the one log file
     that had already been written before the fix.
2. **The Transactions page's delete button did nothing when it failed.**
   A delete rejected by the insufficient-shares replay check (or any
   other 4xx) silently vanished — no error, no feedback, the row just
   stayed there. Fixed to surface the actual error inline next to the
   row, with a regression test.

---

## 2026-09-16 (evening) — Operational verification: found two live data-integrity bugs

*No commit — this was investigation + direct data cleanup, not a code
change.* Ran "Update Market Data" for real and checked
`/api/recommendations`; it came back empty. Diagnosed as **EOD data lag**
(FinMind's daily datasets settle after market close; a same-day run
before data has published legitimately has nothing new to compare
against) — not a bug, just a timing expectation to set correctly.

While sanity-checking the underlying data to confirm that diagnosis,
found two **real, pre-existing bugs that had been silently corrupting the
live Research and Recommendations pages for all 7 demo tickers since
Phase 7 shipped** — not just a backtest artifact:

1. **Stale weekend `MOCK` price rows.** `seed.py`'s original demo dataset
   filled every *calendar* day (including weekends) in an 11-day trailing
   window; real FinMind ingestion only ever touches actual trading days.
   Two Saturday/Sunday rows per ticker retained wildly out-of-range mock
   closes sandwiched inside two years of real price history. Fixed by
   deleting the 14 stale `PriceHistory` rows (and the 14 `Score` rows
   computed from them) — `source='MOCK'`, the two weekend dates.
2. **Stale `TTM`-labeled fundamentals row.** `seed.py` also inserted one
   fake `Fundamentals(period="TTM", source="MOCK")` row per demo ticker
   with a tiny fabricated revenue figure. Real FinMind ingestion writes
   real quarterly periods (`"2023Q3"` .. `"2026Q2"`) but never a
   `"TTM"`-labeled one. The revenue-growth code sorts periods as
   **strings** — and `"TTM"` sorts alphabetically *after* `"2026Q2"`
   (`'T' > '2'`) — so the fake row was always treated as "the latest
   period," comparing a fabricated tiny number against the real latest
   quarter. This produced a fake ~-90% "revenue collapse" reading for all
   7 demo tickers, uniformly, and had been silently feeding the
   `REVENUE_GROWTH_POSITIVE`/`_ACCELERATING` signals and the composite
   score's growth sub-score since Phase 7. Fixed by deleting the 7 stale
   rows.

Both root causes trace to the same thing: `seed.py`'s original fixture
data was never fully superseded when real ingestion arrived for those 7
tickers, and nothing checked for the mismatch. Worth remembering next
time demo/fixture data and real data coexist in the same tables.

Also this evening: recorded the user's first real (non-demo) transaction
— 2408 南亞科, 10 shares @ NT$471 (corrected from an initial NT$474) —
and deleted the 7 old demo transactions, leaving 2408 as the only real
holding.

---

## 2026-09-16 (night) — Cathay Securities fee rule, UX automation ask, backtest research

Three more threads the same evening, none of them code changes to this
repo:

- **Researched Cathay Securities' (國泰證券) actual fee schedule** and
  saved it as a **permanent memory rule**, since the user asked for it to
  be applied automatically to all future real transactions: commission ≈
  0.399‰ of trade value (1.425‰ × 2.8折), NT$1 minimum, both legs;
  0.3% securities transaction tax on **sell only**, never buy. This rule
  now applies automatically whenever a real transaction is recorded going
  forward, unless the user supplies an actual bank-statement figure that
  overrides the estimate.
- **Backtest / strategy-tuning exploration** (all scratchpad-only —
  reused the app's real `SignalService`/`ScoringService` against real
  price history, but never touched the repo, per the standing "one-off
  analysis, not a feature" rule): walked the 7 demo tickers' 2 years of
  real backfilled price history day by day, simulating BUY/SELL at the
  signal engine's own `overall_status` transitions, NT$5,000 per order,
  Cathay's fee/tax rule applied. The forward rule (buy on BULLISH, sell
  on BEARISH — following the signals as designed) lost money. Inverting
  it (buy on BEARISH, sell on BULLISH) won decisively across every
  variant tested:

  | Ticker set | Rule | Trades | Win rate | Realized P&L | Profit factor | Max drawdown |
  |---|---|---|---|---|---|---|
  | 7 demo tickers | forward | — | low | negative | <1 | large |
  | 7 demo tickers | inverted | — | high | positive | — | 3,368.60 |
  | 7 demo minus worst | inverted | 35 | 71.4% | +2,523.90 | 1.69 | 2,646.60 |
  | 6 fundamentals-screened¹ | forward | 40 | 22.5% | -2,044.00 | <1 | 3,316.30 |
  | 6 fundamentals-screened¹ | **inverted** | 42 | **78.6%** | **+1,860.30** | **3.04** | **266.00** |

  ¹ Screened from the 19 non-demo real tickers by PE < 20 and 3
  consecutive months of positive YoY revenue growth: 2603 長榮, 6505
  台塑化, 4104 佳醫, 1513 中興電, 2912 統一超, 1216 統一.

  **Why inverting works — verified, not just theorized**: the 8-signal
  engine's short-horizon components (SMA/RSI/MACD) are trend-*confirmation*
  indicators — coincident with recent price action, not predictive of
  future action. Measured directly: across 50 BULLISH transitions on the
  screened tickers, the average return in the 5 days *before* the
  transition was +1.28% (the rally already happened) vs. only +0.08% in
  the 5 days *after* (momentum already spent). Across 49 BEARISH
  transitions, the average return *before* was -2.29% (already sold off)
  vs. **+0.75% after** (a bounce). In a market/period where these
  specific stocks were locally mean-reverting rather than trending, a
  trend-confirmation rule buys near local tops and sells near local
  bottoms; inverting it converts the same signals into a contrarian/
  mean-reversion entry, which is what actually fit this sample.
  - Also researched [FinLab](https://finlab.tw) as a potential
    third-party quant backtesting platform — concluded it would be an
    architecture mismatch (external paid data dependency vs. this repo's
    FinMind + in-house deterministic engine) and is at most a reference
    for a future in-house backtest module's API design, not something to
    integrate directly.
  - **None of this shipped.** Small sample (42–50 trades), 6–7
    correlated tickers, a single 180-day window during which TAIEX's own
    regime was BULL throughout (so the regime-gate hypothesis couldn't
    even be tested against this sample). If this is ever adopted as a
    real strategy version, that needs its own explicit decision and a
    fresh plan — not an inference from one backtest run.

---

## 2026-09-17 — Phase 12: Gemini multi-agent research team

**Commit:** pending (not committed as of this entry)

You asked for a "team" of agents modeled on how a real brokerage research
department is organized — a fundamental analyst, a technical analyst, and
a decision-synthesis role — with a KPI system so it's possible to tell
which agent's calls are actually worth listening to. You picked Gemini
over Claude (citing your own existing familiarity with Google
Antigravity's multi-agent persona system), so this phase is Gemini-only.

The one rule carried forward unchanged from every prior phase: **the
deterministic Phase 8 engine still owns the actual decision.** Nothing
here lets an LLM change `action`/`new_status`/`risk_blocked` — the three
Gemini agents produce a narrative research opinion that rides alongside
the existing `Recommendation`, never instead of it.

- **Verified the SDK before writing any code, same discipline as the
  `claude-api` skill already enforces for Claude.** The plan going in
  assumed `client.interactions.create()` — turns out that's a different,
  session/agent-oriented surface (persisted Agents, webhooks, triggers)
  that doesn't fit a stateless structured-output call. Installed
  `google-genai` locally and inspected the real client before writing
  `app/services/gemini_client.py` — the correct surface for this is
  `client.models.generate_content()` with a Pydantic `response_schema`.
  Caught before any production code was written, not after.
- **`AgentResearchService`** (`app/services/agent_research_service.py`):
  Fundamental Analyst and Technical Analyst run off `ResearchService`'s
  existing data-access methods (no new queries); the Portfolio Manager
  additionally sees the other two roles' output plus the deterministic
  decision as fixed context — it can discuss or disagree with the
  system's call, but its own output can never become the system's call.
  Each role fails independently (`_safe_role`) so one bad response never
  loses the other two.
- **Rate limiting, discovered live, not anticipated.** The first real run
  (right after the user enabled billing) still failed everything with
  `429`/`503` — Gemini's free tier caps `gemini-3.8-flash` at 5
  requests/minute, and a single scan with several changed tickers × 3
  roles blows through that in one burst. Turned out to be a billing
  propagation delay, not a real limit once billing had settled — but
  added a real retry (5s, then 15s backoff on `429`/`503` only, not on
  `400`/auth errors) to `GeminiClient` regardless, since transient
  rate-limiting can recur on the paid tier too.
- **A real, load-bearing test-isolation bug.** Once a real
  `GEMINI_API_KEY` sits in the local `.env` — now permanent on this dev
  machine — any test that called `MarketDataIngestionService.update_all()`
  without explicitly faking `agent_research_service` would make real,
  billed Gemini calls during `pytest`, both in API tests and in existing
  unit tests that never anticipated a real key being present. FinMind
  already had exactly this problem solved via a dependency-injection seam
  (`get_finmind_provider`, overridden per-test with `StubProvider`) — the
  Gemini client had no equivalent seam. Fixed two ways: a
  `get_gemini_client()` seam in `app/api/deps.py` threaded through
  `MarketDataIngestionService.__init__`, and — because unit tests
  construct that service directly, bypassing the API layer's DI entirely
  — a blanket `autouse=True` fixture in `tests/conftest.py` (the file
  above both `tests/unit/` and `tests/api/`) that patches
  `app.services.gemini_client.GEMINI_API_KEY` to `None` for every test,
  full stop. Worth remembering: any future external-API integration in
  this repo needs the same two-layer seam from day one, not bolted on
  after a real key starts costing money during test runs.
- **The output format changed after the user saw real content.** The
  first live run produced genuinely good analysis, but one free-text
  `rationale` paragraph per role read like a wall of text, not a report.
  Redesigned into three role-specific Pydantic schemas
  (`FundamentalCallSchema`/`TechnicalCallSchema`/`PortfolioManagerCallSchema`),
  each with `call`/`confidence` plus 3-4 short, labeled one-sentence
  fields (e.g. `revenue_trend`/`profitability`/`cash_flow_and_balance`/
  `key_risk` for the Fundamental Analyst). `AgentAnalysis.rationale: Text`
  became `details: JSON` (migration `40ca7918d59f`) — the 18 rows already
  generated under the old shape were discarded and regenerated under the
  new schema rather than migrated, since they were same-day AI output,
  cheap to redo (~$0.05), and not worth a data-migration script.
- **KPI reuses Phase 10, no new scoring pass**
  (`app/services/agent_performance_service.py`): each role's `call` is
  graded against the exact same `RecommendationOutcome.actual_direction`
  the deterministic engine's own call is already graded against —
  `UNAVAILABLE` calls excluded from the denominator, same "not
  information-bearing" exclusion Phase 10 already applies to `WATCH`.
- **Recommendations page** gained a per-role structured card in the
  expandable row (call badge, confidence, labeled fields, `key_risk` in
  red); **Review page** gained an "Agent Performance" section, one
  hit-rate card per role, same "insufficient sample" honesty as the cards
  above it.
- **24 new backend tests** (512 → 536) plus existing frontend tests
  updated for the new card format (113 total, unchanged count — existing
  cases rewritten, not new files). Two Alembic migrations
  (`a3ea98c9cdec` adds `agent_analyses`; `40ca7918d59f` reshapes
  `rationale` into `details`) verified from a clean DB.
- **Deliberately not an LLM**: risk/compliance stays the existing Phase A
  rule engine, unchanged — an LLM gating a financial decision would
  reintroduce exactly the hallucination risk every phase up to this one
  has structured itself to avoid.

---

## Open threads (not yet scoped)

- **The continuous-learning loop** (投資日誌/回饋報告/複盤 — a feedback
  loop that reviews past recommendations against what actually happened)
  — requested, not yet designed or built.
- **2408's own backtest** — blocked all session on FinMind rate limits;
  the ticker still has no local price history as of this writing. The 7
  demo tickers and the 6 screened tickers were used as substitutes
  precisely because they already had 2 years of real backfilled data
  locally.
- **Whether to formalize the inverted/mean-reversion finding** into a
  real `StrategyVersion` — an explicit decision the user hasn't made yet,
  flagged above as scratchpad-only for a reason.
