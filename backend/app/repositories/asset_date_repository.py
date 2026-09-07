"""Shared base for repositories keyed by (asset_id, a single date column) --
Dividend/InstitutionalFlow/MarginTrading/PriceHistory all have this exact
range/get_by_asset_and_date/upsert shape, differing only by model class and
(for Dividend) the date column's name. Factored here after the pattern was
independently copy-pasted 4 times in one commit -- a bug fixed in the upsert
semantics now needs fixing once, not once per dataset.
"""

from datetime import date
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class AssetDateRepository(Generic[ModelT]):
    """Subclasses set `model` (the mapped class) and, if its date column
    isn't literally named `date`, `date_column`."""

    model: type[ModelT]
    date_column: str = "date"

    def __init__(self, db: Session):
        self.db = db

    def _date_attr(self):
        return getattr(self.model, self.date_column)

    def range(self, asset_id: int, start: date | None = None, end: date | None = None) -> list[ModelT]:
        date_attr = self._date_attr()
        stmt = select(self.model).where(self.model.asset_id == asset_id)
        if start is not None:
            stmt = stmt.where(date_attr >= start)
        if end is not None:
            stmt = stmt.where(date_attr <= end)
        stmt = stmt.order_by(date_attr)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_asset_and_date(self, asset_id: int, on_date: date) -> ModelT | None:
        date_attr = self._date_attr()
        stmt = select(self.model).where(self.model.asset_id == asset_id, date_attr == on_date)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, asset_id: int, on_date: date, **fields) -> ModelT:
        """One row per (asset, date) -- re-ingesting the same date updates
        the existing row in place instead of hitting the model's unique
        constraint."""
        existing = self.get_by_asset_and_date(asset_id, on_date)
        if existing is None:
            row = self.model(asset_id=asset_id, **{self.date_column: on_date}, **fields)
            self.db.add(row)
            self.db.flush()
            return row
        for key, value in fields.items():
            if not hasattr(existing, key):
                # A misspelled/renamed field would otherwise silently set a
                # non-persisted plain attribute on the update path (while
                # the create path above would raise TypeError immediately) --
                # fail the same way on both paths instead of only on insert.
                raise AttributeError(f"{type(existing).__name__} has no attribute {key!r}")
            setattr(existing, key, value)
        self.db.flush()
        return existing
