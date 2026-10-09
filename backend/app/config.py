from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valeurs d'exemple, connues de quiconque lit ce dépôt : elles permettraient de fabriquer
# un jeton de session valide. Acceptées seulement en développement.
EXAMPLE_JWT_SECRETS = {"dev-secret-a-changer", "remplacer-par-une-longue-chaine-aleatoire"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://tontine:tontine@localhost:5432/tontine"
    app_env: str = "development"
    jwt_secret: str = "dev-secret-a-changer"
    jwt_expire_minutes: int = 60 * 24

    fedapay_env: str = "sandbox"
    fedapay_secret_key: str = ""
    fedapay_webhook_secret: str = ""

    frontend_url: str = "http://localhost:5180"

    @model_validator(mode="after")
    def require_real_jwt_secret(self) -> "Settings":
        # Hors développement, ou dès que FedaPay encaisse de l'argent réel.
        exposed = self.app_env.lower() not in {"development", "dev", "local", "test"} or self.fedapay_env == "live"
        if exposed and (self.jwt_secret in EXAMPLE_JWT_SECRETS or len(self.jwt_secret) < 32):
            raise ValueError(
                "JWT_SECRET doit être une vraie clé de 32 caractères minimum hors développement. "
                "Générez-en une : python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self

    @property
    def fedapay_base_url(self) -> str:
        if self.fedapay_env == "live":
            return "https://api.fedapay.com/v1"
        return "https://sandbox-api.fedapay.com/v1"


settings = Settings()
