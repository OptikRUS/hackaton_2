from pydantic import BaseSettings, Field


class SiteSettings(BaseSettings):
    host: str = Field("127.0.0.1", env="SITE_HOST")
    port: int = Field(8000, env="SITE_PORT")
    # reload: bool = Field(True, env="SITE_RELOAD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ApplicationSettings(BaseSettings):
    title: str = Field("Currency Converter Sovcombank Team Challenge 2022")
    description = Field("Приложения для конвертирования валют")
    debug: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class DataBaseSettings(BaseSettings):

    # postgres
    # database_url: str = Field("postgres://{user}:{password}@{host}:{port}/{database}")
    # port: str = Field("5432", env="DATABASE_PORT")
    # user: str = Field("postgres", env="DATABASE_USER")
    # host: str = Field("db_app", env="DATABASE_HOST")
    # password: str = Field("postgres", env="DATABASE_PASSWORD")
    # database: str = Field("postgres", env="DATABASE_NAME")

    # sqlite
    database_url: str = Field("sqlite://{db_name}.db")
    db_name: str = Field("db_app", env="DATABASE_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class AuthSettings(BaseSettings):
    type: str = Field("Bearer")
    password_time: int = Field(3)
    algorithm: str = Field("HS256")
    expires: int = Field(60*60)
    hasher_deprecated: str = Field("auto")
    hasher_schemes: list[str] = Field(["bcrypt"])

    secret_key: str = Field("secret_key", env="AUTH_SECRET_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class CORSSettings(BaseSettings):
    allow_credentials: bool = Field(True)
    allow_methods: list[str] = Field(["*"])
    allow_headers: list[str] = Field(["*", "Authorization"])
    allow_origins: list[str] = Field(["*"], env="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class CurrencyApiHeaders(BaseSettings):
    apikey: str = Field("taPxAI02BK4NITCwpZxqiCy3nDNXdtzs", env="API_KEY")


class CurrencyApiSettings(BaseSettings):
    apikey: str = Field(CurrencyApiHeaders().apikey)
    headers: dict = CurrencyApiHeaders().dict()
    url: str = Field("https://api.apilayer.com/exchangerates_data", env="API_URL")
