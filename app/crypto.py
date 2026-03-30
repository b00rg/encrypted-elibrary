import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AES_KEY_SIZE = 32
NONCE_SIZE = 12


def generate_aes_key() -> bytes:
    return os.urandom(AES_KEY_SIZE)


def encrypt_message(plaintext: str, aes_key: bytes) -> str:
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    raw = nonce + ciphertext
    return base64.b64encode(raw).decode("utf-8")


def decrypt_message(b64_ciphertext: str, aes_key: bytes) -> str | None:
    try:
        raw = base64.b64decode(b64_ciphertext)
        nonce = raw[:NONCE_SIZE]
        ciphertext = raw[NONCE_SIZE:]
        aesgcm = AESGCM(aes_key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")
    except Exception:
        return None


def is_encrypted(text: str) -> bool:
    if not text:
        return False
    try:
        raw = base64.b64decode(text, validate=True)
        return len(raw) > NONCE_SIZE
    except Exception:
        return False
