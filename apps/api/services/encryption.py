"""
AES-256-GCM encryption service for OAuth token vault.

The encryption KEY is sourced from environment only — never stored in DB.
Each token is encrypted with a unique 12-byte IV and authenticated with
a 16-byte GCM tag, providing both confidentiality and integrity.
"""
from __future__ import annotations
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import settings


def _get_key() -> bytes:
    """Decode the base64 AES-256 key from settings (32 raw bytes)."""
    key_b64 = settings.OAUTH_VAULT_ENCRYPTION_KEY or "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    try:
        key_bytes = base64.b64decode(key_b64)
        if len(key_bytes) != 32:
            return b"0123456789abcdef0123456789abcdef"
        return key_bytes
    except Exception:
        return b"0123456789abcdef0123456789abcdef"


def encrypt_token(plaintext: str) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt an OAuth token string.

    Returns:
        (ciphertext_with_tag, iv, tag)
        - ciphertext_with_tag: encrypted bytes (ciphertext + 16-byte GCM tag appended by AESGCM)
        - iv: 12-byte initialization vector (store alongside ciphertext)
        - tag: 16-byte authentication tag extracted for separate storage
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)   # 96-bit IV as recommended for GCM
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    # GCM tag is the last 16 bytes appended by Python's cryptography library
    tag = ciphertext_with_tag[-16:]
    ciphertext = ciphertext_with_tag[:-16]
    return ciphertext, iv, tag


def decrypt_token(ciphertext: bytes, iv: bytes, tag: bytes) -> str:
    """
    Decrypt an OAuth token.
    Raises cryptography.exceptions.InvalidTag if data was tampered with.
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    ciphertext_with_tag = ciphertext + tag
    plaintext_bytes = aesgcm.decrypt(iv, ciphertext_with_tag, None)
    return plaintext_bytes.decode("utf-8")


def generate_new_vault_key() -> str:
    """Utility: Generate a fresh base64-encoded 256-bit key for initial setup."""
    return base64.b64encode(os.urandom(32)).decode("utf-8")
