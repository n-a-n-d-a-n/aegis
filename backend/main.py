import uuid
import datetime
import os

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from cryptography.hazmat.primitives import serialization

from crypto import encrypt_message, encrypt_file_hybrid
from database import init_db, save_submission, get_all_submissions, get_submission_by_id

app = FastAPI(
    title="Aegis",
    docs_url=None,   # Disable Swagger in production
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["content-type"],
)


# ── Load journalist public key at startup ─────────────────────────────────────

PUBLIC_KEY_PATH = os.getenv("PUBLIC_KEY_PATH", "keys/journalist_public.pem")

try:
    with open(PUBLIC_KEY_PATH, "rb") as f:
        PUBLIC_KEY = serialization.load_pem_public_key(f.read())
    print(f"[aegis] Public key loaded from {PUBLIC_KEY_PATH}")
except FileNotFoundError:
    raise RuntimeError(
        f"Public key not found at '{PUBLIC_KEY_PATH}'.\n"
        "Run: python scripts/keygen.py and copy journalist_public.pem to backend/keys/"
    )


@app.on_event("startup")
async def startup():
    await init_db()
    print("[aegis] Database initialised")


# ── Public: submission endpoint ───────────────────────────────────────────────

@app.post("/submit", status_code=201)
async def submit(
    message: str = Form(..., min_length=1, max_length=50_000),
    file: UploadFile = File(None),
):
    """
    Accept an anonymous submission.

    Security guarantees:
    - No IP stored (Cloudflare Worker strips CF-Connecting-IP upstream)
    - Message encrypted with journalist RSA public key before storage
    - File encrypted with hybrid RSA+AES scheme
    - Server holds zero decryption capability
    """
    submission_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat()

    encrypted_msg = encrypt_message(message, PUBLIC_KEY)

    encrypted_file = None
    file_ext = None
    if file and file.filename:
        contents = await file.read()
        if len(contents) > 100 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 100 MB)")
        encrypted_file = encrypt_file_hybrid(contents, PUBLIC_KEY)
        # Preserve only extension — strip identifying filename
        parts = file.filename.rsplit(".", 1)
        file_ext = parts[1].lower() if len(parts) == 2 else "bin"

    await save_submission(
        submission_id=submission_id,
        encrypted_message=encrypted_msg,
        encrypted_file=encrypted_file,
        file_ext=file_ext,
        timestamp=timestamp,
        # Notice: no IP, no user-agent, no fingerprint stored
    )

    return {"status": "received", "id": submission_id}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Admin: read submissions (protected by Cloudflare Access upstream) ─────────

@app.get("/admin/submissions")
async def list_submissions():
    """
    Returns encrypted submission blobs.
    This endpoint must be behind Cloudflare Access — do not expose publicly.
    Decryption always happens offline via scripts/decrypt.py.
    """
    submissions = await get_all_submissions()
    return {"submissions": submissions}


@app.get("/admin/submissions/{submission_id}")
async def get_submission(submission_id: str):
    sub = await get_submission_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub
