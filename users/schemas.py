from datetime import datetime
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str
    first_name: str
    last_name: str
    password: str = Field(min_length=8, max_length=20)


class UserApproved(BaseModel):
    username: str
    is_approved: bool
    updated_at: datetime

    class Config:
        orm_mode = True


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