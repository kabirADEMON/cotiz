import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import Conflit, ErreurMetier
from app.models import (
    Cycle,
    MembreTontine,
    MethodePaiement,
    Paiement,
    StatutCycle,
    StatutPaiement,
    TypeNotification,
    User,
)
from app.services.fedapay import FedaPayClient
from app.services.notifications import fcfa, notifier

logger = logging.getLogger(__name__)

STATUTS_FEDAPAY_REUSSIS = {"approved", "transferred"}
STATUTS_FEDAPAY_ECHOUES = {"declined", "canceled", "refunded"}


def _verifier_peut_payer(cycle: Cycle, membre: MembreTontine) -> None:
    if membre.tontine_id != cycle.tontine_id:
        raise ErreurMetier("Ce membre ne fait pas partie de cette tontine")
    if cycle.statut == StatutCycle.CLOS:
        raise Conflit("Ce cycle est clôturé")
    if membre.id in cycle.membres_a_jour:
        raise Conflit("Cotisation déjà réglée pour ce cycle")


def _valider(db: Session, paiement: Paiement) -> None:
    paiement.statut = StatutPaiement.REUSSI
    paiement.paye_le = datetime.now(UTC)
    tontine = paiement.cycle.tontine
    notifier(
        db,
        paiement.membre.user_id,
        TypeNotification.PAIEMENT_RECU,
        f"Paiement de {fcfa(paiement.montant)} reçu pour le cycle n°{paiement.cycle.numero} "
        f"de « {tontine.nom} ».",
        paiement.cycle_id,
    )


def enregistrer_especes(db: Session, cycle: Cycle, membre: MembreTontine, par: User) -> Paiement:
    """Le trésorier enregistre une cotisation remise en main propre."""
    _verifier_peut_payer(cycle, membre)
    paiement = Paiement(
        cycle=cycle,
        membre=membre,
        montant=cycle.tontine.montant_cotisation,
        methode=MethodePaiement.ESPECES,
        enregistre_par=par.id,
    )
    db.add(paiement)
    _valider(db, paiement)
    db.commit()
    return paiement


def initier_paiement_fedapay(
    db: Session, cycle: Cycle, membre: MembreTontine, fedapay: FedaPayClient
) -> tuple[Paiement, str]:
    """Crée un paiement en attente et la transaction FedaPay. Renvoie (paiement, URL de paiement)."""
    _verifier_peut_payer(cycle, membre)
    paiement = Paiement(
        cycle=cycle,
        membre=membre,
        montant=cycle.tontine.montant_cotisation,
        methode=MethodePaiement.FEDAPAY,
    )
    db.add(paiement)
    db.flush()  # pour obtenir paiement.id

    user = membre.user
    transaction_id, url = fedapay.creer_transaction(
        montant=paiement.montant,
        description=f"{cycle.tontine.nom} - cycle n°{cycle.numero}",
        callback_url=f"{settings.frontend_url}/paiements/{paiement.id}/retour",
        prenom=user.prenom,
        nom=user.nom,
        telephone=user.telephone,
        email=user.email,
    )
    paiement.fedapay_transaction_id = transaction_id
    db.commit()
    return paiement, url


def appliquer_statut_fedapay(db: Session, paiement: Paiement, statut_fedapay: str) -> Paiement:
    """Met à jour un paiement en attente d'après le statut FedaPay. Idempotent."""
    if paiement.statut != StatutPaiement.EN_ATTENTE:
        return paiement

    if statut_fedapay in STATUTS_FEDAPAY_REUSSIS:
        if paiement.membre_id in paiement.cycle.membres_a_jour:
            # Deux paiements lancés en parallèle : le second est à rembourser manuellement.
            logger.warning("Paiement %s en double pour le cycle %s", paiement.id, paiement.cycle_id)
            return paiement
        _valider(db, paiement)
    elif statut_fedapay in STATUTS_FEDAPAY_ECHOUES:
        paiement.statut = StatutPaiement.ECHOUE
    db.commit()
    return paiement
