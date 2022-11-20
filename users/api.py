from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from httpx import ReadTimeout
from pydantic.types import Decimal
from tortoise.contrib.fastapi import HTTPNotFoundError
from tortoise.transactions import in_transaction
from tortoise.exceptions import OperationalError

from .models import (User_Pydantic, Users, Checks, Transfers,
                     TransfersIn_Pydantic, HistoryConvert_Pydantic, HistoryConvert)
from .schemas import UserRegister, UserApproved, UserBlocked, Token, UserUpdate
from .currency import CurrencyUpdate, CreateCheck, CurrencyType, ConverterCurrency, CurrencyList
from .converter import currency_converter, currency_list

from .hashing import get_hasher
from .security import authenticate_user, get_current_active_user, signJWT


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/currency_types", response_model=CurrencyList, status_code=200)
async def get_currency_types(current_user: Users = Depends(get_current_active_user)):
    """
    Расшифровка кодов валют
    """
    try:
        return await currency_list()
    except ReadTimeout:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
        )


@users_router.get("/histories", response_model=list[HistoryConvert_Pydantic] | HistoryConvert_Pydantic, status_code=200)
async def get_history(current_user: Users = Depends(get_current_active_user)):
    """
    История всех конвертаций (только для админа)
    """
    if current_user.is_superuser:
        histories = await HistoryConvert_Pydantic.from_queryset(HistoryConvert.all())
        if histories:
            return histories
        raise HTTPException(
            status_code=status.HTTP_200_OK, detail="Пока конвертаций не было"
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет прав для данного действия"
    )


@users_router.get("/history", response_model=list[HistoryConvert_Pydantic] | HistoryConvert_Pydantic, status_code=200)
async def get_user_history(current_user: Users = Depends(get_current_active_user)):
    """
    История всех конвертаций пользователя
    """
    history = await HistoryConvert_Pydantic.from_queryset(HistoryConvert.filter(user_id=current_user.id))
    if history:
        return history
    raise HTTPException(
        status_code=status.HTTP_200_OK, detail="У вас не было ещё ковертаций"
    )


@users_router.get("/checks/{user_id}", response_model=list[CreateCheck] | CreateCheck, status_code=200)
async def get_user_checks(user_id: int, current_user: Users = Depends(get_current_active_user)):
    """
    Счета пользователя (для админа)
    """
    if current_user.is_superuser:
        check = await Checks.get_or_none(user_id=user_id)
        if not check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Нет пользователя с такими счетами"
            )
        return check
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет прав для данного действия"
    )


@users_router.get("/checks/", response_model=list[CreateCheck] | CreateCheck, status_code=200)
async def get_my_checks(current_user: Users = Depends(get_current_active_user)):
    """
    Счета пользователя
    """
    return await Checks.filter(user_id=current_user.id)


@users_router.get("/unapproved", response_model=list[UserApproved] | UserApproved, status_code=200)
async def get_unapproved_users(current_user: Users = Depends(get_current_active_user)):
    """
    Список неподтверждённых пользователей (для админа)
    """
    if current_user.is_superuser:
        users_list = await Users.filter(is_approved=False, is_superuser=False).all()
        if users_list:
            return users_list
        raise HTTPException(
            status_code=status.HTTP_200_OK, detail="Пока нет неподтверждённых пользователей"
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет прав для данного действия"
    )


@users_router.get("/approved", response_model=list[UserApproved] | UserApproved, status_code=200)
async def get_approved_users(current_user: Users = Depends(get_current_active_user)):
    """
    Список подтверждённых пользователей (для админа)
    """
    if current_user.is_superuser:
        users_list = await Users.filter(is_approved=True, is_superuser=False).all()
        if users_list:
            return users_list
        raise HTTPException(
            status_code=status.HTTP_200_OK, detail="Пока нет подтверждённых пользователей"
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет прав для данного действия"
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


@users_router.post("/create_check", response_model=CreateCheck, status_code=201)
async def create_check(currency: CurrencyType, current_user: Users = Depends(get_current_active_user)):
    """
    Регистрация нового счёта
    """
    is_check = await Checks.get_or_none(user_id=current_user.id, currency_type=currency)

    if is_check:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=f"У вас уже есть {currency.name} счёт"
        )

    # дополнительная проверка на бэке
    if not (currency in list(CurrencyType)):
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=f"Вы не можете создать {currency.name} счёт"
        )

    # создание нового счёта
    new_check = await Checks.create(currency_type=currency)
    await new_check.user_id.add(current_user)
    await new_check.save()
    return CreateCheck.from_orm(new_check)


@users_router.put("/convert", response_model=list[ConverterCurrency] | ConverterCurrency, status_code=200)
async def convert_currency(
        type_from: CurrencyType,
        type_to: CurrencyType,
        value: Decimal,
        current_user: Users = Depends(get_current_active_user)
):
    """
    Конвертация валют
    """
    is_check_from = await Checks.get_or_none(user_id=current_user.id, currency_type=type_from, is_open=True)
    if not is_check_from:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"У вас нет {type_from.name} счёта или он закрыт"
        )

    if is_check_from.value < value:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=f"У вас недостаточно средствн на {type_from.name} счёту"
        )

    is_check_to = await Checks.get_or_none(user_id=current_user.id, currency_type=type_to, is_open=True)
    if not is_check_to:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"У вас нет {type_to.name} счёта или он закрыт"
        )
    try:
        convert = await currency_converter(
            currency_from=type_from.name, currency_to=type_to.name, value=str(value)
        )
    except ReadTimeout:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
        )
    converter_value = Decimal(convert.get("result"))
    is_check_from.value -= value
    is_check_to.value += converter_value
    try:
        async with in_transaction() as connection:
            await is_check_from.save(using_db=connection)
            await is_check_to.save(using_db=connection)
            await HistoryConvert.create(
                user_id=current_user,
                currency_type_from=type_from,
                currency_type_to=type_to,
                value_from=value,
                value_to=converter_value
            )
            return await Checks.filter(user_id=current_user.id).all()

    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@users_router.patch("/refill", response_model=CurrencyUpdate, status_code=200)
async def user_refill(
        amount: Decimal, currency: CurrencyType, current_user: Users = Depends(get_current_active_user)
):
    """
    Пополнение баланса
    """
    if currency != CurrencyType.RUB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Для пополнения пока доступно только {CurrencyType.RUB.name}"
        )
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
    check = await Checks.get_or_none(user_id=current_user.id, is_open=True, currency_type=currency.name)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Открытые счета не найдены")
    check.value += amount
    await check.save()
    return check


@users_router.patch("/unfill", response_model=CurrencyUpdate, status_code=200)
async def user_unfill(
        amount: Decimal, currency: CurrencyType, current_user: Users = Depends(get_current_active_user)
):
    """
    Вывод средств со счёта
    """
    if currency != CurrencyType.RUB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Для вывода средств пока доступно только {CurrencyType.RUB.name}"
        )
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
    check = await Checks.get_or_none(user_id=current_user.id, is_open=True, currency_type=currency.name)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Открытые счета не найдены")

    if amount > check.value:
        raise HTTPException(status_code=status.HTTP_200_OK, detail=f"У нас недостаточно средств")

    check.value -= amount
    await check.save()
    return check


@users_router.patch("/approve/{user_id}", response_model=UserApproved, status_code=200)
async def user_approve(user_id: int, current_user: Users = Depends(get_current_active_user)):
    """
    Подтвержение пользователя администратором
    """
    if current_user.is_superuser:
        _user = await Users.filter(id=user_id, is_approved=False).update(is_approved=True)
        if not _user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден или уже подтверждён"
            )
        user = await Users.get(id=user_id)
        return UserApproved.from_orm(user)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет прав для данного действия"
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


@users_router.patch(
    "/transfer", response_model=TransfersIn_Pydantic, status_code=200
)
async def create_transfer(
        currency: CurrencyType, user_id: int, value: Decimal, current_user: Users = Depends(get_current_active_user)
):
    """
    Перевод средств между пользователями
    """
    # проверка отправителя
    if not current_user.is_active and not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Отправитель не найден, заблокирован или не подтверждён"
        )

    # проверка получателя
    user_to = await Users.get_or_none(id=user_id, is_active=True, is_approved=True)
    if not user_to:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Получатель не найден, заблокирован или не подтверждён"
        )

    if current_user == user_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Вы не можете переводить средства самому себе"
        )

    try:
        async with in_transaction() as connection:
            transfer = Transfers(
                user_from=current_user,
                user_to=user_to,
                value=value,
                currency_type=currency
            )
            check_from = await Checks.get_or_none(
                user_id=current_user.id, is_open=True, currency_type=currency
            )
            if check_from.value < value:
                raise HTTPException(
                    status_code=status.HTTP_200_OK,
                    detail=f"У вас недостаточно средствн на {currency.name} счёту"
                )
            if not check_from:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Открытый счёт {currency.name} отправителя не найден"
                )
            check_to = await Checks.get_or_none(
                user_id=user_to.id, is_open=True, currency_type=currency
            )
            if not check_to:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Открытый счёт {currency.name} получателя не найден"
                )
            check_to.value += value
            check_from.value -= value
            await transfer.save(using_db=connection)
            await check_to.save()
            await check_from.save()
            return await TransfersIn_Pydantic.from_tortoise_orm(transfer)

    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@users_router.get(
    "/me", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def get_me(current_user: Users = Depends(get_current_active_user)):
    """
    Получить информацию о текущем пользователе
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
    Изменить информацию текущего пользователя
    """
    await Users.filter(id=current_user.id).update(**user_data.dict(exclude_unset=True))
    return await User_Pydantic.from_queryset_single(Users.get(id=current_user.id))
