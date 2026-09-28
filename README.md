# Cotiz — gestion de tontines

![CI](https://github.com/kabirADEMON/cotiz/actions/workflows/ci.yml/badge.svg)

**Cotiz** est une application web de gestion de **tontines** (épargne collective rotative), pensée pour le Bénin :
chaque membre cotise un montant fixe à chaque échéance, et la cagnotte est versée à tour de rôle
à un bénéficiaire. Les cotisations se règlent en **Mobile Money via FedaPay** ou en espèces auprès
du trésorier.

**Stack** : FastAPI · PostgreSQL · SQLAlchemy 2 · Alembic · JWT · React (Vite) · pytest · GitHub Actions

---

## Fonctionnalités

- **Comptes et rôles** : inscription par numéro de téléphone (`+229…`), mots de passe hashés (bcrypt), authentification JWT.
  - **Admin** (rôle global) : gère les comptes de la plateforme.
  - **Trésorier** (rôle par tontine) : gère les membres, l'ordre de passage, encaisse les espèces et verse la cagnotte.
  - **Membre** : consulte sa tontine et paie ses cotisations.
- **Tontines** : montant de cotisation, fréquence (quotidienne, hebdomadaire, mensuelle), ordre de passage modifiable.
- **Cycles** : au démarrage, le calendrier complet est généré (un cycle par membre, dans l'ordre de passage).
- **Paiements** : Mobile Money via FedaPay (sandbox), avec webhook signé, ou espèces enregistrées par le trésorier.
- **Historique** des paiements par membre et par cycle.
- **Notifications** : paiement reçu, cagnotte versée, rappels de cotisation (tâche quotidienne).

## Règles métier

| Règle | Où |
|---|---|
| Une tontine démarre avec au moins 2 membres ; ensuite, membres et ordre sont figés | `services/cycles.py` |
| Échéances calculées selon la fréquence (en mensuel, le 31 janv. donne le 28/29 févr. puis le 31 mars) | `ajouter_periodes` |
| Un seul paiement réussi par membre et par cycle (index unique partiel en base) | `models.py` |
| Les tentatives FedaPay échouées restent dans l'historique ; le membre peut réessayer | `services/paiements.py` |
| Un cycle n'est clôturé (cagnotte versée) que si tous les membres ont payé, et dans l'ordre | `cloturer_cycle` |
| La clôture du dernier cycle termine la tontine | `cloturer_cycle` |
| Un seul rappel par membre et par cycle | `envoyer_rappels` |

## Modèle de données

```mermaid
erDiagram
    users ||--o{ membres_tontine : "adhère"
    tontines ||--o{ membres_tontine : "compte"
    tontines ||--o{ cycles : "planifie"
    membres_tontine ||--o{ cycles : "bénéficie"
    cycles ||--o{ paiements : "reçoit"
    membres_tontine ||--o{ paiements : "effectue"
    users ||--o{ notifications : "reçoit"

    users { int id string telephone string password_hash bool is_admin }
    tontines { int id string nom int montant_cotisation enum frequence date date_debut enum statut }
    membres_tontine { int id enum role int ordre_passage }
    cycles { int id int numero date date_echeance enum statut int montant_attendu datetime verse_le }
    paiements { int id int montant enum methode enum statut string fedapay_transaction_id }
    notifications { int id enum type text message bool lu }
```

## Lancer le projet

### Prérequis

- Python 3.12+
- Node.js 20+
- PostgreSQL 14+ (ou Docker)

### 1. Base de données

Avec Docker :

```bash
docker compose up -d db
```

Ou avec un PostgreSQL installé localement :

```sql
CREATE USER tontine WITH PASSWORD 'tontine';
CREATE DATABASE tontine OWNER tontine;
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate    |    Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                  # puis ajuster DATABASE_URL et JWT_SECRET
alembic upgrade head                  # crée les tables
python -m app.seed                    # (facultatif) données de démo
uvicorn app.main:app --reload
```

- API : http://localhost:8000
- Documentation interactive (Swagger) : http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env                  # VITE_API_URL=http://localhost:8000
npm run dev
```

Application : http://localhost:5180

### Comptes de démo

Créés par `python -m app.seed`, avec le mot de passe **`demo1234`** pour tous :

| Téléphone | Profil |
|---|---|
| `+2290100000000` | Admin de la plateforme |
| `+2290197000001` | Afi : trésorière de la tontine « Dantokpa » (cycle 1 versé, cycle 2 en cours) |
| `+2290197000002` | Bio : membre, trésorier de « Épargne entre amis » (en préparation) |
| `+2290197000003` | Codjo : membre, cotisation du cycle 2 en attente |

Hors démo, le premier compte inscrit devient automatiquement administrateur.

## Paiement FedaPay (sandbox)

1. Créer un compte sur [FedaPay](https://fedapay.com), passer en mode **Sandbox**, puis copier la clé secrète (`sk_sandbox_…`) dans `FEDAPAY_SECRET_KEY`.
2. Dans *Webhooks*, ajouter l'URL `https://<votre-url-publique>/webhooks/fedapay` et copier la clé de signature dans `FEDAPAY_WEBHOOK_SECRET`. En local, exposer l'API avec [ngrok](https://ngrok.com) : `ngrok http 8000`.
3. Payer une cotisation depuis la page d'un cycle et utiliser les numéros de test indiqués dans la documentation FedaPay.

**Déroulement :**

```
Membre ──► POST /cycles/{id}/paiements/fedapay ──► paiement « en_attente » + transaction FedaPay
       ◄── URL de paiement FedaPay
Membre ──► paie sur la page FedaPay ──► redirigé vers /paiements/{id}/retour (frontend)
FedaPay ──► POST /webhooks/fedapay (signature HMAC vérifiée)
API ──► relit le statut auprès de FedaPay ──► paiement « reussi » + notification
```

Le webhook ne fait pas confiance au contenu de l'événement : le statut est toujours relu auprès de
l'API FedaPay. Sans webhook (en local sans ngrok), la page de retour appelle
`POST /paiements/{id}/verifier`, qui fait la même vérification.

## Rappels de cotisation

À planifier une fois par jour (cron sous Linux, Planificateur de tâches sous Windows) :

```bash
cd backend && python -m app.jobs.rappels
```

Un rappel est envoyé aux membres qui n'ont pas payé lorsque l'échéance est dans 2 jours ou moins, ou déjà dépassée.

## Tests

```bash
cd backend
pytest                      # SQLite en mémoire, aucune configuration nécessaire
TEST_DATABASE_URL=postgresql+psycopg://tontine:tontine@localhost:5432/tontine_test pytest
```

Les tests couvrent :
- le calcul des échéances ;
- la génération et la clôture des cycles ;
- les paiements en espèces et FedaPay (API simulée) ;
- la vérification de signature du webhook ;
- l'idempotence ;
- les contrôles d'accès ;
- les rappels.

La CI GitHub Actions lance les migrations (aller-retour) et les tests sur PostgreSQL, puis le build du frontend.

## Principaux endpoints

| Méthode | Route | Accès |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | Public |
| GET | `/auth/me` | Connecté |
| GET, POST | `/tontines` | Connecté |
| GET | `/tontines/{id}`, `/tontines/{id}/cycles`, `/tontines/{id}/paiements` | Membre |
| POST, DELETE | `/tontines/{id}/membres` | Trésorier |
| PUT | `/tontines/{id}/ordre` | Trésorier |
| POST | `/tontines/{id}/demarrer` | Trésorier |
| GET | `/cycles/{id}` | Membre |
| POST | `/cycles/{id}/paiements/fedapay` | Membre |
| POST | `/cycles/{id}/paiements/especes` | Trésorier |
| POST | `/cycles/{id}/cloturer` | Trésorier |
| GET | `/paiements/me` | Connecté |
| POST | `/paiements/{id}/verifier` | Payeur ou trésorier |
| GET, POST | `/notifications…` | Connecté |
| GET, PATCH | `/users` | Admin |
| POST | `/webhooks/fedapay` | FedaPay (signé) |

## Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py            # Application FastAPI
│   │   ├── models.py          # Modèles SQLAlchemy
│   │   ├── schemas.py         # Schémas Pydantic
│   │   ├── deps.py            # Authentification et contrôles d'accès
│   │   ├── routers/           # Endpoints HTTP (couche fine)
│   │   ├── services/          # Logique métier : cycles, paiements, FedaPay, notifications
│   │   ├── jobs/rappels.py    # Tâche quotidienne
│   │   └── seed.py            # Données de démo
│   ├── alembic/               # Migrations
│   └── tests/
├── frontend/src/
│   ├── pages/                 # Écrans
│   ├── components/
│   └── api.js                 # Client HTTP
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Pistes d'évolution

- Notifications par SMS (par ex. via un agrégateur local) en plus des notifications dans l'application
- Versement automatique de la cagnotte au bénéficiaire (payouts FedaPay)
- Pénalités de retard configurables
- Déploiement (Render / Railway pour l'API, Vercel pour le frontend)
