import calendar
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.errors import Conflit, ErreurMetier
from app.models import Cycle, Frequence, StatutCycle, StatutTontine, Tontine, TypeNotification
from app.services.notifications import fcfa, notifier


def ajouter_periodes(debut: date, frequence: Frequence, n: int) -> date:
    """Date située `n` périodes après `debut`.

    En mensuel, le jour est ramené à la fin du mois si besoin (31 janv. + 1 mois = 28/29 févr.).
    """
    if frequence == Frequence.QUOTIDIENNE:
        return debut + timedelta(days=n)
    if frequence == Frequence.HEBDOMADAIRE:
        return debut + timedelta(weeks=n)
    mois = debut.month - 1 + n
    annee = debut.year + mois // 12
    mois = mois % 12 + 1
    jour = min(debut.day, calendar.monthrange(annee, mois)[1])
    return date(annee, mois, jour)


def demarrer_tontine(db: Session, tontine: Tontine) -> list[Cycle]:
    """Fige la liste des membres et génère un cycle par membre, dans l'ordre de passage."""
    if tontine.statut != StatutTontine.BROUILLON:
        raise Conflit("La tontine a déjà démarré")
    membres = sorted(tontine.membres, key=lambda m: m.ordre_passage)
    if len(membres) < 2:
        raise ErreurMetier("Il faut au moins 2 membres pour démarrer une tontine")

    cagnotte = tontine.montant_cotisation * len(membres)
    for i, membre in enumerate(membres):
        tontine.cycles.append(
            Cycle(
                numero=i + 1,
                date_echeance=ajouter_periodes(tontine.date_debut, tontine.frequence, i),
                beneficiaire=membre,
                montant_attendu=cagnotte,
            )
        )
    tontine.statut = StatutTontine.ACTIVE
    db.commit()
    return tontine.cycles


def cycle_courant(tontine: Tontine) -> Cycle | None:
    """Premier cycle non clôturé : c'est celui dont la cagnotte sera versée en prochain."""
    return next((c for c in tontine.cycles if c.statut == StatutCycle.OUVERT), None)


def cloturer_cycle(db: Session, cycle: Cycle) -> Cycle:
    """Marque la cagnotte comme versée au bénéficiaire. Exige que tous les membres aient payé."""
    tontine = cycle.tontine
    if cycle.statut == StatutCycle.CLOS:
        raise Conflit("Ce cycle est déjà clôturé")

    courant = cycle_courant(tontine)
    if courant is not None and courant.id != cycle.id:
        raise ErreurMetier(f"Le cycle n°{courant.numero} doit être clôturé avant celui-ci")

    a_jour = cycle.membres_a_jour
    manquants = [m.user.nom_complet for m in tontine.membres if m.id not in a_jour]
    if manquants:
        raise ErreurMetier("Cotisations manquantes : " + ", ".join(manquants))

    cycle.statut = StatutCycle.CLOS
    cycle.verse_le = datetime.now(UTC)
    notifier(
        db,
        cycle.beneficiaire.user_id,
        TypeNotification.CAGNOTTE_VERSEE,
        f"La cagnotte de {fcfa(cycle.montant_collecte)} du cycle n°{cycle.numero} "
        f"de « {tontine.nom} » vous a été versée.",
        cycle.id,
    )
    if all(c.statut == StatutCycle.CLOS for c in tontine.cycles):
        tontine.statut = StatutTontine.TERMINEE
    db.commit()
    return cycle
