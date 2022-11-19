from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.types import Decimal


class CurrencyType(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class CreateCurrency(BaseModel):
    value: Decimal = Field('100')
    currency_type: CurrencyType


class CreateCheck(CreateCurrency):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class CurrencyUpdate(CreateCurrency):
    id: int
    updated_at: datetime

