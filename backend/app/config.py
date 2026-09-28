from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://tontine:tontine@localhost:5432/tontine"
    jwt_secret: str = "dev-secret-a-changer"
    jwt_expire_minutes: int = 60 * 24

    fedapay_env: str = "sandbox"
    fedapay_secret_key: str = ""
    fedapay_webhook_secret: str = ""

    frontend_url: str = "http://localhost:5180"

    @property
    def fedapay_base_url(self) -> str:
        if self.fedapay_env == "live":
            return "https://api.fedapay.com/v1"
        return "https://sandbox-api.fedapay.com/v1"


settings = Settings()
