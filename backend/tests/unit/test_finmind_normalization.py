"""FinMind adapter normalization tests. All HTTP calls are mocked with
httpx.MockTransport using response shapes captured from FinMind's live API
on 2026-08-31 (see finmind_provider.py's module docstring) -- no network
access, fully deterministic and offline.
"""

from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.providers.finmind_provider import FinMindProvider
from app.providers.market_data_provider import AssetNotFoundError, ProviderError, RateLimitError

PRICE_ROWS = [
    {
        "date": "2026-08-27",
        "stock_id": "2330",
        "Trading_Volume": 19214481,
        "Trading_money": 46545167227,
        "open": 2430.0,
        "max": 2435.0,
        "min": 2410.0,
        "close": 2410.0,
        "spread": -5.0,
        "Trading_turnover": 60122,
    },
    {
        "date": "2026-08-28",
        "stock_id": "2330",
        "Trading_Volume": 15025832,
        "Trading_money": 36465015980,
        "open": 2440.0,
        "max": 2445.0,
        "min": 2410.0,
        "close": 2420.0,
        "spread": 10.0,
        "Trading_turnover": 52492,
    },
]

PER_ROWS = [{"date": "2026-08-28", "stock_id": "2330", "dividend_yield": 0.91, "PER": 28.05, "PBR": 9.76}]

INFO_ROWS = [
    {"industry_category": "半導體業", "stock_id": "2330", "stock_name": "台積電", "type": "twse", "date": "2026-08-31"}
]

DIVIDEND_ROWS = [
    {
        "date": "2024-03-24",
        "stock_id": "2330",
        "CashEarningsDistribution": 3.49978969,
        "StockEarningsDistribution": 0.0,
        "CashExDividendTradingDate": "2024-03-18",
        "StockExDividendTradingDate": "",
        "CashDividendPaymentDate": "2024-04-11",
    },
    {
        # No ex-dividend date fixed yet -- must be skipped, not crash.
        "date": "2026-06-01",
        "stock_id": "2330",
        "CashEarningsDistribution": 0.0,
        "StockEarningsDistribution": 0.0,
        "CashExDividendTradingDate": "",
        "StockExDividendTradingDate": "",
        "CashDividendPaymentDate": "",
    },
]

FINANCIAL_STATEMENT_ROWS = [
    {"date": "2026-03-31", "stock_id": "2330", "type": "EPS", "value": 22.08, "origin_name": "x"},
    {"date": "2026-03-31", "stock_id": "2330", "type": "Revenue", "value": 1134103440000.0, "origin_name": "x"},
    {"date": "2026-03-31", "stock_id": "2330", "type": "GrossProfit", "value": 751295421000.0, "origin_name": "x"},
    {"date": "2026-03-31", "stock_id": "2330", "type": "OperatingIncome", "value": 658966142000.0, "origin_name": "x"},
    {"date": "2026-03-31", "stock_id": "2330", "type": "IncomeAfterTaxes", "value": 572801304000.0, "origin_name": "x"},
]

BALANCE_SHEET_ROWS = [
    {"date": "2026-03-31", "stock_id": "2330", "type": "TotalAssets", "value": 8660949685000.0},
    {"date": "2026-03-31", "stock_id": "2330", "type": "Liabilities", "value": 2728560764000.0},
    {"date": "2026-03-31", "stock_id": "2330", "type": "EquityAttributableToOwnersOfParent", "value": 5890960252000.0},
]

CASH_FLOW_ROWS = [
    {"date": "2026-03-31", "stock_id": "2330", "type": "CashFlowsFromOperatingActivities", "value": 698976265000.0},
    {"date": "2026-03-31", "stock_id": "2330", "type": "PropertyAndPlantAndEquipment", "value": -350762799000.0},
]

# Captured from FinMind's live API on 2026-08-31 (see finmind_provider.py's
# module docstring for how the units were cross-checked).
INSTITUTIONAL_ROWS = [
    {"date": "2026-08-27", "stock_id": "2330", "name": "Foreign_Investor", "buy": 14070814, "sell": 9570219},
    {"date": "2026-08-27", "stock_id": "2330", "name": "Foreign_Dealer_Self", "buy": 0, "sell": 0},
    {"date": "2026-08-27", "stock_id": "2330", "name": "Investment_Trust", "buy": 41754, "sell": 359218},
    {"date": "2026-08-27", "stock_id": "2330", "name": "Dealer_self", "buy": 22210, "sell": 70050},
    {"date": "2026-08-27", "stock_id": "2330", "name": "Dealer_Hedging", "buy": 266650, "sell": 61309},
]

MARGIN_ROWS = [
    {
        "date": "2026-08-20",
        "stock_id": "2330",
        "MarginPurchaseBuy": 315,
        "MarginPurchaseCashRepayment": 11,
        "MarginPurchaseLimit": 6483092,
        "MarginPurchaseSell": 418,
        "MarginPurchaseTodayBalance": 28308,
        "MarginPurchaseYesterdayBalance": 28422,
        "Note": " ",
        "OffsetLoanAndShort": 0,
        "ShortSaleBuy": 1,
        "ShortSaleCashRepayment": 0,
        "ShortSaleLimit": 6483092,
        "ShortSaleSell": 2,
        "ShortSaleTodayBalance": 30,
        "ShortSaleYesterdayBalance": 29,
    }
]

MONTH_REVENUE_ROWS = [
    {
        "date": "2026-08-01",
        "stock_id": "2330",
        "country": "Taiwan",
        "revenue": 467580548000,
        "revenue_month": 7,
        "revenue_year": 2026,
        "create_time": "2026-08-10",
    }
]


def make_provider(handler) -> FinMindProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FinMindProvider(client=client)


def dataset_router(mapping: dict[str, list[dict] | dict]):
    """Builds an httpx.MockTransport handler that returns canned rows keyed
    by the `dataset` query param -- `mapping` values that are already a full
    response dict (status/msg) are returned as-is; plain lists are wrapped
    in a success envelope."""

    def handler(request: httpx.Request) -> httpx.Response:
        dataset = request.url.params.get("dataset")
        payload = mapping.get(dataset, [])
        if isinstance(payload, dict):
            return httpx.Response(200, json=payload)
        return httpx.Response(200, json={"msg": "success", "status": 200, "data": payload})

    return handler


# ---- get_quote --------------------------------------------------------------


def test_get_quote_normalizes_latest_row():
    provider = make_provider(dataset_router({"TaiwanStockPrice": PRICE_ROWS}))
    quote = provider.get_quote("2330")

    assert quote.ticker == "2330"
    assert quote.price == Decimal("2420.0")
    assert quote.as_of == date(2026, 8, 28)
    assert quote.high_52w == Decimal("2420.0")
    assert quote.low_52w == Decimal("2410.0")


def test_get_quote_unknown_ticker_raises_asset_not_found():
    provider = make_provider(dataset_router({"TaiwanStockPrice": []}))
    with pytest.raises(AssetNotFoundError):
        provider.get_quote("9999999")


# ---- get_historical_prices ----------------------------------------------------


def test_get_historical_prices_maps_finmind_field_names():
    provider = make_provider(dataset_router({"TaiwanStockPrice": PRICE_ROWS}))
    points = provider.get_historical_prices("2330")

    assert len(points) == 2
    first = points[0]
    assert first.date == date(2026, 8, 27)
    assert first.open == Decimal("2430.0")
    assert first.high == Decimal("2435.0")  # FinMind calls this "max"
    assert first.low == Decimal("2410.0")  # FinMind calls this "min"
    assert first.close == Decimal("2410.0")
    assert first.volume == 19214481  # FinMind calls this "Trading_Volume"
    assert first.trading_value == Decimal("46545167227")  # FinMind calls this "Trading_money"
    assert first.source == "FINMIND"


# ---- get_company_info ---------------------------------------------------------


def test_get_company_info_maps_market_type():
    provider = make_provider(dataset_router({"TaiwanStockInfo": INFO_ROWS}))
    info = provider.get_company_info("2330")

    assert info.name == "台積電"
    assert info.market == "TWSE"  # FinMind's lowercase "twse" normalized
    assert info.is_demo_data is False


def test_get_company_info_unknown_ticker_raises():
    provider = make_provider(dataset_router({"TaiwanStockInfo": []}))
    with pytest.raises(AssetNotFoundError):
        provider.get_company_info("9999999")


# ---- get_dividends --------------------------------------------------------------


def test_get_dividends_maps_ex_dividend_and_amounts():
    provider = make_provider(dataset_router({"TaiwanStockDividend": DIVIDEND_ROWS}))
    dividends = provider.get_dividends("2330")

    assert len(dividends) == 1  # the undated announcement row is skipped
    d = dividends[0]
    assert d.ex_dividend_date == date(2024, 3, 18)
    assert d.payment_date == date(2024, 4, 11)
    assert d.cash_dividend == Decimal("3.49978969")
    assert d.stock_dividend is None  # zero -> None, not a fake 0
    assert d.source == "FINMIND"


# ---- get_valuation --------------------------------------------------------------


def test_get_valuation_maps_per_pbr_dividend_yield():
    provider = make_provider(dataset_router({"TaiwanStockPER": PER_ROWS, "TaiwanStockMarketValue": []}))
    valuation = provider.get_valuation("2330")

    assert valuation.pe_ratio == Decimal("28.05")
    assert valuation.pb_ratio == Decimal("9.76")
    assert valuation.dividend_yield == Decimal("0.91")
    assert valuation.source == "FINMIND"


def test_get_valuation_handles_free_tier_market_cap_denial_gracefully():
    """TaiwanStockMarketValue requires a paid FinMind tier -- a documented,
    expected limitation (Phase 5 Discovery Report Sec.4/15), not a crash."""
    denial = {"msg": "Your level is free. Please update your user level.", "status": 400, "token_tail": ""}
    provider = make_provider(dataset_router({"TaiwanStockPER": PER_ROWS, "TaiwanStockMarketValue": denial}))

    valuation = provider.get_valuation("2330")

    assert valuation.pe_ratio == Decimal("28.05")  # PER data still comes through
    assert valuation.market_cap is None  # gracefully absent, not an exception
    assert valuation.shares_outstanding is None


def test_get_valuation_unknown_ticker_raises():
    provider = make_provider(dataset_router({"TaiwanStockPER": []}))
    with pytest.raises(AssetNotFoundError):
        provider.get_valuation("9999999")


# ---- get_fundamentals: three-dataset pivot/merge -------------------------------


def test_get_fundamentals_merges_income_balance_cashflow_by_period():
    provider = make_provider(
        dataset_router(
            {
                "TaiwanStockFinancialStatements": FINANCIAL_STATEMENT_ROWS,
                "TaiwanStockBalanceSheet": BALANCE_SHEET_ROWS,
                "TaiwanStockCashFlowsStatement": CASH_FLOW_ROWS,
            }
        )
    )
    results = provider.get_fundamentals("2330")

    assert len(results) == 1
    f = results[0]
    assert f.period == "2026Q1"
    assert f.eps == Decimal("22.08")
    assert f.revenue == Decimal("1134103440000.0")
    # gross_margin = GrossProfit / Revenue
    assert f.gross_margin == Decimal("751295421000.0") / Decimal("1134103440000.0")
    assert f.operating_margin == Decimal("658966142000.0") / Decimal("1134103440000.0")
    assert f.net_margin == Decimal("572801304000.0") / Decimal("1134103440000.0")
    # roe = net income / equity
    assert f.roe == Decimal("572801304000.0") / Decimal("5890960252000.0")
    # roa = net income / total assets
    assert f.roa == Decimal("572801304000.0") / Decimal("8660949685000.0")
    # debt_ratio = liabilities / total assets
    assert f.debt_ratio == Decimal("2728560764000.0") / Decimal("8660949685000.0")
    assert f.operating_cash_flow == Decimal("698976265000.0")
    # free cash flow = operating cash flow + capex (capex already negative)
    assert f.free_cash_flow == Decimal("698976265000.0") + Decimal("-350762799000.0")
    assert f.source == "FINMIND"


def test_get_fundamentals_missing_balance_sheet_still_returns_income_derived_fields():
    """Missing balance-sheet/cash-flow data for a period must not crash the
    whole method -- ratios that need it just come back None."""
    provider = make_provider(
        dataset_router(
            {
                "TaiwanStockFinancialStatements": FINANCIAL_STATEMENT_ROWS,
                "TaiwanStockBalanceSheet": [],
                "TaiwanStockCashFlowsStatement": [],
            }
        )
    )
    results = provider.get_fundamentals("2330")

    assert len(results) == 1
    f = results[0]
    assert f.eps == Decimal("22.08")
    assert f.roe is None
    assert f.roa is None
    assert f.debt_ratio is None
    assert f.operating_cash_flow is None
    assert f.free_cash_flow is None


def test_get_fundamentals_no_data_returns_empty_list_not_error():
    provider = make_provider(
        dataset_router(
            {"TaiwanStockFinancialStatements": [], "TaiwanStockBalanceSheet": [], "TaiwanStockCashFlowsStatement": []}
        )
    )
    assert provider.get_fundamentals("2330") == []


# ---- transport-level errors -----------------------------------------------------


def test_rate_limit_response_raises_rate_limit_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"msg": "Requests reach the upper limit.", "status": 402, "token_tail": ""})

    provider = make_provider(handler)
    with pytest.raises(RateLimitError):
        provider.get_historical_prices("2330")


def test_generic_api_error_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"msg": "something broke", "status": 500, "token_tail": ""})

    provider = make_provider(handler)
    with pytest.raises(ProviderError):
        provider.get_historical_prices("2330")


def test_network_failure_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = make_provider(handler)
    with pytest.raises(ProviderError):
        provider.get_historical_prices("2330")


def test_non_json_response_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    provider = make_provider(handler)
    with pytest.raises(ProviderError):
        provider.get_historical_prices("2330")


# ---- get_institutional_flows: 5 raw categories -> 3-way TWSE split -------------


def test_get_institutional_flows_groups_five_categories_into_three():
    provider = make_provider(dataset_router({"TaiwanStockInstitutionalInvestorsBuySell": INSTITUTIONAL_ROWS}))
    flows = provider.get_institutional_flows("2330")

    assert len(flows) == 1
    f = flows[0]
    assert f.date == date(2026, 8, 27)
    # foreign = Foreign_Investor + Foreign_Dealer_Self
    assert f.foreign_buy == 14070814 + 0
    assert f.foreign_sell == 9570219 + 0
    assert f.foreign_net == (14070814 - 9570219)
    # investment_trust = Investment_Trust alone
    assert f.investment_trust_buy == 41754
    assert f.investment_trust_net == 41754 - 359218
    # dealer = Dealer_self + Dealer_Hedging
    assert f.dealer_buy == 22210 + 266650
    assert f.dealer_net == (22210 + 266650) - (70050 + 61309)
    assert f.total_net == f.foreign_net + f.investment_trust_net + f.dealer_net
    assert f.source == "FINMIND"


def test_get_institutional_flows_partial_categories_leave_bucket_and_total_none():
    """If FinMind is missing one category of a bucket (e.g. Dealer_self is
    missing but Dealer_Hedging is present), that whole bucket must come back
    None rather than silently summing only the part that's there -- and
    total_net must not be computed from an incomplete set either."""
    partial_rows = [r for r in INSTITUTIONAL_ROWS if r["name"] != "Dealer_self"]
    provider = make_provider(dataset_router({"TaiwanStockInstitutionalInvestorsBuySell": partial_rows}))
    flows = provider.get_institutional_flows("2330")

    assert len(flows) == 1
    f = flows[0]
    assert f.foreign_net is not None
    assert f.investment_trust_net is not None
    # dealer bucket is incomplete (Dealer_self missing) -> None, not a
    # partial sum of just Dealer_Hedging.
    assert f.dealer_buy is None
    assert f.dealer_sell is None
    assert f.dealer_net is None
    # total_net requires all three buckets to avoid understating the total.
    assert f.total_net is None


def test_get_institutional_flows_no_data_returns_empty_list():
    provider = make_provider(dataset_router({"TaiwanStockInstitutionalInvestorsBuySell": []}))
    assert provider.get_institutional_flows("2330") == []


# ---- get_margin_trading ----------------------------------------------------------


def test_get_margin_trading_maps_finmind_field_names():
    provider = make_provider(dataset_router({"TaiwanStockMarginPurchaseShortSale": MARGIN_ROWS}))
    rows = provider.get_margin_trading("2330")

    assert len(rows) == 1
    r = rows[0]
    assert r.date == date(2026, 8, 20)
    assert r.margin_buy == 315
    assert r.margin_sell == 418
    assert r.margin_cash_repayment == 11
    assert r.margin_balance == 28308  # MarginPurchaseTodayBalance
    assert r.short_sale_buy == 1
    assert r.short_sale_sell == 2
    assert r.short_sale_balance == 30  # ShortSaleTodayBalance
    assert r.source == "FINMIND"


def test_get_margin_trading_no_data_returns_empty_list():
    provider = make_provider(dataset_router({"TaiwanStockMarginPurchaseShortSale": []}))
    assert provider.get_margin_trading("2330") == []


# ---- get_monthly_revenue: keyed by covered month, not announcement date ---------


def test_get_monthly_revenue_keys_by_covered_month_not_announcement_date():
    provider = make_provider(dataset_router({"TaiwanStockMonthRevenue": MONTH_REVENUE_ROWS}))
    rows = provider.get_monthly_revenue("2330")

    assert len(rows) == 1
    r = rows[0]
    assert r.revenue_year == 2026
    assert r.revenue_month == 7  # July revenue, NOT the August `date`
    assert r.revenue == Decimal("467580548000")
    assert r.announcement_date == date(2026, 8, 1)  # kept for reference only
    assert r.source == "FINMIND"


def test_get_monthly_revenue_incomplete_row_is_skipped():
    incomplete = [{"date": "2026-08-01", "stock_id": "2330", "revenue": None, "revenue_month": 7, "revenue_year": 2026}]
    provider = make_provider(dataset_router({"TaiwanStockMonthRevenue": incomplete}))
    assert provider.get_monthly_revenue("2330") == []


def test_get_monthly_revenue_no_data_returns_empty_list():
    provider = make_provider(dataset_router({"TaiwanStockMonthRevenue": []}))
    assert provider.get_monthly_revenue("2330") == []
