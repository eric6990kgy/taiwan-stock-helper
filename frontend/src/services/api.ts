import type {
  Account,
  Allocation,
  Asset,
  Holding,
  Performance,
  PortfolioSummary,
  PricePoint,
  ResearchPage,
  Risk,
  ScreenerResult,
  Thesis,
  Transaction,
  WatchlistEntry,
} from "../types/api";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export class ApiRequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON -- keep statusText
    }
    throw new ApiRequestError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
}

// ---- Accounts ---------------------------------------------------------------

export const accountsApi = {
  list: () => request<Account[]>("/api/accounts"),
  create: (body: { name: string; account_type: string; currency?: string }) =>
    request<Account>("/api/accounts", { method: "POST", body: JSON.stringify(body) }),
};

// ---- Assets -------------------------------------------------------------------

export const assetsApi = {
  list: () => request<Asset[]>("/api/assets"),
  getByTicker: (ticker: string) => request<Asset>(`/api/assets/${encodeURIComponent(ticker)}`),
};

// ---- Transactions ---------------------------------------------------------------

export interface TransactionFilters {
  account_id?: number;
  asset_id?: number;
  type?: string;
  date_from?: string;
  date_to?: string;
  [key: string]: string | number | undefined;
}

export const transactionsApi = {
  list: (filters: TransactionFilters = {}) => request<Transaction[]>(`/api/transactions${qs(filters)}`),
  create: (body: {
    account_id: number;
    asset_id: number;
    date: string;
    type: string;
    quantity: string;
    price: string;
    fee?: string;
    tax?: string;
    currency?: string;
    note?: string;
  }) => request<Transaction>("/api/transactions", { method: "POST", body: JSON.stringify(body) }),
  update: (id: number, body: Partial<{ date: string; type: string; quantity: string; price: string; fee: string; tax: string; note: string }>) =>
    request<Transaction>(`/api/transactions/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  delete: (id: number) => request<void>(`/api/transactions/${id}`, { method: "DELETE" }),
};

// ---- Portfolio / Holdings -------------------------------------------------------

export const portfolioApi = {
  summary: () => request<PortfolioSummary>("/api/portfolio"),
  holdings: (accountId?: number) => request<Holding[]>(`/api/holdings${qs({ account_id: accountId })}`),
};

// ---- Research -------------------------------------------------------------------

export const researchApi = {
  page: (ticker: string) => request<ResearchPage>(`/api/research/${encodeURIComponent(ticker)}`),
  prices: (ticker: string, range?: string) =>
    request<PricePoint[]>(`/api/prices/${encodeURIComponent(ticker)}${qs({ range })}`),
};

// ---- Watchlist ------------------------------------------------------------------

export const watchlistApi = {
  list: (status?: string) => request<WatchlistEntry[]>(`/api/watchlist${qs({ status })}`),
  create: (body: {
    asset_id: number;
    status?: string;
    reason?: string;
    target_metrics?: Record<string, unknown>;
    entry_consideration?: string;
    review_date?: string;
  }) => request<WatchlistEntry>("/api/watchlist", { method: "POST", body: JSON.stringify(body) }),
  update: (id: number, body: Partial<{ status: string; reason: string; entry_consideration: string; review_date: string }>) =>
    request<WatchlistEntry>(`/api/watchlist/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  delete: (id: number) => request<void>(`/api/watchlist/${id}`, { method: "DELETE" }),
};

// ---- Thesis ---------------------------------------------------------------------

export const thesisApi = {
  get: (ticker: string) => request<Thesis>(`/api/thesis/${encodeURIComponent(ticker)}`),
  upsert: (
    ticker: string,
    body: { thesis?: string; catalysts?: string; risks?: string; status?: string; last_reviewed?: string },
  ) => request<Thesis>(`/api/thesis/${encodeURIComponent(ticker)}`, { method: "PUT", body: JSON.stringify(body) }),
};

// ---- Analytics ------------------------------------------------------------------

export const analyticsApi = {
  allocation: () => request<Allocation>("/api/analytics/allocation"),
  performance: () => request<Performance>("/api/analytics/performance"),
  risk: () => request<Risk>("/api/analytics/risk"),
};

// ---- Screener -------------------------------------------------------------------

export const screenerApi = {
  screen: (params: { revenue_growth_gt?: number; roe_gt?: number; pe_lt?: number }) =>
    request<ScreenerResult[]>(`/api/screener${qs(params)}`),
};
