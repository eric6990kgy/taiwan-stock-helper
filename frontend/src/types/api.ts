/**
 * Mirrors the backend's Pydantic schemas (backend/app/schemas/*.py).
 * Every money/quantity/percent field is typed `string` -- the API
 * serializes Decimal as a JSON string (DecimalStr) specifically so the
 * frontend never has to round-trip financial values through a JS float.
 * Parse with utils/decimal.ts at the point of display, never with `+x` or
 * `Number(x)` for anything that gets shown or compared.
 */

export type AccountType = "BROKERAGE" | "BANK" | "GLOBAL_INVEST" | "CASH";
export type AssetType = "STOCK" | "ETF" | "CASH" | "FUND";
export type ValuationMethod = "TRANSACTION_BASED" | "MANUAL_MARKET_VALUE";
export type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "FEE" | "CASH_DEPOSIT" | "CASH_WITHDRAWAL";
export type WatchlistStatus = "WATCHING" | "RESEARCHING" | "CANDIDATE" | "OWNED" | "REJECTED";
export type ThesisStatus = "INTACT" | "NEEDS_REVIEW" | "BROKEN";

export interface Account {
  id: number;
  user_id: number;
  name: string;
  account_type: AccountType;
  currency: string;
  created_at: string;
}

export interface Asset {
  id: number;
  ticker: string;
  name: string;
  asset_type: AssetType;
  market: string | null;
  currency: string;
  sector: string | null;
  industry: string | null;
  valuation_method: ValuationMethod;
  is_demo_data: boolean;
  needs_review: boolean;
}

export interface Transaction {
  id: number;
  account_id: number;
  asset_id: number;
  date: string;
  type: TransactionType;
  quantity: string;
  price: string;
  fee: string;
  tax: string;
  currency: string;
  note: string | null;
  created_at: string;
}

export interface Holding {
  account_id: number;
  asset_id: number;
  ticker: string;
  asset_name: string;
  valuation_method: ValuationMethod;
  remaining_shares: string;
  average_cost: string;
  remaining_cost_basis: string;
  latest_close: string;
  price_as_of: string | null;
  market_value: string;
  unrealized_pnl: string;
  realized_pnl: string;
  total_pnl: string;
  return_pct: string | null;
  weight: string | null;
  total_dividends_received: string;
  total_fees_paid: string;
  total_tax_paid: string;
}

export interface PortfolioSummary {
  total_market_value: string;
  remaining_cost_basis: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_pnl: string;
  total_return_pct: string | null;
  total_dividends_received: string;
  total_fees_paid: string;
  total_tax_paid: string;
  holdings_count: number;
}

export interface WatchlistEntry {
  id: number;
  asset_id: number;
  ticker: string;
  asset_name: string;
  status: WatchlistStatus;
  reason: string | null;
  target_metrics: Record<string, unknown> | null;
  entry_consideration: string | null;
  review_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface KeyMetric {
  label: string;
  operator: string;
  value: number;
}

export interface Thesis {
  id: number;
  asset_id: number;
  ticker: string;
  thesis: string | null;
  catalysts: string | null;
  risks: string | null;
  key_metrics: KeyMetric[] | null;
  status: ThesisStatus;
  last_reviewed: string | null;
  updated_at: string;
}

export interface Quote {
  ticker: string;
  price: string;
  as_of: string;
  high_52w: string | null;
  low_52w: string | null;
}

export interface Fundamentals {
  period: string;
  revenue: string | null;
  eps: string | null;
  gross_margin: string | null;
  operating_margin: string | null;
  net_margin: string | null;
  roe: string | null;
  roa: string | null;
  debt_ratio: string | null;
  operating_cash_flow: string | null;
  free_cash_flow: string | null;
  source: string;
}

export interface PricePoint {
  date: string;
  open: string | null;
  high: string | null;
  low: string | null;
  close: string;
  volume: number | null;
  source: string;
}

export interface ResearchPage {
  ticker: string;
  name: string;
  asset_type: AssetType;
  market: string | null;
  sector: string | null;
  industry: string | null;
  is_demo_data: boolean;
  quote: Quote;
  latest_fundamentals: Fundamentals | null;
  thesis: Thesis | null;
}

export interface AllocationEntry {
  account_id: number;
  asset_id: number;
  ticker: string;
  asset_name: string;
  market_value: string;
  weight: string | null;
}

export interface Allocation {
  total_market_value: string;
  entries: AllocationEntry[];
}

export interface Performance {
  total_market_value: string;
  remaining_cost_basis: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_pnl: string;
  total_return_pct: string | null;
  note: string;
}

export interface SectorConcentrationEntry {
  sector: string | null;
  market_value: string;
  weight: string | null;
}

export interface TopHolding {
  ticker: string;
  asset_name: string;
  market_value: string;
  weight: string | null;
}

export interface Risk {
  sector_concentration: SectorConcentrationEntry[];
  top_holdings: TopHolding[];
  max_single_position_weight: string | null;
  note: string;
}

export interface ScreenerResult {
  ticker: string;
  asset_name: string;
  revenue_growth_yoy: string | null;
  roe: string | null;
  pe_ratio: string | null;
  foreign_net_buy: number | null;
  rsi_14: string | null;
  above_sma_20: boolean | null;
  composite_score: string | null;
  meets_criteria: boolean;
}

export interface ApiError {
  detail: string;
}

// ---- Phase 6: institutional flow / margin trading / monthly revenue / technical ---

/** Buy/sell/net figures are in shares. `foreign` combines FinMind's
 * Foreign_Investor + Foreign_Dealer_Self categories; `dealer` combines
 * Dealer_self + Dealer_Hedging (see the backend's InstitutionalFlowDTO). */
export interface InstitutionalFlow {
  date: string;
  foreign_buy: number | null;
  foreign_sell: number | null;
  foreign_net: number | null;
  investment_trust_buy: number | null;
  investment_trust_sell: number | null;
  investment_trust_net: number | null;
  dealer_buy: number | null;
  dealer_sell: number | null;
  dealer_net: number | null;
  total_net: number | null;
  source: string;
}

/** All fields are in 張 (board lots, 1 lot = 1,000 shares). */
export interface MarginTrading {
  date: string;
  margin_buy: number | null;
  margin_sell: number | null;
  margin_cash_repayment: number | null;
  margin_balance: number | null;
  short_sale_buy: number | null;
  short_sale_sell: number | null;
  short_sale_cash_repayment: number | null;
  short_sale_balance: number | null;
  source: string;
}

/** yoy_growth/mom_growth are computed by the backend on read -- null means
 * the comparison period is missing or would divide by zero, never a fake 0%. */
export interface MonthlyRevenue {
  revenue_year: number;
  revenue_month: number;
  revenue: string;
  yoy_growth: string | null;
  mom_growth: string | null;
  announcement_date: string | null;
  source: string;
}

export interface TechnicalIndicatorValues {
  sma_5: string | null;
  sma_20: string | null;
  ema_20: string | null;
  rsi_14: string | null;
  macd: string | null;
  macd_signal: string | null;
  macd_histogram: string | null;
  bollinger_upper: string | null;
  bollinger_middle: string | null;
  bollinger_lower: string | null;
  kd_k: string | null;
  kd_d: string | null;
}

export interface TechnicalIndicators {
  ticker: string;
  as_of: string | null;
  indicators: TechnicalIndicatorValues;
  source: string;
}

// ---- Phase 7: composite score --------------------------------------------------

/** Persisted (unlike TechnicalIndicators, which is computed on demand) --
 * one row per day, so a history of these can plot a score trend. A null
 * sub-score means it couldn't be computed for that date (listed in
 * missing_components), never a fabricated neutral value. */
export interface Score {
  date: string;
  value_score: string | null;
  growth_score: string | null;
  momentum_score: string | null;
  quality_score: string | null;
  composite_score: string | null;
  regime: "BULL" | "BEAR" | "NEUTRAL" | null;
  missing_components: string[];
  source: string;
}

// ---- Phase 7 Part 2: deterministic signals --------------------------------------

export type SignalStatus = "BULLISH" | "BEARISH" | "NEUTRAL" | "UNAVAILABLE";

/** A signal is NOT an investment recommendation -- BULLISH/BEARISH describe
 * an indicator's own reading (e.g. "price above its 20-day average"), never
 * a BUY/SELL instruction. Computed on demand, never persisted (unlike
 * Score above) -- there is no /signals/history endpoint. */
export interface Signal {
  id: string;
  category: "TECHNICAL" | "INSTITUTIONAL" | "FUNDAMENTAL" | "COMPOSITE";
  name: string;
  status: SignalStatus;
  value: string | null;
  threshold: string | null;
  as_of: string | null;
  explanation: string;
  source: string;
}

/** overall_status is an unweighted majority vote over every non-UNAVAILABLE
 * signal (V1, not IC/backtest-weighted) -- a tie, including "everything
 * NEUTRAL", is NEUTRAL; UNAVAILABLE only when every signal is UNAVAILABLE. */
export interface SignalResult {
  ticker: string;
  as_of: string | null;
  signals: Signal[];
  overall_status: SignalStatus;
  composite_score: string | null;
  regime: "BULL" | "BEAR" | "NEUTRAL" | null;
}

// ---- Phase 8: risk-gated recommendation engine ----------------------------

export type RecommendationAction = "WATCH" | "CONSIDER_INCREASE" | "CONSIDER_DECREASE";

export interface TriggeredSignal {
  id: string;
  category: string;
  name: string;
  status: SignalStatus;
  explanation: string;
}

/** Never a BUY/SELL instruction -- action is conditional language only
 * (關注/考慮增加關注度/考慮減碼). risk_blocked/risk_block_reason are always
 * present so a blocked recommendation can never be mistaken for a clear
 * one. Only ever created when a ticker's overall signal status actually
 * changed since the last scan -- an unchanged ticker never appears here. */
export interface Recommendation {
  id: number;
  ticker: string;
  asset_name: string;
  action: RecommendationAction;
  previous_status: SignalStatus | null;
  new_status: SignalStatus;
  triggered_signals: TriggeredSignal[];
  risk_blocked: boolean;
  risk_block_reason: string | null;
  composite_score: string | null;
  regime: "BULL" | "BEAR" | "NEUTRAL" | null;
  strategy_version_id: number;
  created_at: string;
}

export interface SignalRules {
  sma_short: number;
  sma_long: number;
  rsi_period: number;
  institutional_window: number;
  composite_bullish: string;
  composite_bearish: string;
}

export type StrategyVersionStatus = "ACTIVE" | "SUPERSEDED" | "ROLLED_BACK";
export type StrategyChangeType = "AUTO_APPLIED" | "CONFIRMED";

export interface StrategyVersion {
  id: number;
  version_number: number;
  rules: Record<string, unknown>;
  status: StrategyVersionStatus;
  change_type: StrategyChangeType;
  reason: string | null;
  backtest_hit_rate: string | null;
  backtest_n: number | null;
  created_at: string;
}

export interface BacktestSummary {
  hits: number;
  n: number;
  horizon: number;
  deadzone_pct: string;
  hit_rate: string | null;
}

export type PendingStrategyChangeStatus = "PENDING" | "CONFIRMED" | "REJECTED";

export interface PendingStrategyChange {
  id: number;
  proposed_rules: Record<string, unknown>;
  reason: string;
  backtest_before: BacktestSummary | null;
  backtest_after: BacktestSummary | null;
  status: PendingStrategyChangeStatus;
  created_at: string;
  decided_at: string | null;
}

// ---- Market Data (Phase 5B) -------------------------------------------------

export interface MarketDataUpdateError {
  ticker: string;
  reason: string;
}

export interface MarketDataUpdateResult {
  status: "completed" | "rate_limited";
  assets_processed: number;
  succeeded: string[];
  failed: MarketDataUpdateError[];
  validation_warnings: MarketDataUpdateError[];
  latest_data_date: string | null;
  source: string;
}
