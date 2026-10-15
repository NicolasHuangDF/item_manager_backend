from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

#: 项目根目录。app/core/config.py -> app/core -> app -> 项目根
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 绝对路径：无论从哪个工作目录启动都能读到 .env
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "家庭物品收纳管理服务"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # 必填：不再提供不安全的默认密钥，缺失时启动即报错
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str = (
        "mysql+aiomysql://root:password@127.0.0.1:3306/"
        "item_manager?charset=utf8mb4"
    )
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # NoDecode：阻止 pydantic-settings 对列表字段做 JSON 预解析，
    # 使 .env 中可以用逗号分隔（如 CORS_ORIGINS=* 或 http://a.com,http://b.com）
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["*"]
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    @field_validator("SECRET_KEY")
    @classmethod
    def check_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY 长度至少 32 个字符，请用 secrets.token_urlsafe(48) 生成")
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
