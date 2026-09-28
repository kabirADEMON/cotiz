from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import ErreurMetier
from app.routers import auth, cycles, notifications, paiements, tontines, users, webhooks

app = FastAPI(
    title="Cotiz API",
    description="Gestion de tontines (épargne collective rotative) avec paiement Mobile Money via FedaPay.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErreurMetier)
def erreur_metier(_: Request, exc: ErreurMetier):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


for module in (auth, users, tontines, cycles, paiements, notifications, webhooks):
    app.include_router(module.router)


@app.get("/health", tags=["Système"])
def health():
    return {"status": "ok"}
