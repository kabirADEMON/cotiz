"""Client minimal pour l'API FedaPay (https://docs.fedapay.com)."""

import hashlib
import hmac
import time

import httpx

from app.config import settings
from app.errors import ErreurMetier


class FedaPayError(ErreurMetier):
    def __init__(self, message: str):
        super().__init__(f"FedaPay : {message}", 502)


class FedaPayClient:
    def __init__(self, secret_key: str, base_url: str, timeout: float = 15):
        self.http = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {secret_key}"},
        )

    def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = self.http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise FedaPayError("service injoignable") from exc
        if response.is_error:
            raise FedaPayError(f"erreur {response.status_code} ({response.text[:200]})")
        return response.json()

    def creer_transaction(
        self,
        montant: int,
        description: str,
        callback_url: str,
        prenom: str,
        nom: str,
        telephone: str,
        email: str | None = None,
    ) -> tuple[str, str]:
        """Crée une transaction et renvoie (id de la transaction, URL de paiement)."""
        client = {
            "firstname": prenom,
            "lastname": nom,
            "phone_number": {"number": telephone, "country": "bj"},
        }
        if email:
            client["email"] = email
        data = self._request(
            "POST",
            "/transactions",
            json={
                "description": description,
                "amount": montant,
                "currency": {"iso": "XOF"},
                "callback_url": callback_url,
                "customer": client,
            },
        )
        transaction_id = str(data["v1/transaction"]["id"])
        token = self._request("POST", f"/transactions/{transaction_id}/token")
        return transaction_id, token["url"]

    def statut_transaction(self, transaction_id: str) -> str:
        """Statut FedaPay : pending, approved, declined, canceled, refunded, transferred…"""
        data = self._request("GET", f"/transactions/{transaction_id}")
        return data["v1/transaction"]["status"]


def verifier_signature(payload: bytes, entete: str | None, secret: str, tolerance: int = 300) -> bool:
    """Vérifie l'en-tête `X-FEDAPAY-SIGNATURE` (format `t=<timestamp>,s=<hmac sha256>`)."""
    if not entete or not secret:
        return False
    parties = dict(p.split("=", 1) for p in entete.split(",") if "=" in p)
    horodatage, signature = parties.get("t"), parties.get("s")
    if not horodatage or not signature or not horodatage.isdigit():
        return False
    if abs(time.time() - int(horodatage)) > tolerance:
        return False
    attendu = hmac.new(secret.encode(), horodatage.encode() + b"." + payload, hashlib.sha256)
    return hmac.compare_digest(attendu.hexdigest(), signature)


def get_fedapay() -> FedaPayClient:
    """Dépendance FastAPI (remplacée par un faux client dans les tests)."""
    if not settings.fedapay_secret_key:
        raise ErreurMetier("FedaPay n'est pas configuré (FEDAPAY_SECRET_KEY manquante)", 503)
    return FedaPayClient(settings.fedapay_secret_key, settings.fedapay_base_url)
