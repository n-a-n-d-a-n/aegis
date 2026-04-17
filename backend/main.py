import uuid
import datetime
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from cryptography.hazmat.primitives import serialization
from crypto import encrypt_message, encrypt_file_hybrid
from database import init_db, save_submission, get_all_submissions, get_submission_by_id

app = FastAPI(
    title="Aegis",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["content-type"],
)

PUBLIC_KEY = None

@app.on_event("startup")
async def startup():
    global PUBLIC_KEY
    key_path = os.getenv("PUBLIC_KEY_PATH", "keys/journalist_public.pem")
    try:
        with open(key_path, "rb") as f:
            PUBLIC_KEY = serialization.load_pem_public_key(f.read())
        print(f"[aegis] Public key loaded from {key_path}")
    except FileNotFoundError:
        raise RuntimeError(
            f"Public key not found at '{key_path}'.\n"
            "Run: python scripts/keygen.py and copy journalist_public.pem to backend/keys/"
        )
    await init_db()
    print("[aegis] Database initialised")


@app.post("/submit", status_code=201)
async def submit(
    message: str = Form(..., min_length=1, max_length=50_000),
    file: UploadFile = File(None),
):
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
        parts = file.filename.rsplit(".", 1)
        file_ext = parts[1].lower() if len(parts) == 2 else "bin"

    await save_submission(
        submission_id=submission_id,
        encrypted_message=encrypted_msg,
        encrypted_file=encrypted_file,
        file_ext=file_ext,
        timestamp=timestamp,
    )
    return {"status": "received", "id": submission_id}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/admin/submissions")
async def list_submissions():
    submissions = await get_all_submissions()
    return {"submissions": submissions}


@app.get("/admin/submissions/{submission_id}")
async def get_submission(submission_id: str):
    sub = await get_submission_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub
