from cryptography.fernet import Fernet
from hashlib import sha256
from base64 import urlsafe_b64encode

from app.config import get_settings


def _fernet() -> Fernet:
    digest = sha256(get_settings().secret_key.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
