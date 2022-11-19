import time
from fastapi import HTTPException, status, Depends

from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import BaseModel

from config import auth_config
from .models import Users as DB_User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")
pwd_context = CryptContext(schemes=auth_config["hasher_schemes"], deprecated="auto")


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str):
    user = await DB_User.get_or_none(username=username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def signJWT(username: str):
    payload = {
        "username": username,
        "expires": time.time() + auth_config["expires"]
    }
    token = jwt.encode(
        payload=payload,
        key=auth_config["secret_key"],
        algorithm=auth_config["algorithm"]
    )
    return {"access_token": token}


def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(
            jwt=token,
            key=auth_config["secret_key"],
            algorithms=auth_config["algorithm"],
        )
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except:
        return {}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_dict = decodeJWT(token)
    if not token_dict:
        raise credentials_exception
    user = await  DB_User.get_or_none(username=token_dict['username'])
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: DB_User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
