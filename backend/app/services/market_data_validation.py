"""V1 validation rules for ingested market data (Phase 5 Discovery Report
Sec.10). Deliberately small and explicit -- no generic validation framework.
Pure functions over provider DTOs; no DB, no HTTP, importable from anywhere
without side effects.
"""

from app.providers.market_data_provider import PricePointDTO


class PriceValidationError(ValueError):
    """A single price point fails a sanity check. Raised per-row so the
    ingestion service can skip just that row, not the whole ticker."""


def validate_price_point(point: PricePointDTO) -> None:
    if point.close is None or point.close <= 0:
        raise PriceValidationError(f"{point.date}: close must be > 0 (got {point.close!r}).")

    if point.open is not None:
        if point.low is not None and point.low > point.open:
            raise PriceValidationError(f"{point.date}: low ({point.low}) > open ({point.open}).")
        if point.high is not None and point.high < point.open:
            raise PriceValidationError(f"{point.date}: high ({point.high}) < open ({point.open}).")

    if point.low is not None and point.low > point.close:
        raise PriceValidationError(f"{point.date}: low ({point.low}) > close ({point.close}).")
    if point.high is not None and point.high < point.close:
        raise PriceValidationError(f"{point.date}: high ({point.high}) < close ({point.close}).")

    if point.volume is not None and point.volume < 0:
        raise PriceValidationError(f"{point.date}: volume must be >= 0 (got {point.volume}).")
