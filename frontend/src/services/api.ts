import type {
  Account,
  AccountType,
  AgentRole,
  Allocation,
  Asset,
  Holding,
  ImportResult,
  InstitutionalFlow,
  JournalCategory,
  JournalEntry,
  MarginTrading,
  MarketDataUpdateResult,
  MonthlyRevenue,
  PendingStrategyChange,
  Performance,
  PortfolioSummary,
  PricePoint,
  Recommendation,
  RecommendationOutcome,
  ResearchPage,
  ReviewSummary,
  Risk,
  Score,
  ScreenerResult,
  SignalResult,
  StrategyVersion,
  TechnicalIndicators,
  Thesis,
  TickerLookup,
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

/** FastAPI's own validation errors (422) return `detail` as an array of
 * `{loc, msg, type}` objects, not a string -- passing that straight to
 * `Error`'s constructor stringifies it as "[object Object]". Join each
 * item's `msg` (falling back to JSON if the shape is ever unexpected)
 * so the UI always shows readable text. */
function formatDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) =>
      item && typeof item === "object" && "msg" in item ? String((item as { msg: unknown }).msg) : JSON.stringify(item),
    );
    if (messages.length > 0) return messages.join("; ");
  }
  if (detail != null) return JSON.stringify(detail);
  return fallback;
}

async function parseResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const body = await res.json();
      detail = formatDetail(body.detail, res.statusText);
    } catch {
      // response wasn't JSON -- keep statusText
    }
    throw new ApiRequestError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  return parseResponse<T>(res);
}

/** Like `request`, but for a `FormData` body (multipart file upload) --
 * omits the JSON Content-Type so the browser can set its own multipart
 * boundary header instead. */
async function postForm<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { method: "POST", body: formData });
  return parseResponse<T>(res);
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
}

// ---- Accounts ---------------------------------------------------------------

export const accountsApi = {
  list: () => request<Account[]>("/api/accounts"),
  create: (body: { name: string; account_type: AccountType; currency?: string }) =>
    request<Account>("/api/accounts", { method: "POST", body: JSON.stringify(body) }),
  update: (id: number, body: Partial<{ name: string; account_type: AccountType }>) =>
    request<Account>(`/api/accounts/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  delete: (id: number) => request<void>(`/api/accounts/${id}`, { method: "DELETE" }),
};

// ---- Assets -------------------------------------------------------------------

export const assetsApi = {
  list: () => request<Asset[]>("/api/assets"),
  getByTicker: (ticker: string) => request<Asset>(`/api/assets/${encodeURIComponent(ticker)}`),
  lookup: (ticker: string) => request<TickerLookup>(`/api/assets/lookup/${encodeURIComponent(ticker)}`),
  quickCreate: (ticker: string) =>
    request<Asset>("/api/assets/quick-create", { method: "POST", body: JSON.stringify({ ticker }) }),
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
  institutionalFlows: (ticker: string, range?: string) =>
    request<InstitutionalFlow[]>(`/api/research/${encodeURIComponent(ticker)}/institutional${qs({ range })}`),
  marginTrading: (ticker: string, range?: string) =>
    request<MarginTrading[]>(`/api/research/${encodeURIComponent(ticker)}/margin${qs({ range })}`),
  monthlyRevenue: (ticker: string) =>
    request<MonthlyRevenue[]>(`/api/research/${encodeURIComponent(ticker)}/revenue`),
  technicalIndicators: (ticker: string, asOf?: string) =>
    request<TechnicalIndicators>(`/api/research/${encodeURIComponent(ticker)}/technical${qs({ as_of: asOf })}`),
  score: (ticker: string) => request<Score | null>(`/api/research/${encodeURIComponent(ticker)}/score`),
  scoreHistory: (ticker: string, range?: string) =>
    request<Score[]>(`/api/research/${encodeURIComponent(ticker)}/scores${qs({ range })}`),
  signals: (ticker: string, asOf?: string) =>
    request<SignalResult>(`/api/research/${encodeURIComponent(ticker)}/signals${qs({ as_of: asOf })}`),
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
  screen: (params: {
    revenue_growth_gt?: number;
    roe_gt?: number;
    pe_lt?: number;
    foreign_net_buy_gt?: number;
    rsi_lt?: number;
    rsi_gt?: number;
    above_sma_20?: boolean;
    composite_score_gt?: number;
  }) => request<ScreenerResult[]>(`/api/screener${qs(params)}`),
};

// ---- Market Data (Phase 5B) -------------------------------------------------

export const marketDataApi = {
  update: () => request<MarketDataUpdateResult>("/api/market-data/update", { method: "POST" }),
};

// ---- Phase 8: risk-gated recommendation engine ----------------------------

export const recommendationsApi = {
  list: (since?: string) => request<Recommendation[]>(`/api/recommendations${qs({ since })}`),
};

export const strategyApi = {
  listVersions: () => request<StrategyVersion[]>("/api/strategy/versions"),
  proposeChange: (body: { proposed_rules: Record<string, unknown>; reason: string }) =>
    request<StrategyVersion | PendingStrategyChange>("/api/strategy/versions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listPending: (status?: string) => request<PendingStrategyChange[]>(`/api/strategy/pending${qs({ status })}`),
  confirmPending: (id: number) =>
    request<StrategyVersion>(`/api/strategy/pending/${id}/confirm`, { method: "POST" }),
  rejectPending: (id: number) =>
    request<PendingStrategyChange>(`/api/strategy/pending/${id}/reject`, { method: "POST" }),
};

// ---- CSV Import/Export ------------------------------------------------------

/** Export routes are plain GETs that return `Content-Disposition:
 * attachment` -- a real `<a href download>` link triggers a browser
 * download with no fetch/blob plumbing needed, so these are just the URLs. */
export const exportUrls = {
  transactions: `${API_URL}/api/export/transactions`,
  holdings: `${API_URL}/api/export/holdings`,
  portfolioSnapshot: `${API_URL}/api/export/portfolio-snapshot`,
};

export const importExportApi = {
  importTransactions: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return postForm<ImportResult>("/api/import/transactions", formData);
  },
};

// ---- Phase 10: review (複盤) + journal (日誌) --------------------------------

export const reviewApi = {
  summary: (action?: string) => request<ReviewSummary>(`/api/review/summary${qs({ action })}`),
  outcomes: (action?: string) => request<RecommendationOutcome[]>(`/api/review/outcomes${qs({ action })}`),
};

export const journalApi = {
  list: (params: { asset_id?: number; category?: JournalCategory; date_from?: string; date_to?: string } = {}) =>
    request<JournalEntry[]>(`/api/journal${qs(params)}`),
  create: (body: { entry_date?: string; category?: JournalCategory; asset_id?: number; body: string }) =>
    request<JournalEntry>("/api/journal", { method: "POST", body: JSON.stringify(body) }),
  update: (id: number, body: Partial<{ entry_date: string; category: JournalCategory; asset_id: number; body: string }>) =>
    request<JournalEntry>(`/api/journal/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  delete: (id: number) => request<void>(`/api/journal/${id}`, { method: "DELETE" }),
};

// ---- Phase 12: Gemini multi-agent research team ---------------------------

export const agentPerformanceApi = {
  summary: (role?: AgentRole) => request<ReviewSummary>(`/api/agent-performance/summary${qs({ role })}`),
};
