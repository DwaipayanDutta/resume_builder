import io
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from resume_builder.api.main import app
from resume_builder.models.resume import (
    ResumeData,
    ContactInfo,
    VerifiableField,
    Experience,
    Education,
)

client = TestClient(app)


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


def test_render_preview_endpoint(sample_resume):
    res = client.post("/api/render/preview", json=sample_resume.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert "html" in data
    assert "pages" in data
    assert "Alex Morgan" in data["html"]
    assert data["pages"] >= 1


def test_import_docx_rejects_non_docx():
    files = {"file": ("test.txt", b"plain text content", "text/plain")}
    res = client.post("/api/import/docx", files=files)
    assert res.status_code == 400
    assert "Only .docx files are supported" in res.json()["detail"]


def test_enhance_bullet_success_ollama():
    mock_resp = '["Architected and deployed microservices reducing latency by 35%.", "Led distributed microservices migration improving system scalability."]'
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
        assert "latency by 35%" in data["variations"][0]
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
        assert res.status_code == 500
        assert "Failed to parse enhanced variations" in res.json()["detail"]

