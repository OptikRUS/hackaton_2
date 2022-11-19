from datetime import datetime

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str
    first_name: str
    last_name: str
    password: str = Field(min_length=8, max_length=20)


class UserResponse(BaseModel):
    username: str
    updated_at: datetime

    class Config:
        orm_mode = True


class UserApproved(UserResponse):
    is_approved: bool


class UserBlocked(UserResponse):
    is_active: bool


class Transfer(BaseModel):
    user_from: int
    user_to: int
    value: float
    currency_type: str = Field('RUB')


# class Login(BaseModel):
#     username: str
#     password: str
#
#
# class Token(BaseModel):
#     access_token: str
#     token_type: str
#
#
# class TokenData(BaseModel):
#     username: str = None