"""
Aegis — Cryptographic primitives

All encryption is asymmetric-first:
  - Short messages:  RSA-4096 OAEP directly
  - Files/long data: Hybrid — AES-256-GCM for content, RSA wraps the AES key

The server ONLY encrypts. It never holds the private key and cannot decrypt.
"""

import os
import base64
import json

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_message(plaintext: str, public_key) -> str:
    """
    Encrypt a short text message with RSA-OAEP.
    Returns base64-encoded ciphertext string.
    """
    ciphertext = public_key.encrypt(
        plaintext.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode("utf-8")


def encrypt_file_hybrid(file_bytes: bytes, public_key) -> str:
    """
    Hybrid encryption for arbitrary-size files.

    Steps:
      1. Generate a random 256-bit AES session key
      2. Encrypt file bytes with AES-256-GCM
      3. Wrap the AES key with RSA-4096-OAEP
      4. Return JSON blob containing all components (base64 encoded)

    Only the holder of the RSA private key can recover the AES key
    and therefore decrypt the file.
    """
    # 1. Random AES-256 session key + nonce
    aes_key = os.urandom(32)
    nonce = os.urandom(12)

    # 2. Encrypt file content
    aesgcm = AESGCM(aes_key)
    ciphertext = aesgcm.encrypt(nonce, file_bytes, None)

    # 3. Wrap AES key with RSA
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # 4. Bundle everything
    payload = {
        "v": 1,  # schema version for future compatibility
        "encrypted_key": base64.b64encode(encrypted_aes_key).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }
    return json.dumps(payload)
