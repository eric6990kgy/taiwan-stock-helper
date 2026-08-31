"""MarketDataIngestionService tests, using a fully in-test FakeProvider
(no HTTP, no FinMind) so behavior can be controlled precisely per ticker:
upsert semantics, partial failure isolation, rate-limit batch handling,
demo->real transition, and dividend/valuation ingestion.
"""

from datetime import date
from decimal import Decimal

from app.models.asset import Asset
from app.models.dividend import Dividend
from app.models.institutional_flow import InstitutionalFlow
from app.models.margin_trading import MarginTrading
from app.models.monthly_revenue import MonthlyRevenue
from app.models.price_history import PriceHistory
from app.providers.market_data_provider import (
    AssetNotFoundError,
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
from app.services.market_data_service import MarketDataIngestionService


class FakeProvider(MarketDataProvider):
    """Every method is driven by a per-ticker dict the test sets up
    beforehand. A dict value that's an Exception instance is raised instead
    of returned -- lets a single test simulate a provider failure on one
    call without touching the others."""

    def __init__(self):
        self.prices: dict[str, object] = {}
        self.valuations: dict[str, object] = {}
        self.fundamentals: dict[str, object] = {}
        self.dividends: dict[str, object] = {}
        self.institutional_flows: dict[str, object] = {}
        self.margin_trading: dict[str, object] = {}
        self.monthly_revenue: dict[str, object] = {}
        self.calls: list[str] = []  # records which tickers were actually touched

    def _resolve(self, store: dict, ticker: str, default):
        self.calls.append(ticker)
        result = store.get(ticker, default)
        if isinstance(result, Exception):
            raise result
        return result

    def get_historical_prices(self, ticker, start=None, end=None):
        return self._resolve(self.prices, ticker, [])

    def get_valuation(self, ticker, on_date=None):
        result = self.valuations.get(ticker)
        if isinstance(result, Exception):
            raise result
        if result is None:
            raise AssetNotFoundError(ticker)
        return result

    def get_fundamentals(self, ticker):
        return self._resolve(self.fundamentals, ticker, [])

    def get_dividends(self, ticker, start=None, end=None):
        return self._resolve(self.dividends, ticker, [])

    def get_institutional_flows(self, ticker, start=None, end=None):
        return self._resolve(self.institutional_flows, ticker, [])

    def get_margin_trading(self, ticker, start=None, end=None):
        return self._resolve(self.margin_trading, ticker, [])

    def get_monthly_revenue(self, ticker):
        return self._resolve(self.monthly_revenue, ticker, [])

    def get_quote(self, ticker) -> QuoteDTO:  # not used by ingestion
        raise NotImplementedError

    def get_company_info(self, ticker):  # not used by ingestion
        raise NotImplementedError


def make_asset(db, ticker="3653", is_demo_data=True) -> Asset:
    asset = Asset(ticker=ticker, name="Test Co", asset_type="STOCK", currency="TWD", is_demo_data=is_demo_data)
    db.add(asset)
    db.flush()
    return asset


def price_point(d: date, close="100", **overrides) -> PricePointDTO:
    fields = dict(date=d, open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close), volume=1000, source="FINMIND")
    fields.update(overrides)
    return PricePointDTO(**fields)


# ---- basic ingestion + demo->real transition ------------------------------------


def test_ingestion_writes_prices_and_flips_demo_flag(db_session):
    asset = make_asset(db_session, is_demo_data=True)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653"])

    assert result.status == "completed"
    assert result.succeeded == ["3653"]
    assert result.failed == []
    assert result.latest_data_date == date(2026, 8, 28)

    db_session.refresh(asset)
    assert asset.is_demo_data is False

    row = db_session.query(PriceHistory).filter_by(asset_id=asset.id, date=date(2026, 8, 28)).one()
    assert row.close == Decimal("650")
    assert row.source == "FINMIND"


def test_ingestion_asset_not_flipped_when_no_valid_rows_written(db_session):
    """A ticker the provider can't find nothing new for stays demo -- an
    empty ingestion result isn't "real data arrived"."""
    asset = make_asset(db_session, is_demo_data=True)
    provider = FakeProvider()
    provider.prices["3653"] = []  # no data returned at all

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    db_session.refresh(asset)
    assert asset.is_demo_data is True


# ---- duplicate / upsert behavior -------------------------------------------------


def test_ingestion_upserts_same_date_instead_of_duplicating(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    # Re-ingest the same date with a different close.
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="655")]
    service.update_all(tickers=["3653"])

    rows = db_session.query(PriceHistory).filter_by(asset_id=asset.id, date=date(2026, 8, 28)).all()
    assert len(rows) == 1
    assert rows[0].close == Decimal("655")


# ---- validation: bad rows skipped, good rows kept --------------------------------


def test_ingestion_skips_invalid_rows_but_keeps_valid_ones(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [
        price_point(date(2026, 8, 27), close="650"),
        price_point(date(2026, 8, 28), close="0"),  # invalid: close must be > 0
    ]
    provider.valuations["3653"] = ValuationDTO(
        date=date(2026, 8, 27), pe_ratio=None, pb_ratio=None, dividend_yield=None,
        market_cap=None, shares_outstanding=None, source="FINMIND",
    )

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653"])

    assert result.succeeded == ["3653"]  # the ticker still counts as a success overall
    assert len(result.validation_warnings) == 1
    assert "2026-08-28" in result.validation_warnings[0].reason

    rows = db_session.query(PriceHistory).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].date == date(2026, 8, 27)


# ---- partial provider failure: one ticker must not abort the batch --------------


def test_one_ticker_failing_does_not_abort_the_batch(db_session):
    good = make_asset(db_session, ticker="3653")
    bad = make_asset(db_session, ticker="3533")
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.prices["3533"] = ProviderError("FinMind is down")

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653", "3533"])

    assert result.status == "completed"
    assert "3653" in result.succeeded
    assert any(f.ticker == "3533" for f in result.failed)
    # the good ticker's data still landed despite the other one failing
    assert db_session.query(PriceHistory).filter_by(asset_id=good.id).count() == 1
    assert db_session.query(PriceHistory).filter_by(asset_id=bad.id).count() == 0


# ---- rate limit: stop the batch, report every remaining ticker explicitly -------


def test_rate_limit_stops_batch_and_reports_remaining_tickers_as_skipped(db_session):
    make_asset(db_session, ticker="3653")
    make_asset(db_session, ticker="3533")
    make_asset(db_session, ticker="3491")
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.prices["3533"] = RateLimitError("quota exceeded")
    provider.prices["3491"] = [price_point(date(2026, 8, 28), close="300")]

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653", "3533", "3491"])

    assert result.status == "rate_limited"
    assert result.succeeded == ["3653"]
    failed_tickers = {f.ticker for f in result.failed}
    assert failed_tickers == {"3533", "3491"}
    skipped_entry = next(f for f in result.failed if f.ticker == "3491")
    assert "skipped" in skipped_entry.reason.lower()
    # 3491 must never have actually been called -- not a silent drop, but a
    # genuine stop, not a "try it anyway and hide the result" either.
    assert "3491" not in provider.calls


# ---- missing fundamentals must not block price ingestion ------------------------


def test_missing_fundamentals_does_not_block_price_ingestion(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.fundamentals["3653"] = ProviderError("fundamentals endpoint down")

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653"])

    assert "3653" in result.succeeded
    assert db_session.query(PriceHistory).filter_by(asset_id=asset.id).count() == 1
    assert any("fundamentals" in w.reason.lower() for w in result.validation_warnings)


# ---- dividends ingestion ----------------------------------------------------------


def test_dividends_are_ingested_and_upserted(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.dividends["3653"] = [
        DividendDTO(ex_dividend_date=date(2026, 3, 18), payment_date=date(2026, 4, 11), cash_dividend=Decimal("3.5"), stock_dividend=None, source="FINMIND")
    ]

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    rows = db_session.query(Dividend).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].cash_dividend == Decimal("3.5")

    # Re-ingest the same ex-dividend date with a corrected amount -> upsert, not a duplicate.
    provider.dividends["3653"] = [
        DividendDTO(ex_dividend_date=date(2026, 3, 18), payment_date=date(2026, 4, 11), cash_dividend=Decimal("3.6"), stock_dividend=None, source="FINMIND")
    ]
    service.update_all(tickers=["3653"])

    rows = db_session.query(Dividend).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].cash_dividend == Decimal("3.6")


# ---- valuation ingestion ----------------------------------------------------------


def test_valuation_is_written_onto_the_latest_price_history_row(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.valuations["3653"] = ValuationDTO(
        date=date(2026, 8, 28), pe_ratio=Decimal("15.5"), pb_ratio=Decimal("2.1"), dividend_yield=Decimal("0.03"),
        market_cap=None, shares_outstanding=None, source="FINMIND",
    )

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    row = db_session.query(PriceHistory).filter_by(asset_id=asset.id, date=date(2026, 8, 28)).one()
    assert row.pe_ratio == Decimal("15.5")
    assert row.pb_ratio == Decimal("2.1")
    assert row.dividend_yield == Decimal("0.03")


def test_valuation_shares_outstanding_updates_asset_when_provider_has_it(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.valuations["3653"] = ValuationDTO(
        date=date(2026, 8, 28), pe_ratio=None, pb_ratio=None, dividend_yield=None,
        market_cap=Decimal("1000000"), shares_outstanding=Decimal("2000"), source="FINMIND",
    )

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    db_session.refresh(asset)
    assert asset.shares_outstanding == Decimal("2000")


# ---- MOCK rows for other dates are preserved, never deleted ---------------------


def test_preserves_existing_mock_rows_the_provider_does_not_cover(db_session):
    asset = make_asset(db_session)
    db_session.add(PriceHistory(asset_id=asset.id, date=date(2020, 1, 1), close=Decimal("500"), source="MOCK"))
    db_session.flush()

    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    old_row = db_session.query(PriceHistory).filter_by(asset_id=asset.id, date=date(2020, 1, 1)).one()
    assert old_row.source == "MOCK"
    assert old_row.close == Decimal("500")


# ---- CASH/FUND assets are out of scope for market-data ingestion ---------------


def test_cash_and_fund_assets_are_never_processed(db_session):
    cash = Asset(ticker="TWD-CASH", name="Cash", asset_type="CASH", currency="TWD")
    fund = Asset(ticker="GLOBAL-ETF-01", name="Fund", asset_type="FUND", currency="TWD", valuation_method="MANUAL_MARKET_VALUE")
    db_session.add_all([cash, fund])
    db_session.flush()

    provider = FakeProvider()
    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all()  # no ticker filter -- would process everything eligible

    assert result.assets_processed == 0
    assert provider.calls == []


# ---- Phase 6: institutional flow ingestion --------------------------------------


def test_institutional_flows_are_ingested_and_upserted(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.institutional_flows["3653"] = [
        InstitutionalFlowDTO(
            date=date(2026, 8, 28), foreign_buy=1000, foreign_sell=400, foreign_net=600,
            investment_trust_buy=200, investment_trust_sell=50, investment_trust_net=150,
            dealer_buy=10, dealer_sell=5, dealer_net=5, total_net=755, source="FINMIND",
        )
    ]

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    rows = db_session.query(InstitutionalFlow).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].foreign_net == 600
    assert rows[0].total_net == 755

    # Re-ingest the same date with corrected figures -> upsert, not a duplicate.
    provider.institutional_flows["3653"] = [
        InstitutionalFlowDTO(
            date=date(2026, 8, 28), foreign_buy=1100, foreign_sell=400, foreign_net=700,
            investment_trust_buy=200, investment_trust_sell=50, investment_trust_net=150,
            dealer_buy=10, dealer_sell=5, dealer_net=5, total_net=855, source="FINMIND",
        )
    ]
    service.update_all(tickers=["3653"])
    rows = db_session.query(InstitutionalFlow).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].foreign_net == 700


def test_institutional_flow_failure_does_not_block_price_ingestion(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.institutional_flows["3653"] = ProviderError("institutional endpoint down")

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653"])

    assert "3653" in result.succeeded
    assert db_session.query(PriceHistory).filter_by(asset_id=asset.id).count() == 1
    assert any("institutional" in w.reason.lower() for w in result.validation_warnings)


def test_institutional_flow_rate_limit_stops_the_batch(db_session):
    make_asset(db_session, ticker="3653")
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.institutional_flows["3653"] = RateLimitError("quota exceeded")

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653"])

    assert result.status == "rate_limited"
    assert result.succeeded == []


# ---- Phase 6: margin trading ingestion -------------------------------------------


def test_margin_trading_is_ingested_and_upserted(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.margin_trading["3653"] = [
        MarginTradingDTO(
            date=date(2026, 8, 28), margin_buy=100, margin_sell=50, margin_cash_repayment=5,
            margin_balance=28308, short_sale_buy=1, short_sale_sell=2,
            short_sale_cash_repayment=0, short_sale_balance=30, source="FINMIND",
        )
    ]

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    rows = db_session.query(MarginTrading).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].margin_balance == 28308
    assert rows[0].short_sale_balance == 30


def test_margin_trading_failure_does_not_block_price_ingestion(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.margin_trading["3653"] = ProviderError("margin endpoint down")

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653"])

    assert "3653" in result.succeeded
    assert db_session.query(PriceHistory).filter_by(asset_id=asset.id).count() == 1
    assert any("margin" in w.reason.lower() for w in result.validation_warnings)


# ---- Phase 6: monthly revenue ingestion ------------------------------------------


def test_monthly_revenue_is_ingested_and_upserted(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.monthly_revenue["3653"] = [
        MonthlyRevenueDTO(
            revenue_year=2026, revenue_month=7, revenue=Decimal("467580548000"),
            announcement_date=date(2026, 8, 1), source="FINMIND",
        )
    ]

    service = MarketDataIngestionService(db_session, provider)
    service.update_all(tickers=["3653"])

    rows = db_session.query(MonthlyRevenue).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].revenue_year == 2026
    assert rows[0].revenue_month == 7
    assert rows[0].revenue == Decimal("467580548000")

    # Re-ingest the same period with a revised figure -> upsert, not a duplicate.
    provider.monthly_revenue["3653"] = [
        MonthlyRevenueDTO(
            revenue_year=2026, revenue_month=7, revenue=Decimal("467999999999"),
            announcement_date=date(2026, 8, 1), source="FINMIND",
        )
    ]
    service.update_all(tickers=["3653"])
    rows = db_session.query(MonthlyRevenue).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].revenue == Decimal("467999999999")


def test_monthly_revenue_failure_does_not_block_price_ingestion(db_session):
    asset = make_asset(db_session)
    provider = FakeProvider()
    provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]
    provider.monthly_revenue["3653"] = ProviderError("revenue endpoint down")

    service = MarketDataIngestionService(db_session, provider)
    result = service.update_all(tickers=["3653"])

    assert "3653" in result.succeeded
    assert db_session.query(PriceHistory).filter_by(asset_id=asset.id).count() == 1
    assert any("revenue" in w.reason.lower() for w in result.validation_warnings)
