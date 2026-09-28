from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select

from app.deps import DB, CurrentUser
from app.errors import Conflit, Interdit
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: DB):
    """Crée un compte. Le tout premier compte de la plateforme devient administrateur."""
    if db.scalar(select(User).where(User.telephone == data.telephone)):
        raise Conflit("Ce numéro de téléphone est déjà utilisé")
    if data.email and db.scalar(select(User).where(User.email == data.email)):
        raise Conflit("Cet email est déjà utilisé")

    premier_compte = db.scalar(select(func.count(User.id))) == 0
    user = User(
        **data.model_dump(exclude={"password"}),
        password_hash=hash_password(data.password),
        is_admin=premier_compte,
    )
    db.add(user)
    db.commit()
    return user


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    """Connexion avec le numéro de téléphone (champ `username`) et le mot de passe."""
    user = db.scalar(select(User).where(User.telephone == form.username))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Téléphone ou mot de passe incorrect")
    if not user.is_active:
        raise Interdit("Ce compte est désactivé")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
