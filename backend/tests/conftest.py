"""Fixtures de test.

Par défaut les tests tournent sur SQLite en mémoire (aucune installation requise).
Pour les lancer sur PostgreSQL : TEST_DATABASE_URL=postgresql+psycopg://... pytest
"""

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Frequence, MembreTontine, RoleMembre, Tontine, User
from app.security import create_access_token, hash_password
from app.services.cycles import demarrer_tontine
from app.services.fedapay import get_fedapay

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")

if TEST_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
else:
    engine = create_engine(TEST_DATABASE_URL)

TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class FakeFedaPay:
    """Remplace l'API FedaPay : aucune requête réseau pendant les tests."""

    def __init__(self):
        self.statuts: dict[str, str] = {}
        self.transactions: list[dict] = []

    def creer_transaction(self, montant, description, callback_url, **client):
        transaction_id = str(1000 + len(self.transactions))
        self.transactions.append({"id": transaction_id, "montant": montant, **client})
        self.statuts[transaction_id] = "pending"
        return transaction_id, f"https://sandbox-checkout.fedapay.com/{transaction_id}"

    def statut_transaction(self, transaction_id):
        return self.statuts[transaction_id]


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def fedapay():
    return FakeFedaPay()


@pytest.fixture
def client(db, fedapay):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_fedapay] = lambda: fedapay
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def creer_user(db, telephone: str, prenom: str = "Test", is_admin: bool = False) -> User:
    user = User(
        nom="Dossou",
        prenom=prenom,
        telephone=telephone,
        password_hash=hash_password("motdepasse"),
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    return user


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def groupe(db):
    """Tontine en brouillon : un trésorier (Afi) et deux membres (Bio, Codjo), 5 000 FCFA/mois."""
    tresorier = creer_user(db, "+2290100000001", "Afi")
    bio = creer_user(db, "+2290100000002", "Bio")
    codjo = creer_user(db, "+2290100000003", "Codjo")
    tontine = Tontine(
        nom="Tontine du marché",
        montant_cotisation=5000,
        frequence=Frequence.MENSUELLE,
        date_debut=date(2025, 1, 31),
        created_by=tresorier.id,
    )
    for i, (user, role) in enumerate(
        [(tresorier, RoleMembre.TRESORIER), (bio, RoleMembre.MEMBRE), (codjo, RoleMembre.MEMBRE)]
    ):
        tontine.membres.append(MembreTontine(user=user, role=role, ordre_passage=i + 1))
    db.add(tontine)
    db.commit()
    return tontine


@pytest.fixture
def tontine_active(db, groupe):
    demarrer_tontine(db, groupe)
    return groupe
