from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

from .currency import CurrencyType


class Users(models.Model):
    """
    Модель пользователя
    """

    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=20, unique=True)
    first_name = fields.CharField(max_length=50, null=True)
    last_name = fields.CharField(max_length=50, null=True)
    password = fields.CharField(max_length=128, null=True)
    is_active = fields.BooleanField(default=True)
    is_approved = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def full_name(self) -> str:
        """
        Полное имя
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    class PydanticMeta:
        computed = ["full_name"]
        exclude = ["password"]


class Checks(models.Model):
    """
    Счета пользователей
    """
    id = fields.IntField(pk=True)
    user_id = fields.ManyToManyField('models.Users', related_name='user_id', through='users_checks')
    value = fields.DecimalField(max_digits=100, decimal_places=2, default=0)
    currency_type = fields.CharEnumField(CurrencyType, default=CurrencyType.RUB)
    is_open = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Transfers(models.Model):
    """
    Транзакции пользователей
    """
    id = fields.IntField(pk=True)
    user_to = fields.ForeignKeyField('models.Users', related_name='user_to')
    user_from = fields.ForeignKeyField('models.Users', related_name='user_from')
    value = fields.DecimalField(max_digits=100, decimal_places=2)
    currency_type = fields.CharEnumField(CurrencyType, default=CurrencyType.RUB)
    created_at = fields.DatetimeField(auto_now_add=True)

    class PydanticMeta:
        exclude = ["id"]


class HistoryConvert(models.Model):
    """
    Истории конвертаций
    """
    id = fields.IntField(pk=True)
    user_id = fields.ForeignKeyField('models.Users')
    currency_type_from = fields.CharEnumField(CurrencyType)
    currency_type_to = fields.CharEnumField(CurrencyType)
    value_to = fields.DecimalField(max_digits=100, decimal_places=2)
    value_from = fields.DecimalField(max_digits=100, decimal_places=2)
    created_at = fields.DatetimeField(auto_now_add=True)


User_Pydantic = pydantic_model_creator(Users, name="User")
UserIn_Pydantic = pydantic_model_creator(Users, name="UserIn", exclude_readonly=True)
TransfersIn_Pydantic = pydantic_model_creator(Transfers, name="TransfersIn")
HistoryConvert_Pydantic = pydantic_model_creator(HistoryConvert, name="HistoryConvert")
