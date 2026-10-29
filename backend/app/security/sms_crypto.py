"""
Lightweight symmetric SMS envelope.

Wire format (single SMS, GSM-7 safe after base64url):

    HLTH ENC <base64url(nonce(12) || ciphertext || tag(16))>

PSK is rotated monthly, derived from a master secret kept server-side.
The offline PWA mirrors this derivation in JS (see frontend/src/crypto.js).
"""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..config import settings

PREFIX = "HLTH ENC "


def _monthly_psk(year: int, month: int) -> bytes:
    master = settings.sms_master_psk.encode()
    msg = f"{year:04d}-{month:02d}".encode()
    return hmac.new(master, msg, hashlib.sha256).digest()


def current_psk() -> bytes:
    now = datetime.now(timezone.utc)
    return _monthly_psk(now.year, now.month)


def previous_psk() -> bytes:
    now = datetime.now(timezone.utc)
    y, m = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    return _monthly_psk(y, m)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def encrypt_sms(plaintext: str, psk: bytes | None = None) -> str:
    key = psk or current_psk()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return PREFIX + _b64url(nonce + ct)


def decrypt_sms(payload: str) -> str:
    """Accepts either a raw HLTH ENC payload or the inner base64url token."""
    body = payload[len(PREFIX):] if payload.startswith(PREFIX) else payload
    raw = _b64url_decode(body.strip())
    if len(raw) < 12 + 16:
        raise ValueError("payload too short")
    nonce, ct = raw[:12], raw[12:]
    for key in (current_psk(), previous_psk()):
        try:
            return AESGCM(key).decrypt(nonce, ct, None).decode()
        except Exception:
            continue
    raise ValueError("decryption_failed")