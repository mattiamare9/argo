"""Cifratura dei segreti a riposo (Fernet). La chiave arriva da ARGO_SECRETS_KEY."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class SecretsError(Exception):
    """Chiave assente o non valida, oppure segreto non decifrabile."""


def _fernet(settings: Settings) -> Fernet:
    if settings.secrets_key is None:
        raise SecretsError("ARGO_SECRETS_KEY non configurata")
    try:
        return Fernet(settings.secrets_key.get_secret_value())
    except ValueError as exc:
        raise SecretsError("ARGO_SECRETS_KEY non valida") from exc


def encrypt(settings: Settings, plaintext: str) -> str:
    return _fernet(settings).encrypt(plaintext.encode()).decode()


def decrypt(settings: Settings, ciphertext: str) -> str:
    try:
        return _fernet(settings).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise SecretsError("segreto non decifrabile con la chiave attuale") from exc
