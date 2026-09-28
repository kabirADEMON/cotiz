from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.deps import DB, CurrentUser, exiger_tresorier
from app.errors import NonTrouve
from app.models import MembreTontine, MethodePaiement, Paiement, StatutPaiement
from app.schemas import PaiementHistorique, PaiementOut
from app.services.fedapay import FedaPayClient, get_fedapay
from app.services.paiements import appliquer_statut_fedapay

router = APIRouter(prefix="/paiements", tags=["Paiements"])


def vers_historique(paiement: Paiement) -> PaiementHistorique:
    return PaiementHistorique(
        **PaiementOut.model_validate(paiement).model_dump(),
        tontine_id=paiement.cycle.tontine_id,
        tontine_nom=paiement.cycle.tontine.nom,
        cycle_numero=paiement.cycle.numero,
    )


@router.get("/me", response_model=list[PaiementHistorique])
def mes_paiements(db: DB, user: CurrentUser):
    requete = (
        select(Paiement)
        .join(MembreTontine)
        .where(MembreTontine.user_id == user.id)
        .order_by(Paiement.created_at.desc(), Paiement.id.desc())
    )
    return [vers_historique(p) for p in db.scalars(requete)]


@router.post("/{paiement_id}/verifier", response_model=PaiementOut)
def verifier(
    paiement_id: int,
    db: DB,
    user: CurrentUser,
    fedapay: Annotated[FedaPayClient, Depends(get_fedapay)],
):
    """Interroge FedaPay pour mettre à jour un paiement en attente.

    Appelé par le frontend au retour de la page de paiement : utile en local, où le
    webhook FedaPay ne peut pas joindre l'API.
    """
    paiement = db.get(Paiement, paiement_id)
    if paiement is None:
        raise NonTrouve("Paiement introuvable")
    if paiement.membre.user_id != user.id:
        exiger_tresorier(db, paiement.cycle.tontine_id, user)

    if paiement.methode == MethodePaiement.FEDAPAY and paiement.statut == StatutPaiement.EN_ATTENTE:
        statut = fedapay.statut_transaction(paiement.fedapay_transaction_id)
        appliquer_statut_fedapay(db, paiement, statut)
    return paiement

