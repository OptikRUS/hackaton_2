from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.types import Decimal


class CurrencyType(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    SRD = "SRD"
    STD = "STD"
    SVC = "SVC"
    SYP = "SYP"
    SZL = "SZL"
    THB = "THB"
    TJS = "TJS"
    TMT = "TMT"
    TND = "TND"
    TOP = "TOP"
    TRY = "TRY"
    TTD = "TTD"
    TWD = "TWD"
    TZS = "TZS"
    UAH = "UAH"
    UGX = "UGX"
    UYU = "UYU"
    UZS = "UZS"
    VEF = "VEF"
    VES = "VES"
    VND = "VND"
    VUV = "VUV"
    WST = "WST"
    XAF = "XAF"
    XAG = "XAG"
    XAU = "XAU"
    XCD = "XCD"
    XDR = "XDR"
    XOF = "XOF"
    XPF = "XPF"
    YER = "YER"
    ZAR = "ZAR"
    ZMK = "ZMK"
    ZMW = "ZMW"
    ZWL = "ZWL"


class CurrencyList(BaseModel):
    success: bool
    currencies: dict = Field('{"RUB": "Russian Ruble"}')


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


class ConverterCurrency(CreateCurrency):
    id: int
    currency_type: CurrencyType
    value: Decimal
    updated_at: datetime
