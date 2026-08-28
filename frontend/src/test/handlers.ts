import { http, HttpResponse } from "msw";

const API_URL = "http://127.0.0.1:8010";

export const mockAccounts = [
  { id: 1, user_id: 1, name: "Fubon Securities", account_type: "BROKERAGE", currency: "TWD", created_at: "2026-01-01T00:00:00" },
  { id: 2, user_id: 1, name: "Cash", account_type: "CASH", currency: "TWD", created_at: "2026-01-01T00:00:00" },
];

export const mockAssets = [
  {
    id: 1,
    ticker: "3653",
    name: "健策",
    asset_type: "STOCK",
    market: "TWSE",
    currency: "TWD",
    sector: "Technology",
    industry: "Semiconductor Packaging",
    valuation_method: "TRANSACTION_BASED",
    is_demo_data: true,
    needs_review: false,
  },
];

export const mockPortfolioSummary = {
  total_market_value: "135750.00000000",
  remaining_cost_basis: "185264.00000000",
  realized_pnl: "51.00000000",
  unrealized_pnl: "-49514.00000000",
  total_pnl: "-49463.00000000",
  total_return_pct: "-0.2672618533552120217635374385",
  total_dividends_received: "120.00000000",
  total_fees_paid: "304.00",
  total_tax_paid: "9.00",
  holdings_count: 4,
};

export const mockHoldings = [
  {
    account_id: 1,
    asset_id: 1,
    ticker: "3653",
    asset_name: "健策",
    valuation_method: "TRANSACTION_BASED",
    remaining_shares: "15.0000",
    average_cost: "628.8000",
    remaining_cost_basis: "9432.00000000",
    latest_close: "650.0000",
    price_as_of: "2026-08-28",
    market_value: "9750.00000000",
    unrealized_pnl: "318.00000000",
    realized_pnl: "51.00000000",
    total_pnl: "369.00000000",
    return_pct: "0.03371501272264631043256997455",
    weight: "1",
    total_dividends_received: "120.00000000",
    total_fees_paid: "222.00",
    total_tax_paid: "9.00",
  },
];

export const mockAllocation = {
  total_market_value: "9750.00000000",
  entries: [
    { account_id: 1, asset_id: 1, ticker: "3653", asset_name: "健策", market_value: "9750.00000000", weight: "1" },
  ],
};

export const mockPerformance = {
  total_market_value: "9750.00000000",
  remaining_cost_basis: "9432.00000000",
  realized_pnl: "51.00000000",
  unrealized_pnl: "318.00000000",
  total_pnl: "369.00000000",
  total_return_pct: "0.033",
  note: "Snapshot only — historical time-series performance is not implemented in V1.",
};

export const mockWatchlist = [
  {
    id: 1,
    asset_id: 3,
    ticker: "3491",
    asset_name: "昇達科",
    status: "RESEARCHING",
    reason: "RF component demand",
    target_metrics: null,
    entry_consideration: null,
    review_date: "2026-10-01",
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
  },
];

export const handlers = [
  http.get(`${API_URL}/api/accounts`, () => HttpResponse.json(mockAccounts)),
  http.get(`${API_URL}/api/assets`, () => HttpResponse.json(mockAssets)),
  http.get(`${API_URL}/api/portfolio`, () => HttpResponse.json(mockPortfolioSummary)),
  http.get(`${API_URL}/api/holdings`, () => HttpResponse.json(mockHoldings)),
  http.get(`${API_URL}/api/analytics/allocation`, () => HttpResponse.json(mockAllocation)),
  http.get(`${API_URL}/api/analytics/performance`, () => HttpResponse.json(mockPerformance)),
  http.get(`${API_URL}/api/watchlist`, () => HttpResponse.json(mockWatchlist)),
  http.get(`${API_URL}/api/transactions`, () => HttpResponse.json([])),
  http.post(`${API_URL}/api/transactions`, () =>
    HttpResponse.json({ detail: "Cannot sell 999 units of asset 4: only 3.0000 available." }, { status: 400 }),
  ),
];
