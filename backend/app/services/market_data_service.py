"""Orchestrates the manual "Update Market Data" flow (Phase 5B, the manual
half of the hybrid ingestion architecture -- no scheduler/cron in this
phase, per explicit instruction):

  Settings -> API -> MarketDataIngestionService -> FinMindProvider
      -> validation -> repositories -> SQLite

One ticker failing must never abort the batch (mirrors
ImportExportService's CSV-row pattern); a RateLimitError stops fetching
further *new* data but still reports every remaining ticker explicitly as
skipped, rather than silently dropping them from the result.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider, ProviderError, RateLimitError
from app.providers.mock_provider import MockMarketDataProvider
from app.repositories.asset_repository import AssetRepository
from app.repositories.dividend_repository import DividendRepository
from app.repositories.fundamentals_repository import FundamentalsRepository
from app.repositories.institutional_flow_repository import InstitutionalFlowRepository
from app.repositories.margin_trading_repository import MarginTradingRepository
from app.repositories.monthly_revenue_repository import MonthlyRevenueRepository
from app.repositories.price_repository import PriceRepository
from app.schemas.market_data import MarketDataError, MarketDataUpdateResult
from app.services.agent_research_service import AgentResearchService
from app.services.gemini_client import GeminiClient
from app.services.line_notifier import LineNotifier, LineNotifyError, format_recommendation_alert
from app.services.market_data_validation import PriceValidationError, validate_price_point
from app.services.recommendation_outcome_service import RecommendationOutcomeService
from app.services.recommendation_service import RecommendationService
from app.services.research_service import ResearchService
from app.services.scoring_service import TAIEX_TICKER, ScoringService
from app.services.thesis_service import ThesisService

SOURCE = "FINMIND"
INCREMENTAL_LOOKBACK_DAYS = 5  # small overlap window on repeat updates, to catch late corrections
INITIAL_BACKFILL_DAYS = 365 * 2  # first-ever real ingestion for a ticker pulls 2 years of history
REGIME_BACKFILL_DAYS = 365 * 3  # TAIEX needs 200+ trading days of history for regime detection (SMA200)

# Market data only applies to things that actually trade on an exchange.
# CASH is a bookkeeping placeholder and FUND (the Global ETF, valued
# MANUAL_MARKET_VALUE) is deliberately user-entered -- see Asset's docstring
# and architecture decision A4. Neither has a ticker FinMind would recognize.
# INDEX (TAIEX) is provisioned and ingested separately (_ensure_taiex_asset),
# not through this per-asset loop -- it has no fundamentals/dividends/
# institutional-flow/margin/revenue to fetch, only price history.
ELIGIBLE_ASSET_TYPES = ("STOCK", "ETF")


class MarketDataIngestionService:
    def __init__(self, db: Session, provider: MarketDataProvider, gemini_client: GeminiClient | None = None):
        self.db = db
        self.provider = provider
        self.assets = AssetRepository(db)
        self.prices = PriceRepository(db)
        self.fundamentals_repo = FundamentalsRepository(db)
        self.dividends_repo = DividendRepository(db)
        self.institutional_flows_repo = InstitutionalFlowRepository(db)
        self.margin_trading_repo = MarginTradingRepository(db)
        self.monthly_revenue_repo = MonthlyRevenueRepository(db)
        self.scoring_service = ScoringService(db)
        self.recommendation_service = RecommendationService(db)
        self.recommendation_outcome_service = RecommendationOutcomeService(db)
        self.line_notifier = LineNotifier()
        # Phase 12: Gemini multi-agent research team. `gemini_client` is a
        # constructor param (not always built here directly) for the same
        # reason `provider` is -- API tests need a real seam to force it
        # off via dependency override (get_gemini_client in deps.py),
        # otherwise a real GEMINI_API_KEY in the local .env would make
        # pytest itself fire real, billed Gemini calls (discovered live
        # 2026-09-17 -- exactly the "no live external calls in tests"
        # rule this repo already enforces for FinMind via stub providers).
        # Reads via the local MockMarketDataProvider (same as
        # SignalService/ResearchService elsewhere) -- never calls FinMind,
        # so this never raises RateLimitError. Inert (analyze() returns
        # immediately) until GEMINI_API_KEY is configured, same "optional"
        # convention as self.line_notifier above.
        self.agent_research_service = AgentResearchService(
            db,
            gemini_client if gemini_client is not None else GeminiClient(),
            ResearchService(db, MockMarketDataProvider(db), ThesisService(db)),
        )

    def close(self) -> None:
        self.line_notifier.close()

    def _ensure_taiex_asset(self) -> Asset:
        """Get-or-create the TAIEX INDEX asset (Phase 7) -- tracked purely
        for regime detection, never a portfolio holding, never appears in
        holdings/transactions. Idempotent: a second call finds the existing
        row instead of creating a duplicate."""
        asset = self.assets.get_by_ticker(TAIEX_TICKER)
        if asset is not None:
            return asset
        asset = Asset(
            ticker=TAIEX_TICKER,
            name="TAIEX",
            asset_type="INDEX",
            market="TWSE",
            currency="TWD",
            is_demo_data=False,
        )
        self.db.add(asset)
        self.db.flush()
        return asset

    def _update_taiex_history(self, taiex: Asset) -> None:
        """Same validate+upsert loop as a stock's price history -- TAIEX has
        no fundamentals/dividends/etc. to fetch, only price history."""
        existing_latest = self.prices.latest(taiex.id)
        start = (
            existing_latest.date - timedelta(days=INCREMENTAL_LOOKBACK_DAYS)
            if existing_latest is not None
            else date.today() - timedelta(days=REGIME_BACKFILL_DAYS)
        )
        for point in self.provider.get_historical_prices(taiex.ticker, start=start, end=date.today()):
            try:
                validate_price_point(point)
            except PriceValidationError:
                continue
            self.prices.upsert(
                taiex.id,
                point.date,
                open=point.open,
                high=point.high,
                low=point.low,
                close=point.close,
                volume=point.volume,
                adjusted_close=point.adjusted_close,
                trading_value=point.trading_value,
                source=SOURCE,
            )

    def update_all(self, tickers: list[str] | None = None) -> MarketDataUpdateResult:
        """Closes self.line_notifier's httpx.Client when done, win or lose --
        this service is constructed fresh per-request (see get_market_data_service),
        so nothing else would ever close it."""
        try:
            return self._update_all(tickers)
        finally:
            self.close()

    def _update_all(self, tickers: list[str] | None = None) -> MarketDataUpdateResult:
        if tickers:
            assets = [self.assets.get_by_ticker(t) for t in tickers]
            assets = [a for a in assets if a is not None]
        else:
            assets = self.assets.list()
        assets = [a for a in assets if a.asset_type in ELIGIBLE_ASSET_TYPES]

        succeeded: list[str] = []
        failed: list[MarketDataError] = []
        validation_warnings: list[MarketDataError] = []
        latest_date: date | None = None
        status = "completed"

        # TAIEX (regime detection input for Phase 7 scoring) updates before
        # the main per-asset loop, so scores computed below see fresh data.
        # A rate limit here must stop the whole batch exactly like a rate
        # limit on any individual asset would -- report every real asset as
        # skipped rather than silently proceeding without regime data.
        taiex = self._ensure_taiex_asset()
        try:
            self._update_taiex_history(taiex)
        except RateLimitError as exc:
            failed.append(MarketDataError(ticker=taiex.ticker, reason=f"Rate limited: {exc}"))
            for asset in assets:
                failed.append(MarketDataError(ticker=asset.ticker, reason="Skipped: update stopped after rate limit."))
            self.db.commit()
            return MarketDataUpdateResult(
                status="rate_limited",
                assets_processed=len(assets),
                succeeded=succeeded,
                failed=failed,
                validation_warnings=validation_warnings,
                latest_data_date=latest_date,
                source=SOURCE,
            )
        except ProviderError:
            # TAIEX itself failing (but not rate-limited) is not fatal --
            # regime detection just falls back to None (composite_score's
            # equal-weighted default) until the next successful update.
            pass

        for index, asset in enumerate(assets):
            try:
                asset_latest_date, warnings = self._update_one(asset)
                succeeded.append(asset.ticker)
                validation_warnings.extend(warnings)
                if asset_latest_date is not None and (latest_date is None or asset_latest_date > latest_date):
                    latest_date = asset_latest_date

            except RateLimitError as exc:
                # Stop fetching more -- retrying immediately just fails again
                # -- but report every remaining ticker explicitly, never a
                # silent drop.
                status = "rate_limited"
                failed.append(MarketDataError(ticker=asset.ticker, reason=f"Rate limited: {exc}"))
                for remaining in assets[index + 1 :]:
                    failed.append(
                        MarketDataError(ticker=remaining.ticker, reason="Skipped: update stopped after rate limit.")
                    )
                break

            except (AssetNotFoundError, ProviderError) as exc:
                failed.append(MarketDataError(ticker=asset.ticker, reason=str(exc)))
                continue

        # Phase 8: one daily scan across the whole watchlist (not per-asset
        # -- run_daily_scan() already loops it), risk-gated against Phase
        # A's risk/drawdown before any recommendation is created. LINE
        # alerts now fire per Recommendation row (only on an actual status
        # change), replacing Phase 7's "fires every run" behavior. Reads
        # only the local DB just written above, so nothing here raises
        # RateLimitError -- best-effort like scoring above.
        try:
            outcomes = self.recommendation_service.run_daily_scan()
        except AssetNotFoundError as exc:
            outcomes = []
            validation_warnings.append(MarketDataError(ticker="(scan)", reason=f"Daily scan unavailable: {exc}"))

        for outcome in outcomes:
            message = format_recommendation_alert(
                outcome.ticker,
                outcome.asset_name,
                outcome.recommendation,
                outcome.composite_score,
                outcome.regime,
            )
            try:
                self.line_notifier.broadcast(message)
            except LineNotifyError as exc:
                validation_warnings.append(MarketDataError(ticker=outcome.ticker, reason=f"LINE alert not sent: {exc}"))

        # Phase 12: Gemini multi-agent research team, only for the same
        # change-only outcomes above -- no-op (empty lists back) when
        # GEMINI_API_KEY isn't configured. Each role's own failure is
        # already isolated inside analyze(); any error message it returns
        # is recorded as a best-effort warning, never raised, matching the
        # LINE-alert failure handling immediately above.
        for outcome in outcomes:
            _, agent_errors = self.agent_research_service.analyze(outcome)
            for message in agent_errors:
                validation_warnings.append(MarketDataError(ticker=outcome.ticker, reason=f"Agent analysis: {message}"))

        # Phase 10: score every past Recommendation that's now old enough
        # to check against real price history. Reads only the local DB
        # (price_history/recommendations already written above), same as
        # the scan itself -- nothing here calls FinMind, so there's no
        # RateLimitError/ProviderError class of failure to guard against.
        self.recommendation_outcome_service.score_due_outcomes()

        self.db.commit()

        return MarketDataUpdateResult(
            status=status,
            assets_processed=len(assets),
            succeeded=succeeded,
            failed=failed,
            validation_warnings=validation_warnings,
            latest_data_date=latest_date,
            source=SOURCE,
        )

    def _update_one(self, asset: Asset) -> tuple[date | None, list[MarketDataError]]:
        existing_latest = self.prices.latest(asset.id)
        if existing_latest is not None:
            start = existing_latest.date - timedelta(days=INCREMENTAL_LOOKBACK_DAYS)
        else:
            start = date.today() - timedelta(days=INITIAL_BACKFILL_DAYS)

        price_points = self.provider.get_historical_prices(asset.ticker, start=start, end=date.today())

        warnings: list[MarketDataError] = []
        latest_written: date | None = None
        wrote_any_real_row = False

        for point in price_points:
            try:
                validate_price_point(point)
            except PriceValidationError as exc:
                warnings.append(MarketDataError(ticker=asset.ticker, reason=str(exc)))
                continue

            self.prices.upsert(
                asset.id,
                point.date,
                open=point.open,
                high=point.high,
                low=point.low,
                close=point.close,
                volume=point.volume,
                adjusted_close=point.adjusted_close,
                trading_value=point.trading_value,
                source=SOURCE,
            )
            wrote_any_real_row = True
            if latest_written is None or point.date > latest_written:
                latest_written = point.date

        if not wrote_any_real_row:
            # Every returned row failed validation, or the provider returned
            # nothing new -- not a hard failure (the ticker exists and was
            # reachable), but nothing to promote from demo to real either.
            return latest_written, warnings

        # Valuation ratios (PER/PBR/dividend yield, +market cap where the
        # provider's tier allows it) land on an *existing* price_history row
        # -- valuation.date can lag latest_written (the provider's PER data
        # can trail its price data by a few days), and upserting onto a date
        # with no row yet would create one missing the required `close`
        # column. Not having that day's ratios yet is a warning, not a crash.
        try:
            valuation = self.provider.get_valuation(asset.ticker, on_date=latest_written)
            if self.prices.get_by_asset_and_date(asset.id, valuation.date) is not None:
                self.prices.upsert(
                    asset.id,
                    valuation.date,
                    pe_ratio=valuation.pe_ratio,
                    pb_ratio=valuation.pb_ratio,
                    dividend_yield=valuation.dividend_yield,
                )
            else:
                warnings.append(
                    MarketDataError(
                        ticker=asset.ticker,
                        reason=f"Valuation unavailable: no price_history row for {valuation.date} to attach it to.",
                    )
                )
            if valuation.shares_outstanding is not None:
                self.assets.update(asset, shares_outstanding=valuation.shares_outstanding)
        except RateLimitError:
            raise  # must stop the whole batch, never get absorbed as a per-ticker warning
        except (AssetNotFoundError, ProviderError) as exc:
            warnings.append(MarketDataError(ticker=asset.ticker, reason=f"Valuation unavailable: {exc}"))

        # Fundamentals and dividends are best-effort -- a failure here must
        # never block the price data that already landed successfully.
        try:
            for fundamentals in self.provider.get_fundamentals(asset.ticker):
                self.fundamentals_repo.upsert(
                    asset.id,
                    fundamentals.period,
                    revenue=fundamentals.revenue,
                    eps=fundamentals.eps,
                    gross_margin=fundamentals.gross_margin,
                    operating_margin=fundamentals.operating_margin,
                    net_margin=fundamentals.net_margin,
                    roe=fundamentals.roe,
                    roa=fundamentals.roa,
                    debt_ratio=fundamentals.debt_ratio,
                    operating_cash_flow=fundamentals.operating_cash_flow,
                    free_cash_flow=fundamentals.free_cash_flow,
                    source=SOURCE,
                )
        except RateLimitError:
            raise
        except ProviderError as exc:
            warnings.append(MarketDataError(ticker=asset.ticker, reason=f"Fundamentals unavailable: {exc}"))

        try:
            for dividend in self.provider.get_dividends(asset.ticker):
                self.dividends_repo.upsert(
                    asset.id,
                    dividend.ex_dividend_date,
                    payment_date=dividend.payment_date,
                    cash_dividend=dividend.cash_dividend,
                    stock_dividend=dividend.stock_dividend,
                    source=SOURCE,
                )
        except RateLimitError:
            raise
        except ProviderError as exc:
            warnings.append(MarketDataError(ticker=asset.ticker, reason=f"Dividends unavailable: {exc}"))

        # Phase 6: institutional flow / margin trading / monthly revenue are
        # all best-effort, same as fundamentals/dividends above -- one
        # dataset failing must never block price data that already landed.
        try:
            for flow in self.provider.get_institutional_flows(asset.ticker, start=start, end=date.today()):
                self.institutional_flows_repo.upsert(
                    asset.id,
                    flow.date,
                    foreign_buy=flow.foreign_buy,
                    foreign_sell=flow.foreign_sell,
                    foreign_net=flow.foreign_net,
                    investment_trust_buy=flow.investment_trust_buy,
                    investment_trust_sell=flow.investment_trust_sell,
                    investment_trust_net=flow.investment_trust_net,
                    dealer_buy=flow.dealer_buy,
                    dealer_sell=flow.dealer_sell,
                    dealer_net=flow.dealer_net,
                    total_net=flow.total_net,
                    source=SOURCE,
                )
        except RateLimitError:
            raise
        except ProviderError as exc:
            warnings.append(MarketDataError(ticker=asset.ticker, reason=f"Institutional flow unavailable: {exc}"))

        try:
            for margin in self.provider.get_margin_trading(asset.ticker, start=start, end=date.today()):
                self.margin_trading_repo.upsert(
                    asset.id,
                    margin.date,
                    margin_buy=margin.margin_buy,
                    margin_sell=margin.margin_sell,
                    margin_cash_repayment=margin.margin_cash_repayment,
                    margin_balance=margin.margin_balance,
                    short_sale_buy=margin.short_sale_buy,
                    short_sale_sell=margin.short_sale_sell,
                    short_sale_cash_repayment=margin.short_sale_cash_repayment,
                    short_sale_balance=margin.short_sale_balance,
                    source=SOURCE,
                )
        except RateLimitError:
            raise
        except ProviderError as exc:
            warnings.append(MarketDataError(ticker=asset.ticker, reason=f"Margin trading unavailable: {exc}"))

        try:
            for revenue in self.provider.get_monthly_revenue(asset.ticker):
                self.monthly_revenue_repo.upsert(
                    asset.id,
                    revenue.revenue_year,
                    revenue.revenue_month,
                    revenue=revenue.revenue,
                    announcement_date=revenue.announcement_date,
                    source=SOURCE,
                )
        except RateLimitError:
            raise
        except ProviderError as exc:
            warnings.append(MarketDataError(ticker=asset.ticker, reason=f"Monthly revenue unavailable: {exc}"))

        # Phase 7: composite score, best-effort like everything above --
        # reads only from the local DB just written above (never calls
        # FinMind), so nothing here raises RateLimitError. An
        # AssetNotFoundError would mean the price row just upserted for
        # latest_written isn't visible for some reason -- shouldn't happen,
        # but handled the same defensive way as every other block.
        try:
            self.scoring_service.compute_and_store(asset.ticker, latest_written)
        except AssetNotFoundError as exc:
            warnings.append(MarketDataError(ticker=asset.ticker, reason=f"Score unavailable: {exc}"))

        # Demo -> real transition (Phase 5B decision 4): flips automatically
        # on the first successfully validated real record, preserving the
        # MOCK rows already written for other dates (they're distinguished
        # by `source`, never deleted).
        if asset.is_demo_data:
            self.assets.update(asset, is_demo_data=False)

        return latest_written, warnings
