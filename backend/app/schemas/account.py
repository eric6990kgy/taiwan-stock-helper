from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.account import ACCOUNT_TYPES

_ACCOUNT_TYPE_PATTERN = f"^({'|'.join(ACCOUNT_TYPES)})$"


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    account_type: str = Field(pattern=_ACCOUNT_TYPE_PATTERN)
    currency: str = Field(default="TWD", max_length=10)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    account_type: str | None = Field(default=None, pattern=_ACCOUNT_TYPE_PATTERN)


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    account_type: str
    currency: str
    created_at: datetime
