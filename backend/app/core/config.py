from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_SCHEMA: str = "public"

    @property
    def DATABASE_URL(self) -> str:
        # URL-encode user/password so special chars like '@' don't break the DSN
        return (
            f"postgresql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    SECRET_KEY: str = "super_secret_eduverse_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    CORS_ORIGINS: str = (
        "http://localhost,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "https://aieduconnect.netlify.app,"
        "https://educonnect-k1tl.onrender.com"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
