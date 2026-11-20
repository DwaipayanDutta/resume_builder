"""Accounts for Resume Studio: register, sign in, sign out, current user.

* Users and sessions live in a local SQLite file (``RESUME_DB_PATH``, default
  ``~/.resume_studio/studio.db``); only the standard library is used.
* Passwords are stored as salted scrypt hashes, never in plain text.
* Sessions are random tokens sent as an HttpOnly, SameSite=Lax cookie. The
  database stores only a SHA-256 of each token, so a copied DB can't be used
  to hijack sessions.
* ``require_session`` (installed as middleware in ``main.py``) protects every
  ``/api/*`` route except ``/api/auth/*``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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

_lock = threading.Lock()
_failed: dict[str, list[float]] = {}


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------
def db_path() -> Path:
    env = os.environ.get("RESUME_DB_PATH")
    return Path(env) if env else Path.home() / ".resume_studio" / "studio.db"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL
        );
        """
    )
    return conn


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


def _create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    conn.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)",
                 (_token_hash(token), user_id, now, now + SESSION_TTL))
    conn.commit()
    return token


def user_for_token(token: Optional[str]) -> Optional[User]:
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT u.id, u.email, u.name FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (_token_hash(token), time.time()),
        ).fetchone()
    return User(row["id"], row["email"], row["name"]) if row else None


def _set_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_TTL, httponly=True, samesite="lax",
        secure=request.url.scheme == "https", path="/",
    )


# --------------------------------------------------------------------------
# Brute-force throttle (per email, in memory)
# --------------------------------------------------------------------------
def _too_many_failures(email: str) -> bool:
    now = time.time()
    with _lock:
        recent = [t for t in _failed.get(email, []) if now - t < FAILED_WINDOW]
        _failed[email] = recent
        return len(recent) >= MAX_FAILED_LOGINS


def _record_failure(email: str) -> None:
    with _lock:
        _failed.setdefault(email, []).append(time.time())


def _clear_failures(email: str) -> None:
    with _lock:
        _failed.pop(email, None)


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
    with _connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (email, name, hash_password(req.password), time.time()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")
        user_id = cur.lastrowid
        token = _create_session(conn, user_id)
    _set_cookie(response, request, token)
    return UserOut(id=user_id, email=email, name=name)


@router.post("/login", response_model=UserOut)
def login(req: LoginRequest, request: Request, response: Response) -> UserOut:
    email = (req.email or "").strip().lower()
    if _too_many_failures(email):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Wait 15 minutes and try again.")
    with _connect() as conn:
        row = conn.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?",
                           (email,)).fetchone()
        if not row or not verify_password(req.password, row["password_hash"]):
            _record_failure(email)
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        token = _create_session(conn, row["id"])
    _clear_failures(email)
    _set_cookie(response, request, token)
    return UserOut(id=row["id"], email=row["email"], name=row["name"])


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with _connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
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
# Middleware: every /api route except /api/auth/* needs a session
# --------------------------------------------------------------------------
async def require_session(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/auth/") and request.method != "OPTIONS":
        user = user_for_token(request.cookies.get(COOKIE_NAME))
        if not user:
            return JSONResponse({"detail": "Sign in to continue."}, status_code=401)
        request.state.user = user
    return await call_next(request)
