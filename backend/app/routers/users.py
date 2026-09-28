from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, AdminUser
from app.errors import ErreurMetier, NonTrouve
from app.models import User
from app.schemas import UserAdminUpdate, UserOut

router = APIRouter(prefix="/users", tags=["Administration"])


@router.get("", response_model=list[UserOut])
def lister(db: DB, _: AdminUser):
    return db.scalars(select(User).order_by(User.nom, User.prenom)).all()


@router.patch("/{user_id}", response_model=UserOut)
def modifier(user_id: int, data: UserAdminUpdate, db: DB, admin: AdminUser):
    user = db.get(User, user_id)
    if user is None:
        raise NonTrouve("Utilisateur introuvable")
    if user.id == admin.id:
        raise ErreurMetier("Vous ne pouvez pas modifier votre propre compte")
    for champ, valeur in data.model_dump(exclude_none=True).items():
        setattr(user, champ, valeur)
    db.commit()
    return user
