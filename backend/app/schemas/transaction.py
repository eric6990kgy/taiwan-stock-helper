from datetime import date as date_
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.types import TRANSACTION_TYPES
from app.schemas.common import DecimalStr

_TRANSACTION_TYPE_PATTERN = f"^({'|'.join(TRANSACTION_TYPES)})$"


class TransactionCreate(BaseModel):
    account_id: int
    asset_id: int
    date: date_
    type: str = Field(pattern=_TRANSACTION_TYPE_PATTERN)
    quantity: DecimalStr = Field(gt=0)
    price: DecimalStr = Field(gt=0)
    fee: DecimalStr = Field(default=Decimal("0"), ge=0)
    tax: DecimalStr = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="TWD", max_length=10)
    note: str | None = None


class TransactionUpdate(BaseModel):
    date: date_ | None = None
    type: str | None = Field(default=None, pattern=_TRANSACTION_TYPE_PATTERN)
    quantity: DecimalStr | None = Field(default=None, gt=0)
    price: DecimalStr | None = Field(default=None, gt=0)
    fee: DecimalStr | None = Field(default=None, ge=0)
    tax: DecimalStr | None = Field(default=None, ge=0)
    note: str | None = None


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    asset_id: int
    date: date_
    type: str
    quantity: DecimalStr
    price: DecimalStr
    fee: DecimalStr
    tax: DecimalStr
    currency: str
    note: str | None
    created_at: datetime
