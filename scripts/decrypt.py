#!/usr/bin/env python3
"""
Aegis — Offline Submission Decryptor

Run this on the journalist's LOCAL machine only.
Never run on the server. Never over a network connection.

Usage:
    # Decrypt a single submission by ID (fetches from admin API)
    python scripts/decrypt.py --key journalist_private.pem --id <uuid>

    # Decrypt from a local JSON export file
    python scripts/decrypt.py --key journalist_private.pem --file submission.json

    # Dump all submissions (requires admin API access)
    python scripts/decrypt.py --key journalist_private.pem --all --api https://admin.yourdomain.com
"""

import argparse
import base64
import json
import sys
import os
from getpass import getpass
from pathlib import Path

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def load_private_key(key_path: str):
    passphrase = getpass(f"Passphrase for {key_path}: ").encode()
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=passphrase)


def decrypt_message(encrypted_b64: str, private_key) -> str:
    ciphertext = base64.b64decode(encrypted_b64)
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return plaintext.decode("utf-8")


def decrypt_file(payload_json: str, private_key) -> bytes:
    payload = json.loads(payload_json)

    # Unwrap AES key with RSA private key
    aes_key = private_key.decrypt(
        base64.b64decode(payload["encrypted_key"]),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Decrypt file content with AES-256-GCM
    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(
        base64.b64decode(payload["nonce"]),
        base64.b64decode(payload["ciphertext"]),
        None,
    )
    return plaintext


def print_submission(sub: dict, private_key):
    print()
    print("=" * 60)
    print(f"  ID:        {sub['id']}")
    print(f"  Received:  {sub['timestamp']} UTC")
    print("=" * 60)

    try:
        message = decrypt_message(sub["encrypted_message"], private_key)
        print("\n  MESSAGE:")
        print()
        for line in message.splitlines():
            print(f"    {line}")
    except Exception as e:
        print(f"\n  [ERROR] Could not decrypt message: {e}")

    if sub.get("encrypted_file"):
        ext = sub.get("file_ext", "bin")
        out_filename = f"aegis_{sub['id'][:8]}.{ext}"
        try:
            file_bytes = decrypt_file(sub["encrypted_file"], private_key)
            out_path = Path(out_filename)
            out_path.write_bytes(file_bytes)
            print(f"\n  FILE: saved to {out_path} ({len(file_bytes):,} bytes)")
        except Exception as e:
            print(f"\n  [ERROR] Could not decrypt file: {e}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Aegis offline submission decryptor")
    parser.add_argument("--key", required=True, help="Path to journalist_private.pem")
    parser.add_argument("--id", help="Submission UUID to decrypt")
    parser.add_argument("--file", help="Local JSON file containing submission data")
    parser.add_argument("--all", action="store_true", help="Decrypt all submissions")
    parser.add_argument("--api", default="http://localhost:8000", help="Admin API base URL")
    args = parser.parse_args()

    print("\n  Aegis — Offline Decryptor")
    print("  Loading private key...\n")

    try:
        private_key = load_private_key(args.key)
    except Exception as e:
        print(f"  [ERROR] Failed to load private key: {e}")
        sys.exit(1)

    print("  ✓ Private key loaded\n")

    if args.file:
        # Decrypt from a local JSON file
        with open(args.file) as f:
            sub = json.load(f)
        print_submission(sub, private_key)

    elif args.id:
        # Fetch single submission from admin API
        import urllib.request
        url = f"{args.api.rstrip('/')}/admin/submissions/{args.id}"
        try:
            with urllib.request.urlopen(url) as resp:
                sub = json.loads(resp.read())
            print_submission(sub, private_key)
        except Exception as e:
            print(f"  [ERROR] Could not fetch submission: {e}")
            sys.exit(1)

    elif args.all:
        # Fetch and decrypt all submissions
        import urllib.request
        url = f"{args.api.rstrip('/')}/admin/submissions"
        try:
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())
            submissions = data.get("submissions", [])
            print(f"  Found {len(submissions)} submission(s)")
            for sub in submissions:
                print_submission(sub, private_key)
        except Exception as e:
            print(f"  [ERROR] Could not fetch submissions: {e}")
            sys.exit(1)

    else:
        print("  Provide --id, --file, or --all")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
