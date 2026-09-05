from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from hashlib import sha256
from base64 import urlsafe_b64encode

from app.config import get_settings


def _fernet(key: str) -> Fernet:
    digest = sha256(key.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    settings = get_settings()
    key = settings.credentials_key or settings.secret_key
    return _fernet(key).encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    settings = get_settings()
    keys = [settings.credentials_key or settings.secret_key]
    if settings.credentials_key and settings.secret_key not in keys:
        # Permite leer secretos creados antes de separar la clave de credenciales.
        keys.append(settings.secret_key)
    for key in keys:
        try:
            return _fernet(key).decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            continue
    raise InvalidToken


def decrypt_totp_compat(value: str) -> str:
    """Lee TOTP cifrado y, temporalmente, valores legacy en claro."""
    try:
        return decrypt_secret(value)
    except InvalidToken:
        return value
