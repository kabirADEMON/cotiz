from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import Interdit, NonTrouve
from app.models import Cycle, MembreTontine, RoleMembre, Tontine, User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DB = Annotated[Session, Depends(get_db)]


def get_current_user(db: DB, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    user_id = decode_access_token(token)
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise Interdit("Réservé aux administrateurs")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


# Contrôles d'accès au niveau d'une tontine


def get_tontine(db: Session, tontine_id: int) -> Tontine:
    tontine = db.get(Tontine, tontine_id)
    if tontine is None:
        raise NonTrouve("Tontine introuvable")
    return tontine


def get_cycle(db: Session, cycle_id: int) -> Cycle:
    cycle = db.get(Cycle, cycle_id)
    if cycle is None:
        raise NonTrouve("Cycle introuvable")
    return cycle


def adhesion(db: Session, tontine_id: int, user: User) -> MembreTontine | None:
    return db.scalar(
        select(MembreTontine).where(
            MembreTontine.tontine_id == tontine_id, MembreTontine.user_id == user.id
        )
    )


def exiger_membre(db: Session, tontine_id: int, user: User) -> MembreTontine | None:
    """Membre du groupe (ou admin, qui voit tout). Renvoie l'adhésion si elle existe."""
    membre = adhesion(db, tontine_id, user)
    if membre is None and not user.is_admin:
        raise Interdit("Vous ne faites pas partie de cette tontine")
    return membre


def exiger_tresorier(db: Session, tontine_id: int, user: User) -> None:
    membre = adhesion(db, tontine_id, user)
    if user.is_admin or (membre and membre.role == RoleMembre.TRESORIER):
        return
    raise Interdit("Réservé au trésorier de la tontine")
