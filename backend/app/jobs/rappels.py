"""Envoie les rappels de cotisation. À lancer une fois par jour (cron, planificateur Windows…).

    python -m app.jobs.rappels
"""

from datetime import date

from app.database import SessionLocal
from app.services.notifications import envoyer_rappels


def main() -> None:
    with SessionLocal() as db:
        total = envoyer_rappels(db, date.today())
    print(f"{total} rappel(s) envoyé(s)")


if __name__ == "__main__":
    main()
