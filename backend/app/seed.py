"""Remplit la base avec des données de démonstration.

    python -m app.seed

Tous les comptes ont le mot de passe `demo1234`.
"""

from datetime import date, timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Frequence, MembreTontine, RoleMembre, Tontine, User
from app.security import hash_password
from app.services.cycles import cloturer_cycle, demarrer_tontine
from app.services.notifications import envoyer_rappels
from app.services.paiements import enregistrer_especes

COMPTES = [
    # (prénom, nom, téléphone, admin)
    ("Admin", "Plateforme", "+2290100000000", True),
    ("Afi", "Houngbédji", "+2290197000001", False),
    ("Bio", "Guéra", "+2290197000002", False),
    ("Codjo", "Adjovi", "+2290197000003", False),
    ("Dansi", "Kpossou", "+2290197000004", False),
    ("Essé", "Tossou", "+2290197000005", False),
]


def main() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count(User.id))):
            print("La base contient déjà des utilisateurs : rien à faire.")
            return

        users = []
        for prenom, nom, telephone, admin in COMPTES:
            user = User(
                prenom=prenom,
                nom=nom,
                telephone=telephone,
                password_hash=hash_password("demo1234"),
                is_admin=admin,
            )
            db.add(user)
            users.append(user)
        db.flush()
        afi, bio, codjo, dansi, esse = users[1:]

        # Tontine mensuelle en cours : le 1er cycle est versé, le 2e partiellement payé.
        marche = Tontine(
            nom="Tontine des commerçantes de Dantokpa",
            montant_cotisation=10_000,
            frequence=Frequence.MENSUELLE,
            date_debut=date.today().replace(day=1) - timedelta(days=31),
            created_by=afi.id,
        )
        for i, user in enumerate([afi, bio, codjo, dansi]):
            role = RoleMembre.TRESORIER if user is afi else RoleMembre.MEMBRE
            marche.membres.append(MembreTontine(user=user, role=role, ordre_passage=i + 1))
        db.add(marche)
        db.commit()
        demarrer_tontine(db, marche)

        premier, second = marche.cycles[0], marche.cycles[1]
        for membre in marche.membres:
            enregistrer_especes(db, premier, membre, par=afi)
        cloturer_cycle(db, premier)
        for membre in marche.membres[:2]:
            enregistrer_especes(db, second, membre, par=afi)

        # Tontine hebdomadaire encore en préparation.
        amis = Tontine(
            nom="Épargne entre amis",
            montant_cotisation=2_500,
            frequence=Frequence.HEBDOMADAIRE,
            date_debut=date.today() + timedelta(days=7),
            created_by=bio.id,
        )
        amis.membres.append(MembreTontine(user=bio, role=RoleMembre.TRESORIER, ordre_passage=1))
        amis.membres.append(MembreTontine(user=esse, role=RoleMembre.MEMBRE, ordre_passage=2))
        db.add(amis)
        db.commit()

        envoyer_rappels(db, date.today(), jours_avant=31)

    print("Données de démo créées. Comptes (mot de passe : demo1234) :")
    for prenom, nom, telephone, admin in COMPTES:
        print(f"  {telephone}  {prenom} {nom}{'  (admin)' if admin else ''}")


if __name__ == "__main__":
    main()
