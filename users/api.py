from fastapi import APIRouter, HTTPException, Depends, status
from tortoise.contrib.fastapi import HTTPNotFoundError
from tortoise.transactions import in_transaction
from tortoise.exceptions import OperationalError

from .models import User_Pydantic, Users, UserIn_Pydantic, Checks, Transfers, TransfersIn_Pydantic
from .schemas import UserRegister, UserApproved, UserBlocked, Transfer, Refill
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


@users_router.get("/unapproved", response_model=list[UserApproved])
async def get_unapproved_users():
    """
    Список неподтверждённых пользователей
    """
    users_list = await Users.filter(is_approved=False).all()
    if users_list:
        return users_list
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Нет неподтверждённых пользователей"
    )


@users_router.get("/approved", response_model=list[UserApproved])
async def get_approved_users():
    """
    Список подтверждённых пользователей
    """
    users_list = await Users.filter(is_approved=True).all()
    if users_list:
        return users_list
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Нет подтверждённых пользователей"
    )


@users_router.post("/register", response_model=User_Pydantic, status_code=201)
async def user_register(user: UserRegister):
    """
    Регистрация пользователя
    """
    password_hash = get_hasher()
    user.password = password_hash.hash(user.password)
    _user = await Users.get_or_none(username=user.username)
    if _user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Пользователь {_user.username} уже существует"
        )
    new_user = await Users.create(**user.dict(exclude_unset=True))

    # создание нового счёта
    new_check = await Checks.create()
    await new_check.user_id.add(new_user)
    return await User_Pydantic.from_tortoise_orm(new_user)


@users_router.put("/refill", status_code=201)
async def user_register(user_id: int, ):
    """
    Пополнение баланса
    """
    _user = await Users.get_or_none(id=user_id)

    if not _user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not _user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Пользователь {_user.username} не подтверждён"
        )
    if not _user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Пользователь {_user.username} заблокирован"
        )


@users_router.patch("/approve/{user_id}", response_model=UserApproved, status_code=200)
async def user_approve(user_id: int):
    """
    Подтвержени пользователя администратором
    """
    _user = await Users.filter(id=user_id, is_approved=False).update(is_approved=True)
    if not _user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Пользователь не найден или уже подтверждён"
        )
    user = await Users.get(id=user_id)
    return UserApproved.from_orm(user)


@users_router.patch("/block/{user_id}", response_model=UserBlocked, status_code=200)
async def user_block(user_id: int):
    """
    Блокировка пользователя администратором
    """
    _user = await Users.filter(id=user_id, is_active=True).update(is_active=False)
    if not _user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Пользователь не найден или уже заблокирован"
        )
    user = await Users.get(id=user_id)
    return UserBlocked.from_orm(user)


@users_router.put(
    "/transfer", response_model=TransfersIn_Pydantic, status_code=200
)
async def create_transfer(transfer_data: Transfer):
    """
    Перевод
    """
    # проверка отправителя
    user_from = await Users.get_or_none(id=transfer_data.user_from)
    if not user_from:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Поулчатель не найден, заблокирован или не подтверждён"
        )

    # проверка получателя
    user_to = await Users.get_or_none(id=transfer_data.user_to, is_active=True, is_approved=True)
    if not user_to:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Отправитель не найден, заблокирован или не подтверждён"
        )

    try:
        async with in_transaction() as connection:
            transfer = Transfers(
                user_from=user_from,
                user_to=user_to,
                value=transfer_data.value,
                currency_type=transfer_data.currency_type
            )
            await transfer.save(using_db=connection)
            return await TransfersIn_Pydantic.from_tortoise_orm(transfer)

    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.get(
    "/{user_id}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def get_user(user_id: int):
    """
    Получить пользователя
    """

    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@users_router.get(
    "/login/{username}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def login(username: str):
    """
    Типа логин
    """
    return await User_Pydantic.from_queryset_single(Users.get(username=username))


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
