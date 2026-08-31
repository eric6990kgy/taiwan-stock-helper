"""OHLC validation rules (Phase 5 Discovery Report Sec.10)."""

from datetime import date
from decimal import Decimal

import pytest

from app.providers.market_data_provider import PricePointDTO
from app.services.market_data_validation import PriceValidationError, validate_price_point


def point(**overrides):
    defaults = dict(
        date=date(2026, 1, 1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=1000,
        source="FINMIND",
    )
    defaults.update(overrides)
    return PricePointDTO(**defaults)


def test_valid_point_passes():
    validate_price_point(point())  # must not raise


def test_close_must_be_positive():
    with pytest.raises(PriceValidationError, match="close must be > 0"):
        validate_price_point(point(close=Decimal("0")))


def test_close_negative_rejected():
    with pytest.raises(PriceValidationError):
        validate_price_point(point(close=Decimal("-5")))


def test_low_greater_than_open_rejected():
    with pytest.raises(PriceValidationError, match="low.*open"):
        validate_price_point(point(low=Decimal("101"), open=Decimal("100")))


def test_low_greater_than_close_rejected():
    with pytest.raises(PriceValidationError, match="low.*close"):
        validate_price_point(point(open=Decimal("107"), low=Decimal("106"), close=Decimal("105")))


def test_high_less_than_open_rejected():
    with pytest.raises(PriceValidationError, match="high.*open"):
        validate_price_point(point(high=Decimal("99"), open=Decimal("100")))


def test_high_less_than_close_rejected():
    with pytest.raises(PriceValidationError, match="high.*close"):
        validate_price_point(point(high=Decimal("104"), close=Decimal("105")))


def test_negative_volume_rejected():
    with pytest.raises(PriceValidationError, match="volume"):
        validate_price_point(point(volume=-1))


def test_none_volume_is_fine():
    validate_price_point(point(volume=None))  # must not raise -- volume is optional


def test_none_open_high_low_is_fine_when_close_valid():
    """A provider might only give a close price for some rows -- validation
    shouldn't demand OHLC completeness, only internal consistency when
    values are present."""
    validate_price_point(point(open=None, high=None, low=None))
