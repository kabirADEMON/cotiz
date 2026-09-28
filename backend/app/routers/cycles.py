from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import DB, CurrentUser, adhesion, exiger_membre, exiger_tresorier, get_cycle
from app.errors import Interdit, NonTrouve
from app.models import MembreTontine, StatutPaiement
from app.schemas import (
    CycleDetail,
    CycleOut,
    EtatMembreCycle,
    MembreOut,
    PaiementEspeces,
    PaiementFedaPayOut,
    PaiementOut,
    TontineOut,
)
from app.services.cycles import cloturer_cycle
from app.services.fedapay import FedaPayClient, get_fedapay
from app.services.paiements import enregistrer_especes, initier_paiement_fedapay

router = APIRouter(prefix="/cycles", tags=["Cycles"])


@router.get("/{cycle_id}", response_model=CycleDetail)
def detail(cycle_id: int, db: DB, user: CurrentUser):
    """Le cycle et, pour chaque membre, s'il a payé sa cotisation."""
    cycle = get_cycle(db, cycle_id)
    moi = exiger_membre(db, cycle.tontine_id, user)

    reussis = {p.membre_id: p for p in cycle.paiements if p.statut == StatutPaiement.REUSSI}
    etats = []
    for membre in cycle.tontine.membres:
        paiement = reussis.get(membre.id)
        etats.append(
            EtatMembreCycle(
                membre=MembreOut.model_validate(membre),
                a_paye=paiement is not None,
                paye_le=paiement.paye_le if paiement else None,
                methode=paiement.methode if paiement else None,
            )
        )
    return CycleDetail(
        **CycleOut.model_validate(cycle).model_dump(),
        tontine=TontineOut.model_validate(cycle.tontine),
        etats=etats,
        mon_role=moi.role if moi else None,
    )


@router.post("/{cycle_id}/paiements/especes", response_model=PaiementOut, status_code=201)
def payer_especes(cycle_id: int, data: PaiementEspeces, db: DB, user: CurrentUser):
    """Le trésorier enregistre une cotisation reçue en espèces."""
    cycle = get_cycle(db, cycle_id)
    exiger_tresorier(db, cycle.tontine_id, user)
    membre = db.get(MembreTontine, data.membre_id)
    if membre is None:
        raise NonTrouve("Membre introuvable")
    return enregistrer_especes(db, cycle, membre, par=user)


@router.post("/{cycle_id}/paiements/fedapay", response_model=PaiementFedaPayOut, status_code=201)
def payer_fedapay(
    cycle_id: int,
    db: DB,
    user: CurrentUser,
    fedapay: Annotated[FedaPayClient, Depends(get_fedapay)],
):
    """Le membre connecté paie sa cotisation : renvoie l'URL de la page de paiement FedaPay."""
    cycle = get_cycle(db, cycle_id)
    membre = adhesion(db, cycle.tontine_id, user)
    if membre is None:
        raise Interdit("Seuls les membres de la tontine peuvent cotiser")
    paiement, url = initier_paiement_fedapay(db, cycle, membre, fedapay)
    return PaiementFedaPayOut(paiement_id=paiement.id, payment_url=url)


@router.post("/{cycle_id}/cloturer", response_model=CycleOut)
def cloturer(cycle_id: int, db: DB, user: CurrentUser):
    """Le trésorier confirme avoir versé la cagnotte au bénéficiaire."""
    cycle = get_cycle(db, cycle_id)
    exiger_tresorier(db, cycle.tontine_id, user)
    return cloturer_cycle(db, cycle)
