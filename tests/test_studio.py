from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from helpers import authed_client

from resume_builder.api import studio
from resume_builder.api.main import app

client = authed_client()
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "New Resume.txt"
CV_TEXT = EXAMPLE.read_text(encoding="utf-8-sig")
JD = "We are hiring a Senior Program Manager to lead software delivery. " * 5


def _upload(text=CV_TEXT, name="resume.txt"):
    return {"resume": (name, text.encode("utf-8"), "text/plain")}


# ---------------------------------------------------------------- config
def test_config_reports_backends_and_defaults(monkeypatch):
    monkeypatch.setenv("RESUME_BACKEND", "litellm")
    monkeypatch.setenv("RESUME_MODEL", "anthropic/claude-sonnet-5-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    data = client.get("/api/studio/config").json()
    assert data["default_backend"] == "litellm"
    assert data["default_model"] == "anthropic/claude-sonnet-5-5"
    ids = {b["id"]: b for b in data["backends"]}
    # Claude is reached through LiteLLM; no separate Claude entry is offered
    assert list(ids) == ["qwen", "litellm"]
    assert ids["litellm"]["configured"] is True and ids["litellm"]["cloud"] is True
    assert ids["qwen"]["cloud"] is False
    assert "sk-test" not in str(data)  # never leak secrets


# ---------------------------------------------------------------- build: format only
def test_build_format_only_produces_downloadable_pdf_and_docx():
    res = client.post("/api/studio/build", files=_upload(), data={"mode": "format", "basename": "My CV"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mode"] == "format" and body["backend"] is None
    assert body["pages"] >= 1 and body["fits_two_pages"] is True
    assert "no AI" in body["disclosure"]
    assert any("DOCX OK" in v for v in body["verification"])

    pdf = client.get(body["files"]["pdf"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert "inline" in pdf.headers["content-disposition"]
    pdf_dl = client.get(body["files"]["pdf"] + "?download=1")
    assert "attachment" in pdf_dl.headers["content-disposition"]
    assert "My%20CV.pdf" in pdf_dl.headers["content-disposition"]
    docx = client.get(body["files"]["docx"])
    assert docx.status_code == 200 and docx.content[:2] == b"PK"


def test_build_rejects_non_txt():
    res = client.post("/api/studio/build", files=_upload(name="resume.pdf"), data={"mode": "format"})
    assert res.status_code == 400
    assert ".txt" in res.json()["detail"]


def test_build_rejects_wrong_layout():
    res = client.post("/api/studio/build", files=_upload("just some words\nno sections"),
                      data={"mode": "format"})
    assert res.status_code == 422
    assert "layout" in res.json()["detail"]


# ---------------------------------------------------------------- build: tailor
def _fake_runner(output):
    return lambda backend, model=None, *a, **k: ((lambda prompt: output), model or "fake-model")


def test_build_tailor_with_mocked_backend():
    fake = "BEGIN_CV\n" + CV_TEXT.replace("Introduced", "Introduced [ADD METRIC]", 1) + "\nEND_CV"
    with patch.object(studio.tl, "make_runner", _fake_runner(fake)):
        res = client.post("/api/studio/build", files=_upload(), data={
            "mode": "tailor", "job_title": "Senior Program Manager", "jd_text": JD,
            "backend": "qwen",
        })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["backend"] == "qwen" and body["model"] == "fake-model"
    assert "locally" in body["disclosure"]
    assert body["placeholders"] == 1
    assert any("[ADD METRIC]" in w for w in body["warnings"])
    assert client.get(body["files"]["txt"]).text.count("[ADD METRIC]") == 1


def test_build_tailor_cloud_disclosure_and_report():
    with patch.object(studio.tl, "make_runner", _fake_runner("BEGIN_CV\n" + CV_TEXT + "\nEND_CV")):
        res = client.post("/api/studio/build", files=_upload(), data={
            "mode": "tailor", "job_title": "PM", "jd_text": JD, "backend": "claude",
            "include_report": "true",
        })
    body = res.json()
    assert "sent to Claude API" in body["disclosure"]
    assert "report" in body["files"]


def test_build_tailor_flags_changed_employer():
    altered = CV_TEXT.replace("Northwind Systems", "Contoso Ltd")
    with patch.object(studio.tl, "make_runner", _fake_runner("BEGIN_CV\n" + altered + "\nEND_CV")):
        res = client.post("/api/studio/build", files=_upload(), data={
            "mode": "tailor", "job_title": "PM", "jd_text": JD, "backend": "qwen"})
    warnings = res.json()["warnings"]
    assert any("Northwind Systems" in w for w in warnings)
    assert any("Contoso Ltd" in w for w in warnings)


def test_build_tailor_backend_failure_is_explicit():
    def boom(prompt):
        raise RuntimeError("Could not reach Ollama")
    with patch.object(studio.tl, "make_runner", lambda *a, **k: (boom, "m")):
        res = client.post("/api/studio/build", files=_upload(), data={
            "mode": "tailor", "job_title": "PM", "jd_text": JD, "backend": "qwen"})
    assert res.status_code == 502
    assert "Could not reach Ollama" in res.json()["detail"]


def test_build_tailor_requires_jd_and_title():
    res = client.post("/api/studio/build", files=_upload(), data={
        "mode": "tailor", "job_title": "PM", "jd_text": "", "backend": "qwen"})
    assert res.status_code == 400
    res = client.post("/api/studio/build", files=_upload(), data={
        "mode": "tailor", "job_title": "", "jd_text": JD, "backend": "qwen"})
    assert res.status_code == 400


def test_build_tailor_missing_key_is_reported(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    res = client.post("/api/studio/build", files=_upload(), data={
        "mode": "tailor", "job_title": "PM", "jd_text": JD, "backend": "claude"})
    assert res.status_code == 400
    assert "ANTHROPIC_API_KEY" in res.json()["detail"]


def test_download_rejects_bad_ids():
    assert client.get("/api/studio/files/../../etc/pdf").status_code == 404
    assert client.get("/api/studio/files/" + "a" * 32 + "/secret").status_code == 404
    assert client.get("/api/studio/files/" + "a" * 32 + "/pdf").status_code == 404


# ---------------------------------------------------------------- JD from link
JSONLD_PAGE = """<html><head><title>Careers</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"JobPosting",
"title":"Senior Program Manager","hiringOrganization":{"@type":"Organization","name":"Acme"},
"description":"<p>Lead delivery of software programs.</p><ul><li>Own roadmaps</li><li>Manage vendors</li></ul>%s"}
</script></head><body>nav junk</body></html>""" % ("<p>More detail.</p>" * 20)


def test_extract_job_description_prefers_json_ld():
    info = studio.extract_job_description(JSONLD_PAGE)
    assert info["source"] == "json-ld"
    assert info["title"] == "Senior Program Manager"
    assert info["company"] == "Acme"
    assert "- Own roadmaps" in info["text"]
    assert "nav junk" not in info["text"]


def test_extract_job_description_falls_back_to_page_text():
    html = "<html><head><title>Job</title><script>var x=1</script></head><body><main><h1>Engineer</h1><p>Build things.</p></main></body></html>"
    info = studio.extract_job_description(html)
    assert info["source"] == "page-text"
    assert "Build things." in info["text"] and "var x" not in info["text"]


def test_jd_from_url_success():
    with patch.object(studio, "_fetch_html", return_value=JSONLD_PAGE):
        res = client.post("/api/studio/jd-from-url", json={"url": "https://jobs.example.com/1"})
    assert res.status_code == 200
    assert res.json()["company"] == "Acme"


def test_jd_from_url_too_little_text():
    with patch.object(studio, "_fetch_html", return_value="<html><body>Sign in</body></html>"):
        res = client.post("/api/studio/jd-from-url", json={"url": "https://www.linkedin.com/jobs/view/1"})
    assert res.status_code == 422
    assert "Paste the description" in res.json()["detail"]


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com/x", "http://127.0.0.1:8001/api/studio/config",
    "http://localhost/", "http://10.0.0.5/", "http://169.254.169.254/latest/meta-data", "not a url",
])
def test_jd_from_url_blocks_unsafe_targets(url):
    with pytest.raises(HTTPException) as exc:
        studio._assert_public_http_url(url)
    assert exc.value.status_code == 400


def test_config_ignores_unlisted_default_backend(monkeypatch):
    monkeypatch.setenv("RESUME_BACKEND", "claude")
    assert client.get("/api/studio/config").json()["default_backend"] is None


def test_build_litellm_requires_model(monkeypatch):
    monkeypatch.delenv("RESUME_MODEL", raising=False)
    res = client.post("/api/studio/build", files=_upload(), data={
        "mode": "tailor", "job_title": "PM", "jd_text": JD, "backend": "litellm"})
    assert res.status_code == 400
    assert "anthropic/claude-sonnet-5-5" in res.json()["detail"]


def test_build_litellm_claude_model_disclosure():
    with patch.object(studio.tl, "make_runner", _fake_runner("BEGIN_CV\n" + CV_TEXT + "\nEND_CV")):
        res = client.post("/api/studio/build", files=_upload(), data={
            "mode": "tailor", "job_title": "PM", "jd_text": JD, "backend": "litellm",
            "model": "anthropic/claude-sonnet-5-5"})
    assert res.status_code == 200
    body = res.json()
    assert body["model"] == "anthropic/claude-sonnet-5-5"
    assert "sent to Any provider via LiteLLM" in body["disclosure"]
