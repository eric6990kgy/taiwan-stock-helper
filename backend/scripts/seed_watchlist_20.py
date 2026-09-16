"""One-off, idempotent import of the 20-ticker candidate watchlist (Phase 8,
個股訊號引擎規格書) -- pulled directly from 看盤台's own artifact database on
2026-09-16, since 看盤台 itself is being retired as a data source (its
per-ticker analysis re-queries Claude live, which is exactly the token cost
this repo's deterministic FinMind-API-based approach exists to avoid).

Not part of app/database/seed.py -- that's fixture/demo data reset on every
test run; this is real candidate-pool data, run once against the actual
dev DB:

    cd backend
    .venv/Scripts/python -m scripts.seed_watchlist_20

Safe to re-run: skips any ticker that already has an Asset row, and skips
adding a watchlist entry for an asset that's already on it.
"""

from app.database.session import SessionLocal
from app.models.asset import Asset
from app.models.watchlist import Watchlist
from app.repositories.asset_repository import AssetRepository
from app.repositories.watchlist_repository import WatchlistRepository

# (ticker, name) -- exactly the 20 rows read from 看盤台's `watchlist`
# collection via the Artifact tool's read_db action.
CANDIDATES = [
    ("1101", "台泥"),
    ("1216", "統一"),
    ("1301", "台塑"),
    ("1513", "中興電"),
    ("1519", "華城"),
    ("1536", "和大"),
    ("2049", "上銀"),
    ("2308", "台達電"),
    ("2330", "台積電"),
    ("2379", "瑞昱"),
    ("2454", "聯發科"),
    ("2603", "長榮"),
    ("2912", "統一超"),
    ("3324", "雙鴻"),
    ("3653", "健策"),
    ("4104", "佳醫"),
    ("6446", "藥華藥"),
    ("6472", "保瑞"),
    ("6505", "台塑化"),
    ("7799", "禾榮科"),
]


def run() -> None:
    db = SessionLocal()
    try:
        assets = AssetRepository(db)
        watchlist = WatchlistRepository(db)

        created_assets = 0
        created_watchlist = 0
        for ticker, name in CANDIDATES:
            asset = assets.get_by_ticker(ticker)
            if asset is None:
                asset = Asset(
                    ticker=ticker,
                    name=name,
                    asset_type="STOCK",
                    market="TWSE",
                    currency="TWD",
                    is_demo_data=False,
                )
                db.add(asset)
                db.flush()
                created_assets += 1

            if watchlist.get_by_asset(asset.id) is None:
                db.add(Watchlist(asset_id=asset.id, status="WATCHING"))
                created_watchlist += 1

        db.commit()
        print(f"Assets created: {created_assets} (of {len(CANDIDATES)} candidates)")
        print(f"Watchlist entries created: {created_watchlist}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
