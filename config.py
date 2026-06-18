from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ==================== SERVER CONFIGURATION ====================
    ENVIRONMENT: str = Field(default="development", description="App environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # ==================== DATABASE CONFIGURATION ====================
    POSTGRES_DB_HOST: str = Field(description="PostgreSQL host")
    POSTGRES_DB_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(description="PostgreSQL database name")
    POSTGRES_USER: str = Field(description="PostgreSQL user")
    POSTGRES_PASSWORD: str = Field(description="PostgreSQL password")

    # ==================== JWT / ADMIN AUTH CONFIGURATION ====================
    JWT_SECRET_KEY: str = Field(default="change-me", description="JWT signing secret")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Admin token expiry in minutes (24h)")

    @property
    def asyncpg_url(self) -> str:
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_DB_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


settings = Settings()
