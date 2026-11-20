import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from helpers import PASSWORD, authed_client
from resume_builder.api import auth
from resume_builder.api.main import app

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "New Resume.txt"


def _anon():
    return TestClient(app)


def test_api_requires_sign_in():
    c = _anon()
    for method, url in [("get", "/api/studio/config"), ("post", "/api/render/preview"),
                        ("post", "/api/enhance-bullet"), ("post", "/api/studio/build")]:
        res = getattr(c, method)(url)
        assert res.status_code == 401, url
        assert res.json()["detail"] == "Sign in to continue."
    assert c.get("/api/auth/me").status_code == 401


def test_register_signs_in_and_sets_secure_cookie():
    c = _anon()
    res = c.post("/api/auth/register", json={"name": "Alex", "email": "Alex.Reg@Example.com", "password": PASSWORD})
    assert res.status_code == 201
    assert res.json()["email"] == "alex.reg@example.com"
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert c.get("/api/auth/me").json()["name"] == "Alex"
    assert c.get("/api/studio/config").status_code == 200


def test_register_validation_and_duplicates():
    c = _anon()
    bad = [
        {"name": "", "email": "a@example.com", "password": PASSWORD},
        {"name": "A", "email": "not-an-email", "password": PASSWORD},
        {"name": "A", "email": "a2@example.com", "password": "short"},
    ]
    for body in bad:
        assert c.post("/api/auth/register", json=body).status_code == 422
    first = authed_client()
    dup = _anon().post("/api/auth/register", json={"name": "B", "email": first.email.upper(), "password": PASSWORD})
    assert dup.status_code == 409


def test_login_logout_cycle():
    c = authed_client()
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401
    assert c.get("/api/studio/config").status_code == 401

    wrong = c.post("/api/auth/login", json={"email": c.email, "password": "wrong password"})
    assert wrong.status_code == 401 and wrong.json()["detail"] == "Incorrect email or password."
    unknown = c.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert unknown.json()["detail"] == wrong.json()["detail"]  # no account enumeration

    ok = c.post("/api/auth/login", json={"email": c.email.upper(), "password": PASSWORD})
    assert ok.status_code == 200
    assert c.get("/api/studio/config").status_code == 200


def test_logout_invalidates_the_token_server_side():
    c = authed_client()
    token = c.cookies.get(auth.COOKIE_NAME)
    c.post("/api/auth/logout")
    replay = _anon()
    replay.cookies.set(auth.COOKIE_NAME, token)
    assert replay.get("/api/auth/me").status_code == 401


def test_login_is_throttled_after_repeated_failures():
    c = authed_client()
    for _ in range(auth.MAX_FAILED_LOGINS):
        assert c.post("/api/auth/login", json={"email": c.email, "password": "nope-nope"}).status_code == 401
    res = c.post("/api/auth/login", json={"email": c.email, "password": PASSWORD})
    assert res.status_code == 429


def test_passwords_and_tokens_are_not_stored_in_plain_text():
    c = authed_client()
    token = c.cookies.get(auth.COOKIE_NAME)
    conn = sqlite3.connect(auth.db_path())
    pw_hash = conn.execute("SELECT password_hash FROM users WHERE email = ?", (c.email,)).fetchone()[0]
    tokens = [r[0] for r in conn.execute("SELECT token_hash FROM sessions")]
    conn.close()
    assert pw_hash.startswith("scrypt$") and PASSWORD not in pw_hash
    assert token not in tokens
    assert auth.verify_password(PASSWORD, pw_hash) and not auth.verify_password("x", pw_hash)


def test_builds_are_private_to_their_owner():
    alice, bob = authed_client("Alice"), authed_client("Bob")
    res = alice.post("/api/studio/build", data={"mode": "format"},
                     files={"resume": ("r.txt", EXAMPLE.read_bytes(), "text/plain")})
    assert res.status_code == 200
    pdf_url = res.json()["files"]["pdf"]
    assert alice.get(pdf_url).status_code == 200
    assert bob.get(pdf_url).status_code == 404
    assert _anon().get(pdf_url).status_code == 401


def test_static_ui_is_public_so_the_login_page_loads():
    res = _anon().get("/")
    assert res.status_code in (200, 404)  # 404 only if the UI hasn't been built
