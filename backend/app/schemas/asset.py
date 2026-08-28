from pydantic import BaseModel, ConfigDict, Field

from app.models.asset import ASSET_TYPES, VALUATION_METHODS

_ASSET_TYPE_PATTERN = f"^({'|'.join(ASSET_TYPES)})$"
_VALUATION_METHOD_PATTERN = f"^({'|'.join(VALUATION_METHODS)})$"


class AssetCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    asset_type: str = Field(pattern=_ASSET_TYPE_PATTERN)
    market: str | None = None
    currency: str = Field(default="TWD", max_length=10)
    sector: str | None = None
    industry: str | None = None
    valuation_method: str = Field(default="TRANSACTION_BASED", pattern=_VALUATION_METHOD_PATTERN)


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    market: str | None = None
    sector: str | None = None
    industry: str | None = None
    valuation_method: str | None = Field(default=None, pattern=_VALUATION_METHOD_PATTERN)
    needs_review: bool | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: str
    asset_type: str
    market: str | None
    currency: str
    sector: str | None
    industry: str | None
    valuation_method: str
    is_demo_data: bool
    needs_review: bool
