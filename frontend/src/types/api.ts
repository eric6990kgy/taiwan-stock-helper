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
  meets_criteria: boolean;
}

export interface ApiError {
  detail: string;
}
