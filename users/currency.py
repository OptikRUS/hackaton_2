from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.types import Decimal


class CurrencyType(str, Enum):
    RUB = "RUB"
    USD = "USD"


class CreateCurrency(BaseModel):
    value: Decimal = Field('100')
    currency_type: CurrencyType


class CreateCheck(CreateCurrency):
    id: int
    created_at_at: datetime


class CurrencyUpdate(CreateCurrency):
    id: int
    updated_at: datetime

