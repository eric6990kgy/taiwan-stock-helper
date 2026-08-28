"""Service-layer domain exceptions. Routes translate these to HTTP status
codes in one place (app/main.py's exception handlers) rather than each route
handling errors ad hoc — keeps controllers thin.
"""


class NotFoundError(Exception):
    """A requested resource (account, asset, transaction, ...) doesn't exist."""


class DuplicateError(Exception):
    """A uniqueness rule was violated (e.g. ticker already exists)."""


class UnsupportedCurrencyError(ValueError):
    """V1 is TWD-only (architecture decision A3) — enforced here, not by a
    DB constraint, so adding FX support later doesn't require a migration."""

    def __init__(self, currency: str):
        self.currency = currency
        super().__init__(f"Unsupported currency: {currency!r}. V1 only supports TWD-denominated transactions.")


class InvalidAmountError(ValueError):
    """A quantity/price/fee/tax value fails a business rule (PRD Sec.39 —
    surfaced as a clear message, not a bare 'something went wrong')."""
