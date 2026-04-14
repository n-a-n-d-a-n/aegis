"""
Aegis — Database layer (SQLite for dev, PostgreSQL for prod)

All rows contain only:
  - A UUID submission ID
  - Encrypted ciphertext blobs
  - UTC timestamp
  - File extension (if applicable)

No IP addresses, user-agents, or any identifying information is ever stored.
"""

import os
import databases
import sqlalchemy

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegis.db")

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

submissions_table = sqlalchemy.Table(
    "submissions",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("encrypted_message", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("encrypted_file", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("file_ext", sqlalchemy.String(10), nullable=True),
    sqlalchemy.Column("timestamp", sqlalchemy.String, nullable=False),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)


async def init_db():
    metadata.create_all(engine)
    await database.connect()


async def save_submission(
    submission_id: str,
    encrypted_message: str,
    encrypted_file: str | None,
    file_ext: str | None,
    timestamp: str,
):
    query = submissions_table.insert().values(
        id=submission_id,
        encrypted_message=encrypted_message,
        encrypted_file=encrypted_file,
        file_ext=file_ext,
        timestamp=timestamp,
    )
    await database.execute(query)


async def get_all_submissions():
    query = submissions_table.select().order_by(
        submissions_table.c.timestamp.desc()
    )
    rows = await database.fetch_all(query)
    return [dict(row) for row in rows]


async def get_submission_by_id(submission_id: str):
    query = submissions_table.select().where(
        submissions_table.c.id == submission_id
    )
    row = await database.fetch_one(query)
    return dict(row) if row else None
