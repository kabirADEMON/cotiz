import hashlib
import hmac
import json
import time
from datetime import date

import pytest

from app.config import settings
from app.errors import Conflit
from app.models import (
    MethodePaiement,
    Notification,
    Paiement,
    StatutCycle,
    StatutPaiement,
    TypeNotification,
)
from app.services.notifications import envoyer_rappels
from app.services.paiements import enregistrer_especes
from tests.conftest import auth, creer_user

WEBHOOK_SECRET = "wh_sandbox_test"


@pytest.fixture(autouse=True)
def secret_webhook(monkeypatch):
    monkeypatch.setattr(settings, "fedapay_webhook_secret", WEBHOOK_SECRET)


def envoyer_webhook(client, transaction_id: str, secret: str = WEBHOOK_SECRET):
    payload = json.dumps({"name": "transaction.approved", "entity": {"id": int(transaction_id)}}).encode()
    t = str(int(time.time()))
    signature = hmac.new(secret.encode(), t.encode() + b"." + payload, hashlib.sha256).hexdigest()
    return client.post(
        "/webhooks/fedapay",
        content=payload,
        headers={"X-FEDAPAY-SIGNATURE": f"t={t},s={signature}", "Content-Type": "application/json"},
    )


# Espèces


def test_tresorier_enregistre_un_paiement_especes(client, db, tontine_active):
    tresorier, bio = tontine_active.membres[0], tontine_active.membres[1]
    cycle = tontine_active.cycles[0]

    r = client.post(
        f"/cycles/{cycle.id}/paiements/especes", json={"membre_id": bio.id}, headers=auth(tresorier.user)
    )

    assert r.status_code == 201
    assert r.json()["statut"] == "reussi"
    assert r.json()["montant"] == 5000
    notif = db.query(Notification).filter_by(user_id=bio.user_id).one()
    assert notif.type == TypeNotification.PAIEMENT_RECU

    detail = client.get(f"/cycles/{cycle.id}", headers=auth(bio.user)).json()
    assert {e["membre"]["user"]["prenom"]: e["a_paye"] for e in detail["etats"]} == {
        "Afi": False,
        "Bio": True,
        "Codjo": False,
    }


def test_double_paiement_refuse(db, tontine_active):
    tresorier, bio = tontine_active.membres[0], tontine_active.membres[1]
    cycle = tontine_active.cycles[0]
    enregistrer_especes(db, cycle, bio, par=tresorier.user)

    with pytest.raises(Conflit, match="déjà réglée"):
        enregistrer_especes(db, cycle, bio, par=tresorier.user)


def test_simple_membre_ne_peut_pas_enregistrer_d_especes(client, tontine_active):
    bio = tontine_active.membres[1]
    r = client.post(
        f"/cycles/{tontine_active.cycles[0].id}/paiements/especes",
        json={"membre_id": bio.id},
        headers=auth(bio.user),
    )
    assert r.status_code == 403


def test_membre_d_une_autre_tontine_refuse(db, tontine_active, groupe):
    from app.models import Frequence, MembreTontine, RoleMembre, Tontine

    etranger = creer_user(db, "+2290100000099", "Étranger")
    autre = Tontine(
        nom="Autre", montant_cotisation=1000, frequence=Frequence.HEBDOMADAIRE,
        date_debut=date(2025, 1, 1), created_by=etranger.id,
    )
    membre_autre = MembreTontine(user=etranger, role=RoleMembre.TRESORIER, ordre_passage=1)
    autre.membres.append(membre_autre)
    db.add(autre)
    db.commit()

    with pytest.raises(Exception, match="ne fait pas partie"):
        enregistrer_especes(db, tontine_active.cycles[0], membre_autre, par=etranger)


def test_non_membre_ne_voit_pas_le_cycle(client, db, tontine_active):
    etranger = creer_user(db, "+2290100000099", "Étranger")
    r = client.get(f"/cycles/{tontine_active.cycles[0].id}", headers=auth(etranger))
    assert r.status_code == 403


def test_paiement_refuse_sur_cycle_clos(db, tontine_active):
    from app.services.cycles import cloturer_cycle

    cycle = tontine_active.cycles[0]
    tresorier = tontine_active.membres[0].user
    for membre in tontine_active.membres:
        enregistrer_especes(db, cycle, membre, par=tresorier)
    cloturer_cycle(db, cycle)
    assert cycle.statut == StatutCycle.CLOS

    with pytest.raises(Conflit, match="clôturé"):
        enregistrer_especes(db, cycle, tontine_active.membres[1], par=tresorier)


# FedaPay


def test_initier_paiement_fedapay(client, db, fedapay, tontine_active):
    bio = tontine_active.membres[1]
    cycle = tontine_active.cycles[0]

    r = client.post(f"/cycles/{cycle.id}/paiements/fedapay", headers=auth(bio.user))

    assert r.status_code == 201
    assert r.json()["payment_url"].startswith("https://sandbox-checkout.fedapay.com/")
    paiement = db.get(Paiement, r.json()["paiement_id"])
    assert paiement.statut == StatutPaiement.EN_ATTENTE
    assert paiement.methode == MethodePaiement.FEDAPAY
    assert fedapay.transactions[0]["montant"] == 5000
    assert fedapay.transactions[0]["telephone"] == bio.user.telephone


def test_webhook_valide_confirme_le_paiement(client, db, fedapay, tontine_active):
    bio = tontine_active.membres[1]
    cycle = tontine_active.cycles[0]
    paiement_id = client.post(f"/cycles/{cycle.id}/paiements/fedapay", headers=auth(bio.user)).json()["paiement_id"]
    paiement = db.get(Paiement, paiement_id)

    fedapay.statuts[paiement.fedapay_transaction_id] = "approved"
    r = envoyer_webhook(client, paiement.fedapay_transaction_id)

    assert r.status_code == 200
    db.refresh(paiement)
    assert paiement.statut == StatutPaiement.REUSSI
    assert paiement.paye_le is not None
    assert bio.id in cycle.membres_a_jour

    # Un webhook rejoué ne crée pas de seconde notification.
    envoyer_webhook(client, paiement.fedapay_transaction_id)
    assert db.query(Notification).filter_by(type=TypeNotification.PAIEMENT_RECU).count() == 1


def test_webhook_signature_invalide_rejete(client, db, fedapay, tontine_active):
    bio = tontine_active.membres[1]
    paiement_id = client.post(
        f"/cycles/{tontine_active.cycles[0].id}/paiements/fedapay", headers=auth(bio.user)
    ).json()["paiement_id"]
    paiement = db.get(Paiement, paiement_id)
    fedapay.statuts[paiement.fedapay_transaction_id] = "approved"

    r = envoyer_webhook(client, paiement.fedapay_transaction_id, secret="mauvais-secret")

    assert r.status_code == 400
    db.refresh(paiement)
    assert paiement.statut == StatutPaiement.EN_ATTENTE


def test_paiement_refuse_puis_nouvelle_tentative(client, db, fedapay, tontine_active):
    bio = tontine_active.membres[1]
    cycle = tontine_active.cycles[0]
    premier = client.post(f"/cycles/{cycle.id}/paiements/fedapay", headers=auth(bio.user)).json()
    transaction_id = db.get(Paiement, premier["paiement_id"]).fedapay_transaction_id

    fedapay.statuts[transaction_id] = "declined"
    r = client.post(f"/paiements/{premier['paiement_id']}/verifier", headers=auth(bio.user))
    assert r.json()["statut"] == "echoue"

    second = client.post(f"/cycles/{cycle.id}/paiements/fedapay", headers=auth(bio.user))
    assert second.status_code == 201

    historique = client.get("/paiements/me", headers=auth(bio.user)).json()
    assert [p["statut"] for p in historique] == ["en_attente", "echoue"]


def test_verifier_le_paiement_d_un_autre_membre_interdit(client, db, fedapay, tontine_active):
    bio, codjo = tontine_active.membres[1], tontine_active.membres[2]
    paiement_id = client.post(
        f"/cycles/{tontine_active.cycles[0].id}/paiements/fedapay", headers=auth(bio.user)
    ).json()["paiement_id"]

    r = client.post(f"/paiements/{paiement_id}/verifier", headers=auth(codjo.user))
    assert r.status_code == 403


# Historique et rappels


def test_historique_par_membre(client, db, tontine_active):
    tresorier, bio = tontine_active.membres[0], tontine_active.membres[1]
    for cycle in tontine_active.cycles[:2]:
        enregistrer_especes(db, cycle, bio, par=tresorier.user)
    enregistrer_especes(db, tontine_active.cycles[0], tresorier, par=tresorier.user)

    r = client.get(
        f"/tontines/{tontine_active.id}/paiements", params={"membre_id": bio.id}, headers=auth(bio.user)
    )

    assert [p["cycle_numero"] for p in r.json()] == [1, 2]
    assert all(p["membre_id"] == bio.id for p in r.json())


def test_rappels_seulement_pour_les_membres_en_retard(db, tontine_active):
    tresorier, bio = tontine_active.membres[0], tontine_active.membres[1]
    enregistrer_especes(db, tontine_active.cycles[0], bio, par=tresorier.user)

    # Le 30/01, seul le cycle 1 (échéance 31/01) est proche ; Bio a déjà payé.
    assert envoyer_rappels(db, date(2025, 1, 30)) == 2
    rappeles = {
        n.user_id for n in db.query(Notification).filter_by(type=TypeNotification.RAPPEL_COTISATION)
    }
    assert rappeles == {tresorier.user_id, tontine_active.membres[2].user_id}

    # Relancer le job le même jour (ou le lendemain) ne duplique pas les rappels.
    assert envoyer_rappels(db, date(2025, 1, 31)) == 0
