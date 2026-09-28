from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Cycle,
    Notification,
    StatutCycle,
    StatutTontine,
    Tontine,
    TypeNotification,
)


def fcfa(montant: int) -> str:
    return f"{montant:,}".replace(",", " ") + " FCFA"


def notifier(
    db: Session, user_id: int, type: TypeNotification, message: str, cycle_id: int | None = None
) -> Notification:
    """Ajoute une notification à la session (le commit est fait par l'appelant)."""
    notification = Notification(user_id=user_id, type=type, message=message, cycle_id=cycle_id)
    db.add(notification)
    return notification


def envoyer_rappels(db: Session, aujourdhui: date, jours_avant: int = 2) -> int:
    """Rappelle leur cotisation aux membres en retard ou dont l'échéance approche.

    Un seul rappel par membre et par cycle. Renvoie le nombre de rappels créés.
    """
    cycles = db.scalars(
        select(Cycle)
        .join(Tontine)
        .where(
            Tontine.statut == StatutTontine.ACTIVE,
            Cycle.statut == StatutCycle.OUVERT,
            Cycle.date_echeance <= aujourdhui + timedelta(days=jours_avant),
        )
    ).all()

    total = 0
    for cycle in cycles:
        deja_rappeles = set(
            db.scalars(
                select(Notification.user_id).where(
                    Notification.cycle_id == cycle.id,
                    Notification.type == TypeNotification.RAPPEL_COTISATION,
                )
            )
        )
        a_jour = cycle.membres_a_jour
        tontine = cycle.tontine
        for membre in tontine.membres:
            if membre.id in a_jour or membre.user_id in deja_rappeles:
                continue
            if cycle.date_echeance < aujourdhui:
                quand = f"était due le {cycle.date_echeance:%d/%m/%Y}"
            else:
                quand = f"est due le {cycle.date_echeance:%d/%m/%Y}"
            notifier(
                db,
                membre.user_id,
                TypeNotification.RAPPEL_COTISATION,
                f"Votre cotisation de {fcfa(tontine.montant_cotisation)} pour « {tontine.nom} » "
                f"(cycle n°{cycle.numero}) {quand}.",
                cycle.id,
            )
            total += 1

    db.commit()
    return total
