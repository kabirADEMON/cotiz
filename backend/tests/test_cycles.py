from datetime import date

import pytest

from app.errors import Conflit, ErreurMetier
from app.models import (
    Frequence,
    Notification,
    StatutCycle,
    StatutTontine,
    TypeNotification,
)
from app.services.cycles import ajouter_periodes, cloturer_cycle, demarrer_tontine
from app.services.paiements import enregistrer_especes
from tests.conftest import auth, creer_user


def payer_tout_le_monde(db, cycle):
    tresorier = cycle.tontine.membres[0].user
    for membre in cycle.tontine.membres:
        enregistrer_especes(db, cycle, membre, par=tresorier)


# Calcul des échéances


@pytest.mark.parametrize(
    "frequence, n, attendu",
    [
        (Frequence.QUOTIDIENNE, 3, date(2025, 2, 3)),
        (Frequence.HEBDOMADAIRE, 2, date(2025, 2, 14)),
        (Frequence.MENSUELLE, 1, date(2025, 2, 28)),  # 31 janv. -> fin février
        (Frequence.MENSUELLE, 2, date(2025, 3, 31)),  # le jour d'origine est conservé
        (Frequence.MENSUELLE, 12, date(2026, 1, 31)),
    ],
)
def test_ajouter_periodes(frequence, n, attendu):
    assert ajouter_periodes(date(2025, 1, 31), frequence, n) == attendu


def test_ajouter_periodes_annee_bissextile():
    assert ajouter_periodes(date(2024, 1, 31), Frequence.MENSUELLE, 1) == date(2024, 2, 29)


# Démarrage


def test_demarrer_genere_un_cycle_par_membre_dans_l_ordre(db, groupe):
    cycles = demarrer_tontine(db, groupe)

    assert groupe.statut == StatutTontine.ACTIVE
    assert [c.numero for c in cycles] == [1, 2, 3]
    assert [c.beneficiaire.user.prenom for c in cycles] == ["Afi", "Bio", "Codjo"]
    assert [c.date_echeance for c in cycles] == [date(2025, 1, 31), date(2025, 2, 28), date(2025, 3, 31)]
    assert all(c.montant_attendu == 15000 for c in cycles)
    assert all(c.statut == StatutCycle.OUVERT for c in cycles)


def test_demarrer_refuse_avec_moins_de_deux_membres(db, groupe):
    groupe.membres = groupe.membres[:1]
    db.commit()
    with pytest.raises(ErreurMetier, match="au moins 2 membres"):
        demarrer_tontine(db, groupe)


def test_demarrer_refuse_une_tontine_deja_active(db, tontine_active):
    with pytest.raises(Conflit):
        demarrer_tontine(db, tontine_active)


def test_ordre_de_passage_personnalise(client, groupe):
    tresorier = groupe.membres[0].user
    ids = [m.id for m in groupe.membres]
    nouvel_ordre = [ids[2], ids[0], ids[1]]  # Codjo, Afi, Bio

    r = client.put(f"/tontines/{groupe.id}/ordre", json={"membre_ids": nouvel_ordre}, headers=auth(tresorier))
    assert r.status_code == 200
    client.post(f"/tontines/{groupe.id}/demarrer", headers=auth(tresorier))

    cycles = client.get(f"/tontines/{groupe.id}/cycles", headers=auth(tresorier)).json()
    assert [c["beneficiaire"]["user"]["prenom"] for c in cycles] == ["Codjo", "Afi", "Bio"]


def test_ordre_refuse_si_liste_incomplete(client, groupe):
    tresorier = groupe.membres[0].user
    r = client.put(
        f"/tontines/{groupe.id}/ordre",
        json={"membre_ids": [groupe.membres[0].id]},
        headers=auth(tresorier),
    )
    assert r.status_code == 400


def test_retirer_un_membre_renumerote_l_ordre(client, db, groupe):
    tresorier = groupe.membres[0].user
    bio = groupe.membres[1]

    r = client.delete(f"/tontines/{groupe.id}/membres/{bio.id}", headers=auth(tresorier))
    assert r.status_code == 204

    membres = client.get(f"/tontines/{groupe.id}", headers=auth(tresorier)).json()["membres"]
    assert [(m["user"]["prenom"], m["ordre_passage"]) for m in membres] == [("Afi", 1), ("Codjo", 2)]


def test_membres_figes_apres_demarrage(client, db, tontine_active):
    tresorier = tontine_active.membres[0].user
    creer_user(db, "+2290100000009", "Dansi")
    r = client.post(
        f"/tontines/{tontine_active.id}/membres",
        json={"telephone": "+2290100000009"},
        headers=auth(tresorier),
    )
    assert r.status_code == 409


def test_seul_le_tresorier_peut_demarrer(client, groupe):
    simple_membre = groupe.membres[1].user
    r = client.post(f"/tontines/{groupe.id}/demarrer", headers=auth(simple_membre))
    assert r.status_code == 403


# Clôture


def test_cloture_refusee_si_cotisations_manquantes(db, tontine_active):
    cycle = tontine_active.cycles[0]
    enregistrer_especes(db, cycle, tontine_active.membres[0], par=tontine_active.membres[0].user)

    with pytest.raises(ErreurMetier, match="Cotisations manquantes : Bio Dossou, Codjo Dossou"):
        cloturer_cycle(db, cycle)


def test_cloture_dans_l_ordre_des_cycles(db, tontine_active):
    deuxieme = tontine_active.cycles[1]
    payer_tout_le_monde(db, deuxieme)

    with pytest.raises(ErreurMetier, match="cycle n°1 doit être clôturé"):
        cloturer_cycle(db, deuxieme)


def test_cloture_verse_la_cagnotte_et_notifie_le_beneficiaire(db, tontine_active):
    cycle = tontine_active.cycles[0]
    payer_tout_le_monde(db, cycle)

    cloturer_cycle(db, cycle)

    assert cycle.statut == StatutCycle.CLOS
    assert cycle.verse_le is not None
    assert cycle.montant_collecte == 15000
    notification = (
        db.query(Notification).filter_by(type=TypeNotification.CAGNOTTE_VERSEE).one()
    )
    assert notification.user_id == cycle.beneficiaire.user_id
    assert "15 000 FCFA" in notification.message
    assert tontine_active.statut == StatutTontine.ACTIVE


def test_cloture_du_dernier_cycle_termine_la_tontine(db, tontine_active):
    for cycle in tontine_active.cycles:
        payer_tout_le_monde(db, cycle)
        cloturer_cycle(db, cycle)

    assert tontine_active.statut == StatutTontine.TERMINEE


def test_cloture_deux_fois_refusee(db, tontine_active):
    cycle = tontine_active.cycles[0]
    payer_tout_le_monde(db, cycle)
    cloturer_cycle(db, cycle)
    with pytest.raises(Conflit):
        cloturer_cycle(db, cycle)
