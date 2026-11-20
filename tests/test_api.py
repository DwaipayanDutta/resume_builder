import io
import json
import pytest
from fastapi.testclient import TestClient
from helpers import authed_client
from unittest.mock import patch, MagicMock

from resume_builder.api.main import app
from resume_builder.models.resume import (
    ResumeData,
    ContactInfo,
    VerifiableField,
    Experience,
    Education,
)

client = authed_client()


def _weasyprint_available() -> bool:
    """WeasyPrint needs native Pango/GTK libraries; skip real-PDF tests without them."""
    try:
        from weasyprint import HTML
        HTML(string="<p>x</p>").render()
        return True
    except Exception:
        return False


requires_weasyprint = pytest.mark.skipif(
    not _weasyprint_available(), reason="WeasyPrint native libraries (Pango) not installed"
)


@pytest.fixture
def sample_resume():
    return ResumeData(
        contact=ContactInfo(
            name=VerifiableField(value="Alex Morgan"),
            email=VerifiableField(value="alex@example.com"),
            phone=VerifiableField(value="+1 555-0100"),
            location=VerifiableField(value="San Francisco, CA"),
        ),
        summary=VerifiableField(value="Senior Software Engineer with 8 years experience."),
        experience=[
            Experience(
                company=VerifiableField(value="TechCorp"),
                title=VerifiableField(value="Lead Engineer"),
                start_date=VerifiableField(value="01/2021"),
                end_date=VerifiableField(value="Present"),
                bullets=[
                    VerifiableField(value="Led migration to microservices architecture."),
                    VerifiableField(value="Reduced cloud infrastructure costs by 20%."),
                ],
            )
        ],
        education=[
            Education(
                institution=VerifiableField(value="UC Berkeley"),
                degree=VerifiableField(value="B.S. in Computer Science"),
            )
        ],
        skills=[
            VerifiableField(value="Python"),
            VerifiableField(value="FastAPI"),
            VerifiableField(value="Docker"),
        ],
    )


def test_tailor_endpoint_success(sample_resume):
    mock_tailored_json = sample_resume.model_dump_json()

    with patch("resume_builder.api.main.tailor_resume") as mock_tailor:
        mock_tailor.return_value = sample_resume
        payload = {
            "master": sample_resume.model_dump(),
            "job_description": "We are seeking a Lead Engineer with Python and FastAPI skills.",
            "backend": "ollama",
            "model": "qwen2.5:3b",
        }
        res = client.post("/api/tailor", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "tailored" in data
        assert "flags" in data
        assert data["tailored"]["contact"]["name"]["value"] == "Alex Morgan"


def test_tailor_endpoint_rejects_none_backend(sample_resume):
    payload = {
        "master": sample_resume.model_dump(),
        "job_description": "Some job",
        "backend": "none",
    }
    res = client.post("/api/tailor", json=payload)
    assert res.status_code == 400
    assert "no-AI formatting" in res.json()["detail"]


def test_tailor_endpoint_invalid_backend(sample_resume):
    payload = {
        "master": sample_resume.model_dump(),
        "job_description": "Some job",
        "backend": "unknown_backend",
    }
    res = client.post("/api/tailor", json=payload)
    assert res.status_code == 400
    assert "Unsupported backend" in res.json()["detail"]


def test_tailor_endpoint_backend_failure(sample_resume):
    with patch("resume_builder.api.main.tailor_resume", side_effect=RuntimeError("Connection refused")):
        payload = {
            "master": sample_resume.model_dump(),
            "job_description": "Some job",
            "backend": "ollama",
        }
        res = client.post("/api/tailor", json=payload)
        assert res.status_code == 502
        assert "Tailoring failed: Connection refused" in res.json()["detail"]


@requires_weasyprint
def test_render_pdf_endpoint(sample_resume):
    res = client.post("/api/render/pdf", json=sample_resume.model_dump())
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=Resume.pdf" in res.headers["content-disposition"]
    assert "x-page-count" in res.headers
    assert int(res.headers["x-page-count"]) >= 1
    assert res.content.startswith(b"%PDF")


def test_render_pdf_error_handling(sample_resume):
    with patch("resume_builder.api.main.render_pdf", side_effect=RuntimeError("WeasyPrint crash")):
        res = client.post("/api/render/pdf", json=sample_resume.model_dump())
        assert res.status_code == 500
        assert "PDF render failed: WeasyPrint crash" in res.json()["detail"]


def test_render_docx_endpoint(sample_resume):
    res = client.post("/api/render/docx", json=sample_resume.model_dump())
    assert res.status_code == 200
    assert "vnd.openxmlformats-officedocument.wordprocessingml.document" in res.headers["content-type"]
    assert "attachment; filename=Resume.docx" in res.headers["content-disposition"]
    assert len(res.content) > 1000


def test_render_docx_error_handling(sample_resume):
    with patch("resume_builder.api.main.render_docx", side_effect=RuntimeError("DOCX corrupt")):
        res = client.post("/api/render/docx", json=sample_resume.model_dump())
        assert res.status_code == 500
        assert "DOCX render failed: DOCX corrupt" in res.json()["detail"]


def test_render_pdf_endpoint_mocked(sample_resume):
    with patch("resume_builder.api.main.render_pdf", return_value=(b"%PDF-1.7 fake", 3)):
        res = client.post("/api/render/pdf", json=sample_resume.model_dump())
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.headers["x-page-count"] == "3"
    assert res.content.startswith(b"%PDF")


def test_render_preview_uses_renderer_page_count(sample_resume):
    with patch("resume_builder.api.main.render_pdf", return_value=(b"%PDF", 3)):
        res = client.post("/api/render/preview", json=sample_resume.model_dump())
    assert res.status_code == 200
    assert res.json()["pages"] == 3


@requires_weasyprint
def test_render_preview_endpoint(sample_resume):
    res = client.post("/api/render/preview", json=sample_resume.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert "html" in data
    assert "pages" in data
    assert "Alex Morgan" in data["html"]
    assert data["pages"] >= 1
    assert data["page_count_error"] is None


def test_import_docx_rejects_non_docx():
    files = {"file": ("test.txt", b"plain text content", "text/plain")}
    res = client.post("/api/import/docx", files=files)
    assert res.status_code == 400
    assert "Only .docx files are supported" in res.json()["detail"]


def test_enhance_bullet_success_ollama():
    mock_resp = '["Architected and deployed a microservices architecture to reduce latency.", "Led distributed microservices migration improving system scalability."]'
    with patch("resume_builder.api.main.OllamaBackend.complete", return_value=mock_resp):
        payload = {
            "bullet": "Led migration to microservices architecture.",
            "job_description": "Looking for a Lead Engineer who optimizes microservices latency.",
            "backend": "ollama",
        }
        res = client.post("/api/enhance-bullet", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert len(data["variations"]) == 2
        assert "reduce latency" in data["variations"][0]
        assert "Private: Content processed locally" in data["disclosure"]


def test_enhance_bullet_success_claude():
    mock_resp = '```json\n["Spearheaded cloud cost optimization saving 20% annually.", "Executed FinOps initiatives to reduce infrastructure overhead."]\n```'
    with patch("resume_builder.api.main.ClaudeBackend.complete", return_value=mock_resp):
        payload = {
            "bullet": "Reduced cloud infrastructure costs by 20%.",
            "job_description": "Need FinOps and cost optimization expert.",
            "backend": "claude",
        }
        res = client.post("/api/enhance-bullet", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert len(data["variations"]) == 2
        assert "saving 20% annually" in data["variations"][0]
        assert "Disclosed: Content sent externally" in data["disclosure"]


def test_enhance_bullet_rejects_empty():
    res = client.post("/api/enhance-bullet", json={"bullet": "   ", "job_description": "JD"})
    assert res.status_code == 400
    assert "Bullet text cannot be empty" in res.json()["detail"]


def test_enhance_bullet_unsupported_backend():
    res = client.post("/api/enhance-bullet", json={"bullet": "Did something", "job_description": "JD", "backend": "unknown"})
    assert res.status_code == 400
    assert "Unsupported backend" in res.json()["detail"]


def test_enhance_bullet_backend_failure():
    with patch("resume_builder.api.main.OllamaBackend.complete", side_effect=RuntimeError("Ollama offline")):
        res = client.post("/api/enhance-bullet", json={"bullet": "Did something", "job_description": "JD", "backend": "ollama"})
        assert res.status_code == 502
        assert "Enhancement failed: Ollama offline" in res.json()["detail"]


def test_enhance_bullet_invalid_output():
    with patch("resume_builder.api.main.OllamaBackend.complete", return_value="Here is your bullet: Improved performance."):
        res = client.post("/api/enhance-bullet", json={"bullet": "Did something", "job_description": "JD", "backend": "ollama"})
        assert res.status_code == 502
        assert "Failed to parse enhanced variations" in res.json()["detail"]



# ---------------------------------------------------------------------------
# Fabricated metrics, server-side secrets, honest page count, schema
# ---------------------------------------------------------------------------

def test_enhance_bullet_drops_variations_with_invented_numbers():
    mock_resp = (
        '["Architected microservices reducing latency by 35%.", '
        '"Led the migration to a microservices architecture.", '
        '"Drove a company-wide microservices migration."]'
    )
    with patch("resume_builder.api.main.OllamaBackend.complete", return_value=mock_resp):
        res = client.post("/api/enhance-bullet", json={
            "bullet": "Led migration to microservices architecture.",
            "job_description": "Lead Engineer", "backend": "ollama",
        })
    assert res.status_code == 200
    variations = res.json()["variations"]
    assert len(variations) == 2
    assert all("35%" not in v for v in variations)


def test_enhance_bullet_keeps_numbers_present_in_original():
    mock_resp = '["Cut cloud infrastructure costs by 20%.", "Lowered cloud spend by 20% via rightsizing."]'
    with patch("resume_builder.api.main.OllamaBackend.complete", return_value=mock_resp):
        res = client.post("/api/enhance-bullet", json={
            "bullet": "Reduced cloud infrastructure costs by 20%.",
            "job_description": "FinOps", "backend": "ollama",
        })
    assert res.status_code == 200
    assert len(res.json()["variations"]) == 2


def test_enhance_bullet_rejects_when_all_variations_fabricate_metrics():
    mock_resp = '["Saved $2M annually.", "Grew revenue 40%.", "Hired 12 engineers."]'
    with patch("resume_builder.api.main.OllamaBackend.complete", return_value=mock_resp):
        res = client.post("/api/enhance-bullet", json={
            "bullet": "Improved team processes.", "job_description": "JD", "backend": "ollama",
        })
    assert res.status_code == 502
    assert "invented numbers" in res.json()["detail"]


def test_enhance_bullet_sends_only_bullet_and_jd():
    captured = {}

    def fake_complete(self, prompt):
        captured["prompt"] = prompt
        return '["Led a team migration.", "Directed the migration effort."]'

    with patch("resume_builder.api.main.OllamaBackend.complete", fake_complete):
        res = client.post("/api/enhance-bullet", json={
            "bullet": "Led migration.", "job_description": "Need a Kubernetes lead.",
            "backend": "ollama",
        })
    assert res.status_code == 200
    assert "Led migration." in captured["prompt"]
    assert "Need a Kubernetes lead." in captured["prompt"]


def test_client_supplied_api_key_is_ignored():
    """Secrets stay server-side: an api_key in the request body is never forwarded."""
    with patch("resume_builder.api.main.LiteLLMBackend") as mock_cls:
        mock_cls.return_value.complete.return_value = '["Led a migration.", "Directed a migration."]'
        res = client.post("/api/enhance-bullet", json={
            "bullet": "Led migration.", "job_description": "JD",
            "backend": "litellm", "api_key": "sk-should-not-be-used",
        })
    assert res.status_code == 200
    _, kwargs = mock_cls.call_args
    assert "api_key" not in kwargs
    assert "Disclosed" in res.json()["disclosure"]


def test_render_preview_reports_missing_pdf_engine(sample_resume):
    with patch("resume_builder.api.main.render_pdf", side_effect=RuntimeError("weasyprint missing")):
        res = client.post("/api/render/preview", json=sample_resume.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert "Alex Morgan" in data["html"]
    assert data["pages"] is None
    assert "weasyprint missing" in data["page_count_error"]


def test_render_preview_html_error(sample_resume):
    with patch("resume_builder.api.main.render_html", side_effect=RuntimeError("bad template")):
        res = client.post("/api/render/preview", json=sample_resume.model_dump())
    assert res.status_code == 500
    assert "Preview render failed: bad template" in res.json()["detail"]


def test_render_preview_escapes_user_content(sample_resume):
    sample_resume.summary = VerifiableField(value="<script>alert(1)</script>")
    res = client.post("/api/render/preview", json=sample_resume.model_dump())
    assert res.status_code == 200
    html = res.json()["html"]
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_preview_does_not_call_ai(sample_resume):
    with patch("resume_builder.api.main.tailor_resume") as t, \
         patch("resume_builder.api.main.OllamaBackend.complete") as o:
        client.post("/api/render/preview", json=sample_resume.model_dump())
    t.assert_not_called()
    o.assert_not_called()


def test_preview_respects_section_order_and_custom_sections(sample_resume):
    payload = sample_resume.model_dump()
    payload["section_order"] = ["skills", "experience", "summary", "projects", "education", "certifications"]
    payload["certifications"] = [{"value": "AWS Solutions Architect"}]
    payload["custom_sections"] = [{"name": "Publications", "items": [{"value": "Paper A"}]}]
    res = client.post("/api/render/preview", json=payload)
    assert res.status_code == 200
    html = res.json()["html"]
    assert html.index("<h2>Skills</h2>") < html.index("<h2>Work Experience</h2>")
    assert "AWS Solutions Architect" in html
    assert "Publications" in html and "Paper A" in html


def test_render_docx_includes_all_sections(sample_resume):
    import docx as _docx
    payload = sample_resume.model_dump()
    payload["certifications"] = [{"value": "CKA"}]
    payload["projects"] = [{"name": {"value": "OSS Tool"}, "bullets": [{"value": "Built CLI"}]}]
    res = client.post("/api/render/docx", json=payload)
    assert res.status_code == 200
    text = "\n".join(p.text for p in _docx.Document(io.BytesIO(res.content)).paragraphs)
    for expected in ("CKA", "OSS Tool", "Built CLI", "Python"):
        assert expected in text


def test_render_rejects_invalid_payload():
    res = client.post("/api/render/pdf", json={"experience": [{"bullets": "not-a-list"}]})
    assert res.status_code == 422


def test_claude_backend_works_without_sdk(monkeypatch):
    """The slim hosted build has no `anthropic` package: ClaudeBackend falls back to HTTPS."""
    import builtins
    from resume_builder.ai.backends import ClaudeBackend
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    real_import = builtins.__import__

    def no_anthropic(name, *a, **k):
        if name == "anthropic":
            raise ImportError("not installed")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_anthropic)
    with patch("resume_builder.tailor.call_claude", return_value="ok via https") as call:
        assert ClaudeBackend(model="claude-x").complete("hi") == "ok via https"
    assert call.call_args.args[:3] == ("hi", "claude-x", "sk-test")
