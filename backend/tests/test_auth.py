def inscrire(client, telephone="+2290197000001", password="motdepasse"):
    return client.post(
        "/auth/register",
        json={"nom": "Houngbo", "prenom": "Aïcha", "telephone": telephone, "password": password},
    )


def test_inscription_puis_connexion(client):
    assert inscrire(client).status_code == 201

    r = client.post("/auth/login", data={"username": "+2290197000001", "password": "motdepasse"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["telephone"] == "+2290197000001"
    assert "password_hash" not in me.json()


def test_premier_compte_admin_les_suivants_non(client):
    assert inscrire(client).json()["is_admin"] is True
    assert inscrire(client, "+2290197000002").json()["is_admin"] is False


def test_mot_de_passe_hashe(client, db):
    from app.models import User

    inscrire(client)
    assert db.query(User).one().password_hash.startswith("$2b$")


def test_mauvais_mot_de_passe(client):
    inscrire(client)
    r = client.post("/auth/login", data={"username": "+2290197000001", "password": "mauvais"})
    assert r.status_code == 401


def test_numero_deja_utilise(client):
    inscrire(client)
    assert inscrire(client).status_code == 409


def test_numero_invalide(client):
    assert inscrire(client, telephone="0197000001").status_code == 422


def test_route_protegee_sans_token(client):
    assert client.get("/tontines").status_code == 401
