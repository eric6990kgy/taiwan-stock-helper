"""FinMind adapter (Phase 5B) -- the chosen primary real market-data source
per the Phase 5 Discovery Report. This is the ONLY file in the codebase that
knows FinMind's response shape (field names like `Trading_Volume`, `PER`,
`CashEarningsDistribution`); everything above the MarketDataProvider
interface -- services, repositories, routes, frontend -- only ever sees the
normalized DTOs (Sec.7 "Provider Adapter" boundary).

Data-use note: FinMind's own README restricts the *data* (not the client
code, which is Apache-2.0) to educational/non-commercial use. This app is
personal, single-user, non-commercial, non-redistributed -- consistent with
that restriction. See README.md's "Market Data" section.

Field mappings were verified against FinMind's live API (not guessed from
docs) on 2026-08-31:
  TaiwanStockPrice              -> OHLCV (Trading_Volume, Trading_money=value)
  TaiwanStockPER                -> PER, PBR, dividend_yield (free tier OK)
  TaiwanStockMarketValue        -> market_value (REQUIRES PAID TIER -- a 400
                                    "Your level is free" response is expected
                                    and handled as "unavailable", not an error)
  TaiwanStockInfo                -> company name/industry/market
  TaiwanStockDividend            -> ex-dividend/payment dates, cash/stock amounts
  TaiwanStockFinancialStatements -> Revenue, GrossProfit, OperatingIncome,
                                     IncomeAfterTaxes, EPS (flat type/value rows)
  TaiwanStockBalanceSheet        -> TotalAssets, Liabilities,
                                     EquityAttributableToOwnersOfParent
  TaiwanStockCashFlowsStatement  -> CashFlowsFromOperatingActivities,
                                     PropertyAndPlantAndEquipment (capex, signed negative)

Field mappings for the three Phase 6 datasets were verified the same way
(live API calls, not docs) on 2026-08-31:
  TaiwanStockInstitutionalInvestorsBuySell -> long-format rows (one per
    date x category); `name` is one of Foreign_Investor, Foreign_Dealer_Self,
    Investment_Trust, Dealer_self, Dealer_Hedging. buy/sell are in shares
    (cross-checked: Foreign_Investor buy/sell for 2330 is the same order of
    magnitude as that day's TaiwanStockPrice Trading_Volume).
  TaiwanStockMarginPurchaseShortSale -> wide-format rows, one per date.
    All fields are in 張 (board lots, 1,000 shares) -- cross-checked
    MarginPurchaseTodayBalance for 2330 against TWSE's own published 融資餘額
    for the same date (matching order of magnitude, ~27-28k; raw shares
    would be ~1000x too large for this ticker).
  TaiwanStockMonthRevenue -> `date` is the first of the *announcement*
    month (Taiwan requires monthly revenue be filed by the 10th of the
    following month); revenue_month/revenue_year identify the *covered*
    month, which is what this app keys on, not `date`.
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import httpx

from app.config import FINMIND_API_TOKEN, FINMIND_API_URL
from app.providers.market_data_provider import (
    AssetNotFoundError,
    CompanyInfoDTO,
    DividendDTO,
    FundamentalsDTO,
    InstitutionalFlowDTO,
    MarginTradingDTO,
    MarketDataProvider,
    MonthlyRevenueDTO,
    PricePointDTO,
    ProviderError,
    QuoteDTO,
    RateLimitError,
    ValuationDTO,
)

SOURCE = "FINMIND"
DEFAULT_HISTORY_START = date(2010, 1, 1)  # FinMind's own price history starts 1994, but
# 2010+ covers everything this app's seed tickers need without an oversized default pull.


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# FinMind's five raw institutional-investor categories, grouped into the
# conventional TWSE three-way 三大法人 split.
_FOREIGN_CATEGORIES = ("Foreign_Investor", "Foreign_Dealer_Self")
_INVESTMENT_TRUST_CATEGORIES = ("Investment_Trust",)
_DEALER_CATEGORIES = ("Dealer_self", "Dealer_Hedging")


def _quarter_label(d: date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


class FinMindProvider(MarketDataProvider):
    def __init__(self, client: httpx.Client | None = None, token: str | None = None):
        self._client = client or httpx.Client(timeout=15.0)
        self._owns_client = client is None
        self._token = FINMIND_API_TOKEN if token is None else token

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ---- transport --------------------------------------------------------

    def _request(self, dataset: str, data_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict]:
        params: dict[str, str] = {"dataset": dataset}
        if data_id is not None:
            params["data_id"] = data_id
        if start_date is not None:
            params["start_date"] = start_date.isoformat()
        if end_date is not None:
            params["end_date"] = end_date.isoformat()
        if self._token:
            params["token"] = self._token

        try:
            response = self._client.get(FINMIND_API_URL, params=params)
        except httpx.HTTPError as exc:
            raise ProviderError(f"FinMind request failed for dataset {dataset!r}: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderError(f"FinMind returned a non-JSON response for dataset {dataset!r} (HTTP {response.status_code})") from exc

        status = body.get("status")
        if status == 402:
            raise RateLimitError(body.get("msg", "FinMind rate limit exceeded."))
        if status != 200:
            raise ProviderError(f"FinMind error on dataset {dataset!r}: {body.get('msg', 'unknown error')} (status {status})")
        return body.get("data", [])

    # ---- MarketDataProvider ------------------------------------------------

    def get_quote(self, ticker: str) -> QuoteDTO:
        end = date.today()
        start = end - timedelta(days=380)  # covers a trailing 52 weeks even across holidays
        rows = self._request("TaiwanStockPrice", data_id=ticker, start_date=start, end_date=end)
        if not rows:
            raise AssetNotFoundError(ticker)

        rows = sorted(rows, key=lambda r: r["date"])
        latest = rows[-1]
        closes = [_to_decimal(r.get("close")) for r in rows]
        closes = [c for c in closes if c is not None]

        return QuoteDTO(
            ticker=ticker,
            price=_to_decimal(latest["close"]),
            as_of=_to_date(latest["date"]),
            high_52w=max(closes) if closes else None,
            low_52w=min(closes) if closes else None,
        )

    def get_historical_prices(self, ticker: str, start: date | None = None, end: date | None = None) -> list[PricePointDTO]:
        rows = self._request(
            "TaiwanStockPrice", data_id=ticker, start_date=start or DEFAULT_HISTORY_START, end_date=end or date.today()
        )
        return [
            PricePointDTO(
                date=_to_date(r["date"]),
                open=_to_decimal(r.get("open")),
                high=_to_decimal(r.get("max")),
                low=_to_decimal(r.get("min")),
                close=_to_decimal(r.get("close")),
                volume=int(r["Trading_Volume"]) if r.get("Trading_Volume") not in (None, "") else None,
                source=SOURCE,
                adjusted_close=None,  # FinMind's TaiwanStockPrice does not expose a distinct adjusted-close field
                trading_value=_to_decimal(r.get("Trading_money")),
            )
            for r in rows
        ]

    def get_company_info(self, ticker: str) -> CompanyInfoDTO:
        rows = self._request("TaiwanStockInfo", data_id=ticker)
        if not rows:
            raise AssetNotFoundError(ticker)
        latest = rows[-1]
        market_type = (latest.get("type") or "").lower()
        market = {"twse": "TWSE", "tpex": "TPEX"}.get(market_type, market_type.upper() or None)

        return CompanyInfoDTO(
            ticker=ticker,
            name=latest.get("stock_name", ticker),
            asset_type="STOCK",
            market=market,
            sector=latest.get("industry_category"),
            industry=latest.get("industry_category"),
            is_demo_data=False,
        )

    def get_fundamentals(self, ticker: str) -> list[FundamentalsDTO]:
        start = date.today() - timedelta(days=365 * 3)
        end = date.today()

        income_rows = self._request("TaiwanStockFinancialStatements", data_id=ticker, start_date=start, end_date=end)
        balance_rows = self._request("TaiwanStockBalanceSheet", data_id=ticker, start_date=start, end_date=end)
        cashflow_rows = self._request("TaiwanStockCashFlowsStatement", data_id=ticker, start_date=start, end_date=end)

        income_by_date = _pivot_by_date(income_rows)
        balance_by_date = _pivot_by_date(balance_rows)
        cashflow_by_date = _pivot_by_date(cashflow_rows)

        results = []
        for period_date in sorted(income_by_date):
            income = income_by_date[period_date]
            balance = balance_by_date.get(period_date, {})
            cashflow = cashflow_by_date.get(period_date, {})

            revenue = income.get("Revenue")
            gross_profit = income.get("GrossProfit")
            operating_income = income.get("OperatingIncome")
            net_income = income.get("IncomeAfterTaxes")
            total_assets = balance.get("TotalAssets")
            liabilities = balance.get("Liabilities")
            equity = balance.get("EquityAttributableToOwnersOfParent") or balance.get("Equity")
            operating_cash_flow = cashflow.get("CashFlowsFromOperatingActivities") or cashflow.get(
                "NetCashInflowFromOperatingActivities"
            )
            capex = cashflow.get("PropertyAndPlantAndEquipment")  # signed negative = cash outflow

            results.append(
                FundamentalsDTO(
                    period=_quarter_label(period_date),
                    revenue=revenue,
                    eps=income.get("EPS"),
                    gross_margin=_safe_ratio(gross_profit, revenue),
                    operating_margin=_safe_ratio(operating_income, revenue),
                    net_margin=_safe_ratio(net_income, revenue),
                    roe=_safe_ratio(net_income, equity),
                    roa=_safe_ratio(net_income, total_assets),
                    debt_ratio=_safe_ratio(liabilities, total_assets),
                    operating_cash_flow=operating_cash_flow,
                    free_cash_flow=(operating_cash_flow + capex) if operating_cash_flow is not None and capex is not None else None,
                    source=SOURCE,
                )
            )
        return results

    def get_dividends(self, ticker: str, start: date | None = None, end: date | None = None) -> list[DividendDTO]:
        rows = self._request(
            "TaiwanStockDividend", data_id=ticker, start_date=start or DEFAULT_HISTORY_START, end_date=end or date.today()
        )
        results = []
        for r in rows:
            ex_date = _to_date(r.get("CashExDividendTradingDate")) or _to_date(r.get("StockExDividendTradingDate"))
            if ex_date is None:
                continue  # announced but no ex-dividend date fixed yet -- nothing to key the row on

            cash = _to_decimal(r.get("CashEarningsDistribution"))
            stock = _to_decimal(r.get("StockEarningsDistribution"))
            if not cash and not stock:
                continue  # a zero/empty distribution row -- nothing to record

            results.append(
                DividendDTO(
                    ex_dividend_date=ex_date,
                    payment_date=_to_date(r.get("CashDividendPaymentDate")),
                    cash_dividend=cash or None,
                    stock_dividend=stock or None,
                    source=SOURCE,
                )
            )
        return results

    def get_valuation(self, ticker: str, on_date: date | None = None) -> ValuationDTO:
        end = on_date or date.today()
        start = end - timedelta(days=10)  # a small trailing window in case on_date isn't a trading day
        rows = self._request("TaiwanStockPER", data_id=ticker, start_date=start, end_date=end)
        if not rows:
            raise AssetNotFoundError(ticker)
        latest = sorted(rows, key=lambda r: r["date"])[-1]

        market_cap = None
        shares_outstanding = None
        try:
            mv_rows = self._request("TaiwanStockMarketValue", data_id=ticker, start_date=start, end_date=end)
            if mv_rows:
                mv_latest = sorted(mv_rows, key=lambda r: r["date"])[-1]
                market_cap = _to_decimal(mv_latest.get("market_value"))
        except ProviderError:
            # Documented, expected limitation: TaiwanStockMarketValue requires
            # a paid FinMind tier (Phase 5 Discovery Report Sec.4/15). Not
            # having market cap is not a failure of the whole valuation call.
            pass

        return ValuationDTO(
            date=_to_date(latest["date"]),
            pe_ratio=_to_decimal(latest.get("PER")),
            pb_ratio=_to_decimal(latest.get("PBR")),
            dividend_yield=_to_decimal(latest.get("dividend_yield")),
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
            source=SOURCE,
        )

    def get_institutional_flows(
        self, ticker: str, start: date | None = None, end: date | None = None
    ) -> list[InstitutionalFlowDTO]:
        rows = self._request(
            "TaiwanStockInstitutionalInvestorsBuySell",
            data_id=ticker,
            start_date=start or DEFAULT_HISTORY_START,
            end_date=end or date.today(),
        )

        by_date: dict[date, dict[str, dict[str, int]]] = {}
        for r in rows:
            d = _to_date(r.get("date"))
            if d is None:
                continue
            by_date.setdefault(d, {})[r["name"]] = {
                "buy": _to_int(r.get("buy")) or 0,
                "sell": _to_int(r.get("sell")) or 0,
            }

        def _bucket_sum(categories_by_name: dict[str, dict[str, int]], names: tuple[str, ...], key: str) -> int | None:
            # Require every category in the bucket to be present -- a bucket
            # missing one of its categories (e.g. Dealer_Hedging without
            # Dealer_self) is incomplete, not "zero for the missing part";
            # summing what's there would silently understate the bucket.
            if not all(n in categories_by_name for n in names):
                return None
            return sum(categories_by_name[n][key] for n in names)

        results = []
        for d in sorted(by_date):
            categories = by_date[d]
            foreign_buy = _bucket_sum(categories, _FOREIGN_CATEGORIES, "buy")
            foreign_sell = _bucket_sum(categories, _FOREIGN_CATEGORIES, "sell")
            trust_buy = _bucket_sum(categories, _INVESTMENT_TRUST_CATEGORIES, "buy")
            trust_sell = _bucket_sum(categories, _INVESTMENT_TRUST_CATEGORIES, "sell")
            dealer_buy = _bucket_sum(categories, _DEALER_CATEGORIES, "buy")
            dealer_sell = _bucket_sum(categories, _DEALER_CATEGORIES, "sell")

            foreign_net = (foreign_buy - foreign_sell) if foreign_buy is not None and foreign_sell is not None else None
            trust_net = (trust_buy - trust_sell) if trust_buy is not None and trust_sell is not None else None
            dealer_net = (dealer_buy - dealer_sell) if dealer_buy is not None and dealer_sell is not None else None
            nets = [n for n in (foreign_net, trust_net, dealer_net) if n is not None]
            # total_net only when every bucket that FinMind covered for this
            # date could be netted -- a partial day never gets a fabricated total.
            total_net = sum(nets) if len(nets) == 3 else None

            results.append(
                InstitutionalFlowDTO(
                    date=d,
                    foreign_buy=foreign_buy,
                    foreign_sell=foreign_sell,
                    foreign_net=foreign_net,
                    investment_trust_buy=trust_buy,
                    investment_trust_sell=trust_sell,
                    investment_trust_net=trust_net,
                    dealer_buy=dealer_buy,
                    dealer_sell=dealer_sell,
                    dealer_net=dealer_net,
                    total_net=total_net,
                    source=SOURCE,
                )
            )
        return results

    def get_margin_trading(
        self, ticker: str, start: date | None = None, end: date | None = None
    ) -> list[MarginTradingDTO]:
        rows = self._request(
            "TaiwanStockMarginPurchaseShortSale",
            data_id=ticker,
            start_date=start or DEFAULT_HISTORY_START,
            end_date=end or date.today(),
        )
        results = []
        for r in sorted(rows, key=lambda r: r["date"]):
            results.append(
                MarginTradingDTO(
                    date=_to_date(r["date"]),
                    margin_buy=_to_int(r.get("MarginPurchaseBuy")),
                    margin_sell=_to_int(r.get("MarginPurchaseSell")),
                    margin_cash_repayment=_to_int(r.get("MarginPurchaseCashRepayment")),
                    margin_balance=_to_int(r.get("MarginPurchaseTodayBalance")),
                    short_sale_buy=_to_int(r.get("ShortSaleBuy")),
                    short_sale_sell=_to_int(r.get("ShortSaleSell")),
                    short_sale_cash_repayment=_to_int(r.get("ShortSaleCashRepayment")),
                    short_sale_balance=_to_int(r.get("ShortSaleTodayBalance")),
                    source=SOURCE,
                )
            )
        return results

    def get_monthly_revenue(self, ticker: str) -> list[MonthlyRevenueDTO]:
        start = date.today() - timedelta(days=365 * 3)
        end = date.today()
        rows = self._request("TaiwanStockMonthRevenue", data_id=ticker, start_date=start, end_date=end)

        results = []
        for r in rows:
            revenue = _to_decimal(r.get("revenue"))
            month = _to_int(r.get("revenue_month"))
            year = _to_int(r.get("revenue_year"))
            if revenue is None or month is None or year is None:
                continue  # an incomplete row can't be keyed -- skip rather than guess
            results.append(
                MonthlyRevenueDTO(
                    revenue_year=year,
                    revenue_month=month,
                    revenue=revenue,
                    announcement_date=_to_date(r.get("date")),
                    source=SOURCE,
                )
            )
        return sorted(results, key=lambda r: (r.revenue_year, r.revenue_month))


def _pivot_by_date(rows: list[dict]) -> dict[date, dict[str, Decimal]]:
    """FinMind's statement datasets are flat {date, type, value} rows (one
    metric per row) rather than one wide row per period -- pivot them into
    {date: {type: value}} so callers can look up named metrics directly."""
    pivoted: dict[date, dict[str, Decimal]] = {}
    for row in rows:
        d = _to_date(row.get("date"))
        if d is None:
            continue
        value = _to_decimal(row.get("value"))
        if value is None:
            continue
        pivoted.setdefault(d, {})[row["type"]] = value
    return pivoted


def _safe_ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator
