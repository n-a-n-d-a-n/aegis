# Aegis 🛡️

> A zero-trust, non-attributable whistleblower submission platform.  
> The origin server never sees submitter identity. Ever.

---

## Architecture

```
Submitter (ideally via Tor Browser)
        │
        ▼
┌─────────────────────────────────────┐
│           Cloudflare Edge           │
│  ┌──────────────────────────────┐   │
│  │ WAF + DDoS (Project Galileo) │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │ Worker — strips all PII      │   │
│  │ headers, hashed rate limit   │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
        │
        ▼  Cloudflare Tunnel (outbound-only, no open inbound ports)
┌─────────────────────────────────────┐
│           Origin Server             │
│  FastAPI — encrypts with journalist │
│  public key. Stores ciphertext only │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Database (SQLite dev / Postgres)   │
│  Encrypted blobs only — no PII      │
└─────────────────────────────────────┘

Admin Panel → Cloudflare Access (ZTNA + FIDO2 MFA + mTLS)
Decryption  → Offline only, journalist's air-gapped machine
```

---

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11) |
| Edge Proxy | Cloudflare Tunnel (`cloudflared`) |
| PII Stripping | Cloudflare Worker (JS) |
| DDoS / WAF | Project Galileo |
| Admin Auth | Cloudflare Access (ZTNA) |
| Encryption | RSA-4096 + AES-256-GCM hybrid |
| Storage | SQLite (dev) / PostgreSQL (prod) |
| Container | Docker + Docker Compose |

---

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/aegis.git
cd aegis
cp .env.example .env
# Fill in your values
```

### 2. Generate journalist keypair

```bash
# Ideally run on an air-gapped machine
python scripts/keygen.py

# Produces:
#   journalist_public.pem  → copy to backend/keys/
#   journalist_private.pem → NEVER on server — store offline on encrypted USB
```

### 3. Run with Docker

```bash
docker-compose up -d
```

### 4. Deploy Cloudflare Tunnel

```bash
bash scripts/setup.sh
```

Full walkthrough → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Security Properties

| Property | Implementation |
|---|---|
| No IP logging | Worker strips `CF-Connecting-IP` before reaching origin |
| End-to-end encryption | RSA-4096 + AES-GCM; server cannot decrypt |
| No open inbound ports | Cloudflare Tunnel (outbound-only connection) |
| Rate limiting without tracking | SHA-256 hashed IP + daily rotating salt |
| Admin zero-trust | Cloudflare Access + FIDO2 hardware MFA |
| File anonymization | Filename stripped, only extension preserved |

---

## Decrypting Submissions (Journalist Side)

```bash
# Always run offline, on journalist's local machine
python scripts/decrypt.py \
  --key journalist_private.pem \
  --id <submission_id>
```

---

## Docs

- [Deployment Guide](docs/DEPLOYMENT.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [OpSec Guide](docs/OPSEC.md)

---

## Project Galileo

This platform is designed to be eligible for
[Cloudflare Project Galileo](https://www.cloudflare.com/galileo/) —
free enterprise WAF and DDoS protection for journalism and civil society orgs.
Apply before going live.

---

## Disclaimer

Educational/research project demonstrating privacy-preserving infrastructure
patterns. Real-world deployment requires additional operational security measures
beyond what code alone provides. Read [docs/OPSEC.md](docs/OPSEC.md) carefully.

---

## License

MIT
