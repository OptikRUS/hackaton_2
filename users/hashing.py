from config import auth_config
from passlib.context import CryptContext


def get_hasher() -> CryptContext:
    """
    Получение хэшера
    """
    hasher: CryptContext = CryptContext(
        schemes=auth_config["hasher_schemes"], deprecated=auth_config["hasher_deprecated"]
    )
    return hasher
