from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Frequence(StrEnum):
    QUOTIDIENNE = "quotidienne"
    HEBDOMADAIRE = "hebdomadaire"
    MENSUELLE = "mensuelle"


class StatutTontine(StrEnum):
    BROUILLON = "brouillon"
    ACTIVE = "active"
    TERMINEE = "terminee"


class RoleMembre(StrEnum):
    TRESORIER = "tresorier"
    MEMBRE = "membre"


class StatutCycle(StrEnum):
    OUVERT = "ouvert"
    CLOS = "clos"


class MethodePaiement(StrEnum):
    FEDAPAY = "fedapay"
    ESPECES = "especes"


class StatutPaiement(StrEnum):
    EN_ATTENTE = "en_attente"
    REUSSI = "reussi"
    ECHOUE = "echoue"


class TypeNotification(StrEnum):
    RAPPEL_COTISATION = "rappel_cotisation"
    PAIEMENT_RECU = "paiement_recu"
    CAGNOTTE_VERSEE = "cagnotte_versee"


def _enum(cls: type[StrEnum]) -> Enum:
    """Stocke la valeur ('mensuelle') plutôt que le nom Python ('MENSUELLE')."""
    return Enum(cls, name=cls.__name__.lower(), values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    telephone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    adhesions: Mapped[list["MembreTontine"]] = relationship(back_populates="user")

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom}"


class Tontine(Base):
    __tablename__ = "tontines"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(150))
    montant_cotisation: Mapped[int] = mapped_column(Integer)  # en FCFA
    frequence: Mapped[Frequence] = mapped_column(_enum(Frequence))
    date_debut: Mapped[date] = mapped_column(Date)
    statut: Mapped[StatutTontine] = mapped_column(
        _enum(StatutTontine), default=StatutTontine.BROUILLON
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    membres: Mapped[list["MembreTontine"]] = relationship(
        back_populates="tontine", order_by="MembreTontine.ordre_passage", cascade="all, delete-orphan"
    )
    cycles: Mapped[list["Cycle"]] = relationship(
        back_populates="tontine", order_by="Cycle.numero", cascade="all, delete-orphan"
    )

    @property
    def nb_membres(self) -> int:
        return len(self.membres)

    @property
    def prochaine_echeance(self) -> date | None:
        return next((c.date_echeance for c in self.cycles if c.statut == StatutCycle.OUVERT), None)


class MembreTontine(Base):
    __tablename__ = "membres_tontine"
    __table_args__ = (
        UniqueConstraint("tontine_id", "user_id"),
        UniqueConstraint("tontine_id", "ordre_passage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tontine_id: Mapped[int] = mapped_column(ForeignKey("tontines.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[RoleMembre] = mapped_column(_enum(RoleMembre), default=RoleMembre.MEMBRE)
    ordre_passage: Mapped[int] = mapped_column(Integer)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tontine: Mapped[Tontine] = relationship(back_populates="membres")
    user: Mapped[User] = relationship(back_populates="adhesions")


class Cycle(Base):
    """Une échéance : chaque membre cotise, un bénéficiaire reçoit la cagnotte."""

    __tablename__ = "cycles"
    __table_args__ = (UniqueConstraint("tontine_id", "numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tontine_id: Mapped[int] = mapped_column(ForeignKey("tontines.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(Integer)
    date_echeance: Mapped[date] = mapped_column(Date)
    beneficiaire_id: Mapped[int] = mapped_column(ForeignKey("membres_tontine.id"))
    statut: Mapped[StatutCycle] = mapped_column(_enum(StatutCycle), default=StatutCycle.OUVERT)
    montant_attendu: Mapped[int] = mapped_column(Integer)
    verse_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tontine: Mapped[Tontine] = relationship(back_populates="cycles")
    beneficiaire: Mapped[MembreTontine] = relationship()
    paiements: Mapped[list["Paiement"]] = relationship(back_populates="cycle")

    @property
    def membres_a_jour(self) -> set[int]:
        """Ids des membres (MembreTontine) ayant réglé leur cotisation pour ce cycle."""
        return {p.membre_id for p in self.paiements if p.statut == StatutPaiement.REUSSI}

    @property
    def montant_collecte(self) -> int:
        return sum(p.montant for p in self.paiements if p.statut == StatutPaiement.REUSSI)


class Paiement(Base):
    __tablename__ = "paiements"
    __table_args__ = (
        # Un seul paiement réussi par membre et par cycle ; les tentatives échouées restent en historique.
        Index(
            "uq_paiement_reussi",
            "cycle_id",
            "membre_id",
            unique=True,
            postgresql_where=text("statut = 'reussi'"),
            sqlite_where=text("statut = 'reussi'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id"))
    membre_id: Mapped[int] = mapped_column(ForeignKey("membres_tontine.id"))
    montant: Mapped[int] = mapped_column(Integer)
    methode: Mapped[MethodePaiement] = mapped_column(_enum(MethodePaiement))
    statut: Mapped[StatutPaiement] = mapped_column(
        _enum(StatutPaiement), default=StatutPaiement.EN_ATTENTE
    )
    fedapay_transaction_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    enregistre_par: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paye_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cycle: Mapped[Cycle] = relationship(back_populates="paiements")
    membre: Mapped[MembreTontine] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("cycles.id"))
    type: Mapped[TypeNotification] = mapped_column(_enum(TypeNotification))
    message: Mapped[str] = mapped_column(Text)
    lu: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
