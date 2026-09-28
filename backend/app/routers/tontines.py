from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import DB, CurrentUser, adhesion, exiger_membre, exiger_tresorier, get_tontine
from app.errors import Conflit, ErreurMetier, NonTrouve
from app.models import (
    Cycle,
    MembreTontine,
    Paiement,
    RoleMembre,
    StatutTontine,
    Tontine,
    User,
)
from app.routers.paiements import vers_historique
from app.schemas import (
    CycleOut,
    MembreAjout,
    MembreOut,
    OrdrePassage,
    PaiementHistorique,
    TontineCreate,
    TontineDetail,
    TontineOut,
)
from app.services.cycles import demarrer_tontine

router = APIRouter(prefix="/tontines", tags=["Tontines"])


def _detail(tontine: Tontine, membre: MembreTontine | None) -> TontineDetail:
    detail = TontineDetail.model_validate(tontine)
    detail.mon_role = membre.role if membre else None
    return detail


def _exiger_brouillon(tontine: Tontine) -> None:
    if tontine.statut != StatutTontine.BROUILLON:
        raise Conflit("Les membres ne peuvent plus être modifiés après le démarrage")


def _renumeroter(db: Session, membres: list[MembreTontine]) -> None:
    """Réattribue les ordres 1..n sans violer la contrainte d'unicité (passage par des négatifs)."""
    for i, membre in enumerate(membres):
        membre.ordre_passage = -(i + 1)
    db.flush()
    for membre in membres:
        membre.ordre_passage = -membre.ordre_passage
    db.flush()


@router.post("", response_model=TontineDetail, status_code=201)
def creer(data: TontineCreate, db: DB, user: CurrentUser):
    """Crée une tontine. Son créateur en devient le trésorier et le premier bénéficiaire."""
    tontine = Tontine(**data.model_dump(), created_by=user.id)
    createur = MembreTontine(user=user, role=RoleMembre.TRESORIER, ordre_passage=1)
    tontine.membres.append(createur)
    db.add(tontine)
    db.commit()
    return _detail(tontine, createur)


@router.get("", response_model=list[TontineOut])
def lister(db: DB, user: CurrentUser):
    """Les tontines de l'utilisateur (toutes pour un admin)."""
    requete = select(Tontine).order_by(Tontine.created_at.desc(), Tontine.id.desc())
    if not user.is_admin:
        requete = requete.join(MembreTontine).where(MembreTontine.user_id == user.id)
    return db.scalars(requete).all()


@router.get("/{tontine_id}", response_model=TontineDetail)
def detail(tontine_id: int, db: DB, user: CurrentUser):
    tontine = get_tontine(db, tontine_id)
    membre = exiger_membre(db, tontine_id, user)
    return _detail(tontine, membre)


@router.post("/{tontine_id}/membres", response_model=MembreOut, status_code=201)
def ajouter_membre(tontine_id: int, data: MembreAjout, db: DB, user: CurrentUser):
    tontine = get_tontine(db, tontine_id)
    exiger_tresorier(db, tontine_id, user)
    _exiger_brouillon(tontine)

    nouveau = db.scalar(select(User).where(User.telephone == data.telephone))
    if nouveau is None:
        raise NonTrouve("Aucun compte avec ce numéro : la personne doit d'abord s'inscrire")
    if adhesion(db, tontine_id, nouveau):
        raise Conflit("Cette personne fait déjà partie de la tontine")

    ordre = max((m.ordre_passage for m in tontine.membres), default=0) + 1
    membre = MembreTontine(user=nouveau, role=data.role, ordre_passage=ordre)
    tontine.membres.append(membre)
    db.commit()
    return membre


@router.delete("/{tontine_id}/membres/{membre_id}", status_code=204)
def retirer_membre(tontine_id: int, membre_id: int, db: DB, user: CurrentUser):
    tontine = get_tontine(db, tontine_id)
    exiger_tresorier(db, tontine_id, user)
    _exiger_brouillon(tontine)

    membre = next((m for m in tontine.membres if m.id == membre_id), None)
    if membre is None:
        raise NonTrouve("Membre introuvable dans cette tontine")
    tresoriers = [m for m in tontine.membres if m.role == RoleMembre.TRESORIER]
    if tresoriers == [membre]:
        raise ErreurMetier("Impossible de retirer le dernier trésorier")

    tontine.membres.remove(membre)
    db.flush()
    _renumeroter(db, sorted(tontine.membres, key=lambda m: m.ordre_passage))
    db.commit()


@router.put("/{tontine_id}/ordre", response_model=list[MembreOut])
def definir_ordre(tontine_id: int, data: OrdrePassage, db: DB, user: CurrentUser):
    """Définit l'ordre de passage : le 1er de la liste reçoit la cagnotte du cycle 1, etc."""
    tontine = get_tontine(db, tontine_id)
    exiger_tresorier(db, tontine_id, user)
    _exiger_brouillon(tontine)

    par_id = {m.id: m for m in tontine.membres}
    if sorted(data.membre_ids) != sorted(par_id):
        raise ErreurMetier("La liste doit contenir chaque membre de la tontine exactement une fois")
    _renumeroter(db, [par_id[i] for i in data.membre_ids])
    db.commit()
    db.refresh(tontine)
    return tontine.membres


@router.post("/{tontine_id}/demarrer", response_model=TontineDetail)
def demarrer(tontine_id: int, db: DB, user: CurrentUser):
    """Fige les membres et génère le calendrier des cycles."""
    tontine = get_tontine(db, tontine_id)
    exiger_tresorier(db, tontine_id, user)
    demarrer_tontine(db, tontine)
    return _detail(tontine, adhesion(db, tontine_id, user))


@router.get("/{tontine_id}/cycles", response_model=list[CycleOut])
def lister_cycles(tontine_id: int, db: DB, user: CurrentUser):
    tontine = get_tontine(db, tontine_id)
    exiger_membre(db, tontine_id, user)
    return tontine.cycles


@router.get("/{tontine_id}/paiements", response_model=list[PaiementHistorique])
def historique(tontine_id: int, db: DB, user: CurrentUser, membre_id: int | None = None):
    """Historique des paiements de la tontine, filtrable par membre."""
    get_tontine(db, tontine_id)
    exiger_membre(db, tontine_id, user)
    requete = (
        select(Paiement)
        .join(Cycle)
        .where(Cycle.tontine_id == tontine_id)
        .order_by(Cycle.numero, Paiement.created_at)
    )
    if membre_id is not None:
        requete = requete.where(Paiement.membre_id == membre_id)
    return [vers_historique(p) for p in db.scalars(requete)]
