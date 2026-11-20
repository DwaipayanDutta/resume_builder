"""Accounts for Resume Studio: register, sign in, sign out, current user.

Storage
  * Local / self-hosted: SQLite file (``RESUME_DB_PATH``, default ``~/.resume_studio/studio.db``).
  * Hosted (e.g. Vercel): PostgreSQL when ``DATABASE_URL`` or ``POSTGRES_URL`` is set
    (Vercel's Neon integration sets these). Needs ``psycopg``.
  * On Vercel without a database the API answers 503 with setup instructions instead of
    silently keeping accounts on a disk that is wiped between requests.

Security
  * Passwords: salted scrypt hashes. Sessions: random tokens in an HttpOnly, SameSite=Lax
    cookie (Secure when served over HTTPS); only a SHA-256 of each token is stored.
  * Failed sign-ins are recorded in the database, so throttling also works when requests are
    spread across several serverless instances.
  * ``require_session`` (middleware in ``main.py``) protects every ``/api/*`` route except
    ``/api/auth/*``.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "rs_session"
SESSION_TTL = 30 * 24 * 3600
MIN_PASSWORD = 8
MAX_FAILED_LOGINS = 5
FAILED_WINDOW = 15 * 60
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}

NO_DB_MESSAGE = ("Accounts database is not configured. In Vercel, open the project's Storage tab, "
                 "add a Postgres (Neon) database and redeploy.")


class DatabaseNotConfigured(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Storage: one small adapter over SQLite (local) and PostgreSQL (hosted)
# --------------------------------------------------------------------------
def database_url() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or None


def db_path() -> Path:
    env = os.environ.get("RESUME_DB_PATH")
    return Path(env) if env else Path.home() / ".resume_studio" / "studio.db"


_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS failed_logins (
    email TEXT NOT NULL,
    at DOUBLE PRECISION NOT NULL
);
"""
_SCHEMA_PG = (_SCHEMA_SQLITE
              .replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
              .replace("user_id INTEGER", "user_id BIGINT"))

_schema_ready: set[str] = set()


class DB:
    """Minimal wrapper: SQL is written with ``?`` placeholders for both engines."""

    def __init__(self, conn: Any, postgres: bool):
        self.conn = conn
        self.postgres = postgres

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.postgres else sql

    def all(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = self.conn.execute(self._sql(sql), params)
        return [dict(r) for r in cur.fetchall()]

    def one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def run(self, sql: str, params: tuple = ()) -> None:
        self.conn.execute(self._sql(sql), params)


def _is_unique_violation(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    return getattr(exc, "sqlstate", None) == "23505"


@contextlib.contextmanager
def connect() -> Iterator[DB]:
    url = database_url()
    if url:
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
        db = DB(conn, postgres=True)
        key = "pg:" + url
        schema = _SCHEMA_PG
    else:
        if os.environ.get("VERCEL") and not os.environ.get("RESUME_DB_PATH"):
            raise DatabaseNotConfigured(NO_DB_MESSAGE)
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        db = DB(conn, postgres=False)
        key = "sqlite:" + str(path)
        schema = _SCHEMA_SQLITE
    try:
        if key not in _schema_ready:
            for stmt in filter(str.strip, schema.split(";")):
                db.run(stmt)
            conn.commit()
            _schema_ready.add(key)
        yield db
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@dataclass
class User:
    id: int
    email: str
    name: str


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, dklen=32, **_SCRYPT)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        expected = base64.b64decode(hash_b64)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt_b64),
                                dklen=len(expected), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _create_session(db: DB, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    db.run("DELETE FROM sessions WHERE expires_at < ?", (now,))
    db.run("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
           (_token_hash(token), user_id, now, now + SESSION_TTL))
    return token


def user_for_token(token: Optional[str]) -> Optional[User]:
    if not token:
        return None
    with connect() as db:
        row = db.one(
            "SELECT u.id, u.email, u.name FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (_token_hash(token), time.time()),
        )
    return User(row["id"], row["email"], row["name"]) if row else None


def _is_https(request: Request) -> bool:
    return (request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"
            or bool(os.environ.get("VERCEL")))


def _set_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_TTL, httponly=True, samesite="lax",
        secure=_is_https(request), path="/",
    )


# --------------------------------------------------------------------------
# Brute-force throttle (per email, stored in the database)
# --------------------------------------------------------------------------
def _too_many_failures(db: DB, email: str) -> bool:
    cutoff = time.time() - FAILED_WINDOW
    db.run("DELETE FROM failed_logins WHERE at < ?", (cutoff,))
    row = db.one("SELECT COUNT(*) AS n FROM failed_logins WHERE email = ? AND at >= ?", (email, cutoff))
    return bool(row) and int(row["n"]) >= MAX_FAILED_LOGINS


def _record_failure(email: str) -> None:
    with connect() as db:
        db.run("INSERT INTO failed_logins (email, at) VALUES (?, ?)", (email, time.time()))


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
class UserOut(BaseModel):
    id: int
    email: str
    name: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _clean_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return email


@router.post("/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest, request: Request, response: Response) -> UserOut:
    name = (req.name or "").strip()
    if not 1 <= len(name) <= 80:
        raise HTTPException(status_code=422, detail="Enter your name (up to 80 characters).")
    email = _clean_email(req.email)
    if len(req.password) < MIN_PASSWORD:
        raise HTTPException(status_code=422, detail=f"Use a password of at least {MIN_PASSWORD} characters.")
    if len(req.password) > 256:
        raise HTTPException(status_code=422, detail="That password is too long.")
    password_hash = hash_password(req.password)
    try:
        with connect() as db:
            row = db.one(
                "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?) RETURNING id",
                (email, name, password_hash, time.time()),
            )
            user_id = int(row["id"])
            token = _create_session(db, user_id)
    except Exception as e:
        if _is_unique_violation(e):
            raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")
        raise
    _set_cookie(response, request, token)
    return UserOut(id=user_id, email=email, name=name)


@router.post("/login", response_model=UserOut)
def login(req: LoginRequest, request: Request, response: Response) -> UserOut:
    email = (req.email or "").strip().lower()
    with connect() as db:
        if _too_many_failures(db, email):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Wait 15 minutes and try again.")
        row = db.one("SELECT id, email, name, password_hash FROM users WHERE email = ?", (email,))
        ok = bool(row) and verify_password(req.password, row["password_hash"])
        if ok:
            token = _create_session(db, row["id"])
            db.run("DELETE FROM failed_logins WHERE email = ?", (email,))
    if not ok:
        _record_failure(email)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    _set_cookie(response, request, token)
    return UserOut(id=row["id"], email=row["email"], name=row["name"])


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with connect() as db:
            db.run("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    resp = Response(status_code=204)
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@router.get("/me", response_model=UserOut)
def me(request: Request) -> UserOut:
    user = user_for_token(request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return UserOut(id=user.id, email=user.email, name=user.name)


# --------------------------------------------------------------------------
# Middleware: every /api route except /api/auth/* needs a session; a missing
# database is reported clearly on every route (including /api/auth/*).
# --------------------------------------------------------------------------
async def require_session(request: Request, call_next):
    path = request.url.path
    try:
        if path.startswith("/api/") and not path.startswith("/api/auth/") and request.method != "OPTIONS":
            user = user_for_token(request.cookies.get(COOKIE_NAME))
            if not user:
                return JSONResponse({"detail": "Sign in to continue."}, status_code=401)
            request.state.user = user
        return await call_next(request)
    except DatabaseNotConfigured as e:
        return JSONResponse({"detail": str(e)}, status_code=503)
