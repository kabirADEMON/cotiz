class ErreurMetier(Exception):
    """Règle métier non respectée. Convertie en réponse HTTP par main.py."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NonTrouve(ErreurMetier):
    def __init__(self, message: str = "Ressource introuvable"):
        super().__init__(message, 404)


class Interdit(ErreurMetier):
    def __init__(self, message: str = "Action non autorisée"):
        super().__init__(message, 403)


class Conflit(ErreurMetier):
    def __init__(self, message: str):
        super().__init__(message, 409)
