"""Decrypts sign-ins sent from the phone. The phone encrypts with AES-256-GCM using a key
made from the pairing code, which is typed into the phone by hand and never sent over ntfy."""
import base64
import hashlib
import json


def key_from_code(code):
    norm = "".join(ch for ch in code.upper() if ch.isalnum())
    return hashlib.sha256(("clipcartel:" + norm).encode()).digest()


def decrypt(blob_b64, code):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = base64.b64decode(blob_b64)
    nonce, ct = raw[:12], raw[12:]
    data = AESGCM(key_from_code(code)).decrypt(nonce, ct, None)
    return json.loads(data.decode("utf-8"))


def encrypt(obj, code):
    """Used for tests (the phone does the same thing in Kotlin)."""
    import os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ct = AESGCM(key_from_code(code)).encrypt(nonce, json.dumps(obj).encode(), None)
    return base64.b64encode(nonce + ct).decode()
