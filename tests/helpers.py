import uuid

from fastapi.testclient import TestClient

from resume_builder.api.main import app

PASSWORD = "correct horse battery"


def authed_client(name: str = "Test User") -> TestClient:
    """A TestClient that has registered a fresh account and holds its session cookie."""
    client = TestClient(app)
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    res = client.post("/api/auth/register", json={"name": name, "email": email, "password": PASSWORD})
    assert res.status_code == 201, res.text
    client.email = email
    return client
