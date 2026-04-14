"""
Aegis — Backend Tests

Run with: pytest tests/ -v
"""

import pytest
import base64
import json
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def keypair():
    """Generate a test RSA keypair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(scope="session")
def public_key_pem(keypair, tmp_path_factory):
    """Write public key to a temp file and return the path."""
    _, public_key = keypair
    pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    keys_dir = tmp_path_factory.mktemp("keys")
    key_path = keys_dir / "journalist_public.pem"
    key_path.write_bytes(pem)
    return str(key_path)


# ── Crypto unit tests ─────────────────────────────────────────────────────────

def test_encrypt_message_roundtrip(keypair):
    from crypto import encrypt_message

    private_key, public_key = keypair
    plaintext = "This is a secret message."

    encrypted = encrypt_message(plaintext, public_key)
    assert isinstance(encrypted, str)

    # Decrypt and verify
    decrypted = private_key.decrypt(
        base64.b64decode(encrypted),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    assert decrypted.decode() == plaintext


def test_encrypt_file_hybrid_roundtrip(keypair):
    from crypto import encrypt_file_hybrid
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    private_key, public_key = keypair
    file_bytes = b"Secret file content " * 100

    payload_json = encrypt_file_hybrid(file_bytes, public_key)
    payload = json.loads(payload_json)

    # Decrypt AES key with RSA
    aes_key = private_key.decrypt(
        base64.b64decode(payload["encrypted_key"]),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Decrypt file content
    aesgcm = AESGCM(aes_key)
    decrypted = aesgcm.decrypt(
        base64.b64decode(payload["nonce"]),
        base64.b64decode(payload["ciphertext"]),
        None,
    )
    assert decrypted == file_bytes


# ── API integration tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(public_key_pem, monkeypatch):
    monkeypatch.setenv("PUBLIC_KEY_PATH", public_key_pem)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_aegis.db")

    import importlib
    import main as app_module
    importlib.reload(app_module)

    async with AsyncClient(
        transport=ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_submit_text_only(public_key_pem, monkeypatch):
    monkeypatch.setenv("PUBLIC_KEY_PATH", public_key_pem)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_aegis.db")

    import importlib
    import main as app_module
    importlib.reload(app_module)

    async with AsyncClient(
        transport=ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/submit",
            data={"message": "Test submission from automated test suite."},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "received"
    assert "id" in data
    assert len(data["id"]) == 36  # UUID format
