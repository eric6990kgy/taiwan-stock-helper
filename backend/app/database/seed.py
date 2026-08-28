"""Populates the demo dataset described in PRD Sec.37: one user, three
accounts, the seven TW tickers plus the Global ETF fund and a cash asset,
a short price/fundamentals history for each stock, one watchlist entry,
one thesis, and a handful of transactions that exercise every transaction
type and both valuation methods. Every price/fundamentals row is stamped
source='MOCK' and every asset stamped is_demo_data=True — this is fixture
data, never to be mistaken for real market data (PRD Sec.37).

Safe to re-run: wipes and recreates all rows (dev/demo tool only).
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models import (
    Account,
    Asset,
    Fundamentals,
    InvestmentThesis,
    PriceHistory,
    Transaction,
    User,
    Watchlist,
)

TW_STOCKS = [
    # ticker, name, sector, industry, seed close price
    ("3653", "健策", "Technology", "Semiconductor Packaging", Decimal("650")),
    ("3533", "嘉澤", "Technology", "Connectors", Decimal("1200")),
    ("3491", "昇達科", "Technology", "RF Components", Decimal("320")),
    ("3515", "華擎", "Technology", "Motherboards", Decimal("980")),
    ("3563", "牧德", "Technology", "AOI Equipment", Decimal("560")),
    ("3551", "世禾", "Technology", "Precision Components", Decimal("210")),
    ("3483", "力致", "Technology", "Precision Machining", Decimal("150")),
]


def _price_series(base_close: Decimal, days: int = 10) -> list[tuple[date, Decimal]]:
    """A short deterministic mock walk ending at `base_close`, for chart rendering."""
    today = date(2026, 8, 28)
    series = []
    for i in range(days, -1, -1):
        drift = Decimal(i) * Decimal("0.4")
        close = (base_close - drift).quantize(Decimal("0.0001"))
        series.append((today - timedelta(days=i), close))
    return series


def seed(db: Session) -> None:
    # Wipe existing demo data (dependency order matters for FKs).
    for model in (Transaction, Watchlist, InvestmentThesis, PriceHistory, Fundamentals, Account, Asset, User):
        db.query(model).delete()
    db.flush()

    user = User(name="Eric")
    db.add(user)
    db.flush()

    fubon = Account(user_id=user.id, name="Fubon Securities", account_type="BROKERAGE", currency="TWD")
    global_invest = Account(user_id=user.id, name="Global ETF Account", account_type="GLOBAL_INVEST", currency="TWD")
    cash = Account(user_id=user.id, name="Cash", account_type="CASH", currency="TWD")
    db.add_all([fubon, global_invest, cash])
    db.flush()

    assets_by_ticker: dict[str, Asset] = {}
    for ticker, name, sector, industry, base_close in TW_STOCKS:
        asset = Asset(
            ticker=ticker,
            name=name,
            asset_type="STOCK",
            market="TWSE",
            currency="TWD",
            sector=sector,
            industry=industry,
            valuation_method="TRANSACTION_BASED",
            is_demo_data=True,
        )
        db.add(asset)
        assets_by_ticker[ticker] = asset

    global_etf = Asset(
        ticker="GLOBAL-ETF-01",
        name="Global ETF Portfolio",
        asset_type="FUND",
        market="GLOBAL",
        currency="TWD",
        sector=None,
        industry=None,
        valuation_method="MANUAL_MARKET_VALUE",
        is_demo_data=True,
    )
    db.add(global_etf)

    cash_asset = Asset(
        ticker="TWD-CASH",
        name="TWD Cash",
        asset_type="CASH",
        market=None,
        currency="TWD",
        sector=None,
        industry=None,
        valuation_method="TRANSACTION_BASED",
        is_demo_data=True,
    )
    db.add(cash_asset)
    db.flush()

    # TWD cash is trivially worth 1:1 -- without this row it would price at
    # zero (no quote available) and show as a 100% unrealized loss.
    db.add(PriceHistory(asset_id=cash_asset.id, date=date(2026, 1, 1), close=Decimal("1"), source="MANUAL"))

    # Price history + fundamentals for the TW stocks only (mock).
    for ticker, name, sector, industry, base_close in TW_STOCKS:
        asset = assets_by_ticker[ticker]
        for d, close in _price_series(base_close):
            db.add(
                PriceHistory(
                    asset_id=asset.id,
                    date=d,
                    open=close,
                    high=close * Decimal("1.01"),
                    low=close * Decimal("0.99"),
                    close=close,
                    volume=1_000_000,
                    source="MOCK",
                )
            )
        db.add(
            Fundamentals(
                asset_id=asset.id,
                period="TTM",
                revenue=base_close * Decimal("1_000_000"),
                eps=base_close / Decimal("40"),
                gross_margin=Decimal("0.35"),
                operating_margin=Decimal("0.20"),
                net_margin=Decimal("0.15"),
                roe=Decimal("0.18"),
                roa=Decimal("0.10"),
                debt_ratio=Decimal("0.30"),
                operating_cash_flow=base_close * Decimal("900_000"),
                free_cash_flow=base_close * Decimal("600_000"),
                source="MOCK",
            )
        )

    # Global ETF: manual valuation series (total position value, not per-unit price).
    for i, value in enumerate([Decimal("115000"), Decimal("118500"), Decimal("120000")]):
        db.add(
            PriceHistory(
                asset_id=global_etf.id,
                date=date(2026, 6, 1) + timedelta(days=30 * i),
                close=value,
                source="MANUAL",
            )
        )

    db.flush()

    # Sample transactions — exercise every type and both valuation conventions.
    db.add_all(
        [
            # Global ETF: NT$120,000 lump-sum contribution, quantity=amount, price=1 (A4 convention).
            Transaction(
                account_id=global_invest.id,
                asset_id=global_etf.id,
                date=date(2026, 6, 1),
                type="CASH_DEPOSIT",
                quantity=Decimal("120000"),
                price=Decimal("1"),
                fee=Decimal("0"),
                tax=Decimal("0"),
                currency="TWD",
                note="Initial global ETF / robo-invest contribution",
            ),
            # 3653: two buys and a partial sell.
            Transaction(
                account_id=fubon.id,
                asset_id=assets_by_ticker["3653"].id,
                date=date(2026, 3, 10),
                type="BUY",
                quantity=Decimal("10"),
                price=Decimal("600"),
                fee=Decimal("85"),
                tax=Decimal("0"),
                currency="TWD",
            ),
            Transaction(
                account_id=fubon.id,
                asset_id=assets_by_ticker["3653"].id,
                date=date(2026, 5, 20),
                type="BUY",
                quantity=Decimal("10"),
                price=Decimal("640"),
                fee=Decimal("91"),
                tax=Decimal("0"),
                currency="TWD",
            ),
            Transaction(
                account_id=fubon.id,
                asset_id=assets_by_ticker["3653"].id,
                date=date(2026, 8, 1),
                type="SELL",
                quantity=Decimal("5"),
                price=Decimal("650"),
                fee=Decimal("46"),
                tax=Decimal("9"),
                currency="TWD",
            ),
            # 3533: single buy, held.
            Transaction(
                account_id=fubon.id,
                asset_id=assets_by_ticker["3533"].id,
                date=date(2026, 4, 15),
                type="BUY",
                quantity=Decimal("5"),
                price=Decimal("1150"),
                fee=Decimal("82"),
                tax=Decimal("0"),
                currency="TWD",
            ),
            # Dividend on 3653.
            Transaction(
                account_id=fubon.id,
                asset_id=assets_by_ticker["3653"].id,
                date=date(2026, 7, 15),
                type="DIVIDEND",
                quantity=Decimal("15"),
                price=Decimal("8"),
                fee=Decimal("0"),
                tax=Decimal("0"),
                currency="TWD",
                note="Cash dividend, NT$8/share",
            ),
            # Cash account funding.
            Transaction(
                account_id=cash.id,
                asset_id=cash_asset.id,
                date=date(2026, 1, 1),
                type="CASH_DEPOSIT",
                quantity=Decimal("50000"),
                price=Decimal("1"),
                fee=Decimal("0"),
                tax=Decimal("0"),
                currency="TWD",
            ),
        ]
    )

    # Watchlist: one entry.
    db.add(
        Watchlist(
            asset_id=assets_by_ticker["3491"].id,
            status="RESEARCHING",
            reason="RF component demand tied to next-gen smartphone cycle",
            target_metrics={"revenue_growth_gt": 15, "roe_gt": 12},
            entry_consideration="Wait for pullback below NT$300",
            review_date=date(2026, 10, 1),
        )
    )

    # Investment thesis: one entry, for the held position.
    db.add(
        InvestmentThesis(
            asset_id=assets_by_ticker["3653"].id,
            thesis="AI server thermal/packaging demand should sustain margin expansion over the next 2-3 years.",
            catalysts="AI server ramp; advanced packaging capacity expansion",
            risks="Customer concentration; cyclicality in semiconductor capex",
            key_metrics=[
                {"label": "Revenue Growth", "operator": ">", "value": 15},
                {"label": "Operating Margin", "operator": ">", "value": 20},
                {"label": "ROE", "operator": ">", "value": 15},
            ],
            status="INTACT",
            last_reviewed=date(2026, 8, 1),
        )
    )

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
