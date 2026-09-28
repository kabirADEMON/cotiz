import re
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    Frequence,
    MethodePaiement,
    RoleMembre,
    StatutCycle,
    StatutPaiement,
    StatutTontine,
    TypeNotification,
)


def _valider_telephone(valeur: str) -> str:
    # Numéro béninois : +229 suivi de 8 ou 10 chiffres (passage à 10 chiffres fin 2024).
    valeur = valeur.replace(" ", "")
    if not re.fullmatch(r"\+229\d{8}(\d{2})?", valeur):
        raise ValueError("numéro béninois attendu (+229 suivi de 8 ou 10 chiffres)")
    return valeur


Telephone = Annotated[str, AfterValidator(_valider_telephone), Field(examples=["+2290197000000"])]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Auth / utilisateurs


class UserCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    telephone: Telephone
    email: EmailStr | None = None
    password: str = Field(min_length=8)


class UserOut(Schema):
    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    is_admin: bool
    is_active: bool
    created_at: datetime


class UserAdminUpdate(BaseModel):
    is_admin: bool | None = None
    is_active: bool | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Tontines


class TontineCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    montant_cotisation: int = Field(gt=0, description="Montant en FCFA")
    frequence: Frequence
    date_debut: date


class MembreAjout(BaseModel):
    telephone: Telephone
    role: RoleMembre = RoleMembre.MEMBRE


class OrdrePassage(BaseModel):
    membre_ids: list[int] = Field(description="Ids des membres, dans l'ordre de passage souhaité")


class MembreOut(Schema):
    id: int
    user_id: int
    role: RoleMembre
    ordre_passage: int
    user: UserOut


class TontineOut(Schema):
    id: int
    nom: str
    montant_cotisation: int
    frequence: Frequence
    date_debut: date
    statut: StatutTontine
    created_at: datetime
    nb_membres: int
    prochaine_echeance: date | None


class TontineDetail(TontineOut):
    membres: list[MembreOut]
    mon_role: RoleMembre | None = None


# Cycles et paiements


class CycleOut(Schema):
    id: int
    numero: int
    date_echeance: date
    statut: StatutCycle
    montant_attendu: int
    montant_collecte: int
    verse_le: datetime | None
    beneficiaire: MembreOut


class EtatMembreCycle(BaseModel):
    membre: MembreOut
    a_paye: bool
    paye_le: datetime | None = None
    methode: MethodePaiement | None = None


class CycleDetail(CycleOut):
    tontine: TontineOut
    etats: list[EtatMembreCycle]
    mon_role: RoleMembre | None = None


class PaiementEspeces(BaseModel):
    membre_id: int


class PaiementOut(Schema):
    id: int
    cycle_id: int
    membre_id: int
    montant: int
    methode: MethodePaiement
    statut: StatutPaiement
    created_at: datetime
    paye_le: datetime | None


class PaiementHistorique(PaiementOut):
    tontine_id: int
    tontine_nom: str
    cycle_numero: int


class PaiementFedaPayOut(BaseModel):
    paiement_id: int
    payment_url: str


# Notifications


class NotificationOut(Schema):
    id: int
    type: TypeNotification
    message: str
    lu: bool
    cycle_id: int | None
    created_at: datetime
