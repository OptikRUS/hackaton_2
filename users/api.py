from fastapi import APIRouter, HTTPException, Depends, status
from tortoise.contrib.fastapi import HTTPNotFoundError

from .models import User_Pydantic, Users, UserIn_Pydantic
from .schemas import UserRegister
from .security import get_current_user
from .hashing import get_hasher


from pydantic import BaseModel


class Status(BaseModel):
    message: str


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/", response_model=list[User_Pydantic])
async def get_users(current_user=Depends(get_current_user)):
    """
    Все пользователи
    """

    return await User_Pydantic.from_queryset(Users.all())


@users_router.post("/register", response_model=User_Pydantic, status_code=201)
async def user_register(user: UserRegister):
    """
    Регистрация пользователя
    """
    password_hash = get_hasher()
    user.password = password_hash.hash(user.password)
    _user = await Users.filter(username=user.username)
    if _user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User {user.username} already exist")
    new_user = await Users.create(**user.dict(exclude_unset=True))
    return await User_Pydantic.from_tortoise_orm(new_user)


@users_router.get(
    "/{user_id}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def get_user(user_id: int):
    """
    Получить пользователя
    """

    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@users_router.put(
    "/{user_id}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def update_user(user_id: int, user: UserIn_Pydantic):
    """
    Изменить информацию пользователя
    """

    await Users.filter(id=user_id).update(**user.dict(exclude_unset=True))
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@users_router.delete("/{user_id}", response_model=Status, responses={404: {"model": HTTPNotFoundError}})
async def delete_user(user_id: int):
    """
    Удалить пользователя
    """

    user_is_deleted = await Users.filter(id=user_id).delete()
    if not user_is_deleted:
        raise HTTPException(status_code=404, detail=f"Пользователь {user_id} не найден")
    return Status(message=f"Пользователь {user_id} удалён")
