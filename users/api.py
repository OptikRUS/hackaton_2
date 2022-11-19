from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from tortoise.contrib.fastapi import HTTPNotFoundError
from tortoise.transactions import in_transaction
from tortoise.exceptions import OperationalError

from .models import User_Pydantic, Users, UserIn_Pydantic, Checks, Transfers, TransfersIn_Pydantic
from .schemas import UserRegister, UserApproved, UserBlocked, Transfer, Token, Login, UserUpdate, Refill
from .currency import CurrencyUpdate, CreateCurrency, CreateCheck, CurrencyType

from .hashing import get_hasher
from .security import authenticate_user, get_current_active_user, signJWT

from pydantic import BaseModel


class Status(BaseModel):
    message: str


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/", response_model=list[User_Pydantic])
async def get_users(current_user: Users = Depends(get_current_active_user)):
    """
    Все пользователи
    """

    return await User_Pydantic.from_queryset(Users.all())


@users_router.get("/unapproved", response_model=list[UserApproved])
async def get_unapproved_users(current_user: Users = Depends(get_current_active_user)):
    """
    Список неподтверждённых пользователей
    """
    if current_user.is_superuser:
        users_list = await Users.filter(is_approved=False).all()
        if users_list:
            return users_list
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Нет неподтверждённых пользователей"
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=f"У вас нет прав для данного действия"
    )


@users_router.get("/approved", response_model=list[UserApproved])
async def get_approved_users(current_user: Users = Depends(get_current_active_user)):
    """
    Список подтверждённых пользователей
    """
    if current_user.is_superuser:
        users_list = await Users.filter(is_approved=True).all()
        if users_list:
            return users_list
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Нет подтверждённых пользователей"
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=f"У вас нет прав для данного действия"
    )


@users_router.post('/token', response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = signJWT(username=form_data.username)
    return access_token


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


@users_router.post("/create_check", status_code=201)
async def user_register(currency: CurrencyType, current_user: Users = Depends(get_current_active_user)):
    """
    Регистрация нового счёта
    """
    is_check = await Checks.get_or_none(user_id=current_user.id, currency_type=currency)

    if is_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"У вас уже есть {currency.name} счёт"
        )

    # дополнительная проверка на бэке
    if not (currency in list(CurrencyType)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Вы не можете создать {currency.name} счёт"
        )

    # создание нового счёта
    new_check = await Checks.create(currency_type=currency)
    await new_check.user_id.add(current_user)
    await new_check.save()
    return new_check


@users_router.put("/refill", response_model=CurrencyUpdate, status_code=200)
async def user_refill(currency_data: Refill, current_user: Users = Depends(get_current_active_user)):
    """
    Пополнение баланса
    """

    if not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Пользователь {current_user.username} не подтверждён"
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Пользователь {current_user.username} заблокирован"
        )
    # проверка существования счёта
    check = await Checks.get_or_none(user_id=current_user.id, is_open=True, currency_type=currency_data.currency_type)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Открытые счета не найдены")
    check.value += currency_data.value
    await check.save()
    return check


@users_router.patch("/approve/{user_id}", response_model=UserApproved, status_code=200)
async def user_approve(user_id: int, current_user: Users = Depends(get_current_active_user)):
    """
    Подтвержени пользователя администратором
    """
    if current_user.is_superuser:
        _user = await Users.filter(id=user_id, is_approved=False).update(is_approved=True)
        if not _user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Пользователь не найден или уже подтверждён"
            )
        user = await Users.get(id=user_id)
        return UserApproved.from_orm(user)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=f"У вас нет прав для данного действия"
    )


@users_router.patch("/block/{user_id}", response_model=UserBlocked, status_code=200)
async def user_block(user_id: int, current_user: Users = Depends(get_current_active_user)):
    """
    Блокировка пользователя администратором
    """
    if current_user.is_superuser:
        _user = await Users.filter(id=user_id, is_active=True).update(is_active=False)
        if not _user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Пользователь не найден или уже заблокирован"
            )
        user = await Users.get(id=user_id)
        return UserBlocked.from_orm(user)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=f"У вас нет прав для данного действия"
    )


@users_router.put(
    "/transfer", response_model=TransfersIn_Pydantic, status_code=200
)
async def create_transfer(transfer_data: Transfer, current_user: Users = Depends(get_current_active_user)):
    """
    Перевод
    """
    # проверка отправителя
    if not current_user.is_active and not current_user.is_approved:
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
                user_from=current_user,
                user_to=user_to,
                value=transfer_data.value,
                currency_type=transfer_data.currency_type
            )
            await transfer.save(using_db=connection)
            return await TransfersIn_Pydantic.from_tortoise_orm(transfer)

    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.get(
    "/me", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def get_me(current_user: Users = Depends(get_current_active_user)):
    """
    Получить текущего пользователя
    """
    return current_user


@users_router.get(
    "/login/{username}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def login(username: str):
    """
    Типа логин
    """
    return await User_Pydantic.from_queryset_single(Users.get(username=username))


@users_router.put(
    "/update_profile", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def update_user(user_data: UserUpdate, current_user: Users = Depends(get_current_active_user)):
    """
    Изменить информацию пользователя
    """

    await Users.filter(id=current_user.id).update(**user_data.dict(exclude_unset=True))
    return await User_Pydantic.from_queryset_single(Users.get(id=current_user.id))


# @users_router.delete("/{user_id}", response_model=Status, responses={404: {"model": HTTPNotFoundError}})
# async def delete_user(user_id: int, current_user: Users = Depends(get_current_active_user)):
#     """
#     Удалить пользователя
#     """
#
#     user_is_deleted = await Users.filter(id=user_id).delete()
#     if not user_is_deleted:
#         raise HTTPException(status_code=404, detail=f"Пользователь {user_id} не найден")
#     return Status(message=f"Пользователь {user_id} удалён")
