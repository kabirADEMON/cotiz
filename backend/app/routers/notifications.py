from fastapi import APIRouter
from sqlalchemy import select, update

from app.deps import DB, CurrentUser
from app.errors import NonTrouve
from app.models import Notification
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationOut])
def lister(db: DB, user: CurrentUser, non_lues: bool = False):
    requete = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(100)
    )
    if non_lues:
        requete = requete.where(Notification.lu.is_(False))
    return db.scalars(requete).all()


@router.post("/{notification_id}/lu", response_model=NotificationOut)
def marquer_lue(notification_id: int, db: DB, user: CurrentUser):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise NonTrouve("Notification introuvable")
    notification.lu = True
    db.commit()
    return notification


@router.post("/tout-lu", status_code=204)
def tout_marquer_lu(db: DB, user: CurrentUser):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(lu=True))
    db.commit()
