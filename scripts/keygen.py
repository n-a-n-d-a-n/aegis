#!/usr/bin/env python3
"""
Aegis — Journalist Keypair Generator

Run this on an air-gapped machine if possible.

Usage:
    python scripts/keygen.py
    python scripts/keygen.py --output-dir /path/to/safe/directory

Outputs:
    journalist_public.pem   → Copy to backend/keys/ on the server
    journalist_private.pem  → NEVER put this on any networked machine.
                              Store on an encrypted USB drive, offline.
"""

import argparse
import os
import sys
from pathlib import Path
from getpass import getpass

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generate_keypair(output_dir: Path, passphrase: bytes):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    public_key = private_key.public_key()

    # Serialize private key — encrypted with passphrase
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )

    # Serialize public key — no passphrase needed
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path = output_dir / "journalist_private.pem"
    public_path = output_dir / "journalist_public.pem"

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    # Restrict private key permissions (Unix only)
    if os.name != "nt":
        os.chmod(private_path, 0o600)

    return public_path, private_path


def main():
    parser = argparse.ArgumentParser(description="Generate Aegis journalist keypair")
    parser.add_argument("--output-dir", default=".", help="Directory to write keys")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Aegis — Journalist Keypair Generator")
    print("=" * 60)
    print()
    print("  Generating RSA-4096 keypair...")
    print()

    passphrase = getpass("  Enter passphrase for private key: ").encode()
    confirm = getpass("  Confirm passphrase: ").encode()

    if passphrase != confirm:
        print("\n  [ERROR] Passphrases do not match. Exiting.")
        sys.exit(1)

    if len(passphrase) < 12:
        print("\n  [WARNING] Passphrase is very short. Consider using a longer one.")

    public_path, private_path = generate_keypair(output_dir, passphrase)

    print()
    print("  ✓ Keys generated successfully")
    print()
    print(f"  Public key:  {public_path}")
    print(f"  Private key: {private_path}")
    print()
    print("  IMPORTANT:")
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  journalist_public.pem  → copy to backend/keys/     │")
    print("  │  journalist_private.pem → store OFFLINE on encrypted │")
    print("  │                           USB. NEVER put on server.  │")
    print("  └─────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    main()
