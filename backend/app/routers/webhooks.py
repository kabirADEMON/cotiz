import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import DB
from app.models import Paiement
from app.services.fedapay import FedaPayClient, get_fedapay, verifier_signature
from app.services.paiements import appliquer_statut_fedapay

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _traiter(db: Session, fedapay: FedaPayClient, transaction_id: str) -> None:
    paiement = db.scalar(select(Paiement).where(Paiement.fedapay_transaction_id == transaction_id))
    if paiement is None:
        return  # transaction qui ne vient pas de cette application
    # On ne se fie pas au contenu de l'événement : le statut est relu auprès de FedaPay.
    statut = fedapay.statut_transaction(transaction_id)
    appliquer_statut_fedapay(db, paiement, statut)


@router.post("/fedapay", include_in_schema=False)
async def fedapay_webhook(
    request: Request,
    db: DB,
    fedapay: Annotated[FedaPayClient, Depends(get_fedapay)],
):
    payload = await request.body()
    signature = request.headers.get("x-fedapay-signature")
    if not verifier_signature(payload, signature, settings.fedapay_webhook_secret):
        raise HTTPException(400, "Signature invalide")

    try:
        transaction_id = str(json.loads(payload)["entity"]["id"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Événement illisible")

    await run_in_threadpool(_traiter, db, fedapay, transaction_id)
    return {"recu": True}
