"""
Symmetric encryption utility for storing embassy credentials at rest.
Uses Fernet (AES-128-CBC + HMAC-SHA256) derived from the app SECRET_KEY.
"""
import base64
import hashlib
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    """Derive a 32-byte Fernet key from the app SECRET_KEY."""
    from ..config import settings
    # SHA-256 gives exactly 32 bytes, base64-url-encode for Fernet
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_password(plaintext: str) -> str:
    """Encrypt a plaintext password for storage in the DB."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a stored password so scrapers can use it."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
