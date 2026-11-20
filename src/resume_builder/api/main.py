from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

from ..models.resume import ResumeData
from ..ai.orchestrator import tailor_resume
from ..ai.backends import OllamaBackend, ClaudeBackend, LiteLLMBackend
from ..verification.fact_checker import check_tailored
from ..rendering.html_renderer import render_html, render_pdf
from ..rendering.docx_renderer import render_docx
from .studio import router as studio_router
from .auth import router as auth_router, require_session

app = FastAPI(title="Resume Builder API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Page-Count", "Content-Disposition"],
)
# Every /api route except /api/auth/* requires a signed-in session.
app.middleware("http")(require_session)
app.include_router(auth_router)
app.include_router(studio_router)


class TailorRequest(BaseModel):
    master: ResumeData
    job_description: str
    backend: str = "ollama"  # ollama | claude | litellm
    model: Optional[str] = None
    api_base: Optional[str] = None


class TailorResponse(BaseModel):
    tailored: ResumeData
    flags: list[str]


class PreviewResponse(BaseModel):
    html: str
    # Actual page count from the PDF renderer; None if the PDF engine is unavailable.
    pages: Optional[int] = None
    page_count_error: Optional[str] = None


CLOUD_BACKENDS = {"claude", "litellm"}


def _make_backend(name: str, model: Optional[str], api_base: Optional[str]):
    """Build a backend. API keys are never accepted from the client; they are
    read server-side from environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...)."""
    if name == "claude":
        return ClaudeBackend(model=model or "claude-sonnet-4-20250514")
    if name == "litellm":
        return LiteLLMBackend(model=model or "gpt-4o", api_base=api_base)
    if name == "ollama":
        return OllamaBackend(model=model or "qwen2.5:3b")
    raise HTTPException(status_code=400, detail=f"Unsupported backend '{name}'")


def _disclosure(name: str, model: Optional[str]) -> str:
    if name == "claude":
        return "Disclosed: Content sent externally to cloud provider (Anthropic Claude API)."
    if name == "litellm":
        return f"Disclosed: Content sent to cloud provider via LiteLLM ({model or 'gpt-4o'})."
    return "Private: Content processed locally on your machine via Ollama (no external cloud transmission)."


class EnhanceBulletRequest(BaseModel):
    bullet: str
    job_description: str
    backend: str = "ollama"  # ollama | claude | litellm
    model: Optional[str] = None
    api_base: Optional[str] = None


class EnhanceBulletResponse(BaseModel):
    original: str
    variations: list[str]
    backend_used: str
    disclosure: str


def _build_bullet_prompt(bullet: str, job_description: str) -> str:
    return f"""You are an executive resume writer. Enhance the following resume bullet point to better align with the target job description.

TARGET JOB DESCRIPTION:
{job_description}

ORIGINAL BULLET POINT:
{bullet}

STRICT CONSTRAINTS:
1. Provide exactly 2 or 3 distinct variations that use strong action verbs and professional phrasing.
2. DO NOT invent metrics, numbers, technologies, tools, dates, employers, or facts that are not present or implied in the original bullet.
3. If a metric spot is recommended where no metric exists, use "[ADD METRIC]".
4. Return ONLY a valid JSON array of strings containing the variations, e.g. ["variation 1", "variation 2", "variation 3"]. No markdown code fences, no extra commentary.
"""


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _introduces_new_numbers(variation: str, original: str) -> bool:
    """True if the variation contains a number (metric, date, count) absent from the original."""
    allowed = set(_NUMBER_RE.findall(original))
    return any(n not in allowed for n in _NUMBER_RE.findall(variation))


def _extract_variations(text: str, original: str = "") -> list[str]:
    import json
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array found in model response")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of variations")
    variations = [str(item).strip() for item in data if str(item).strip()]
    # Drop variations that fabricate metrics/dates not present in the original bullet
    variations = [v for v in variations if not _introduces_new_numbers(v, original)]
    if len(variations) < 2:
        raise ValueError(
            f"Expected at least 2 valid variations (without invented numbers), got {len(variations)}"
        )
    return variations[:3]


@app.post("/api/enhance-bullet", response_model=EnhanceBulletResponse)
def enhance_bullet(req: EnhanceBulletRequest):
    """Contextual enhancement: sends only the selected bullet and JD context to LLM."""
    if not req.bullet.strip():
        raise HTTPException(status_code=400, detail="Bullet text cannot be empty")

    backend = _make_backend(req.backend, req.model, req.api_base)
    disclosure = _disclosure(req.backend, req.model)

    prompt = _build_bullet_prompt(req.bullet, req.job_description)
    try:
        raw = backend.complete(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Enhancement failed: {e}")

    try:
        variations = _extract_variations(raw, req.bullet)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse enhanced variations: {e}")

    return EnhanceBulletResponse(
        original=req.bullet,
        variations=variations,
        backend_used=req.backend,
        disclosure=disclosure,
    )


@app.post("/api/tailor", response_model=TailorResponse)
def tailor(req: TailorRequest):
    if req.backend == "none":
        raise HTTPException(status_code=400, detail="Use /api/render for no-AI formatting")

    backend = _make_backend(req.backend, req.model, req.api_base)

    try:
        tailored = tailor_resume(req.master, req.job_description, backend)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Tailoring failed: {e}")

    checked = check_tailored(tailored, req.master)
    flags = [
        f"{f.value[:60]}…" for exp in checked.experience for f in exp.bullets
        if f.verification_status.value == "flagged"
    ]
    return TailorResponse(tailored=checked, flags=flags)


@app.post("/api/render/preview", response_model=PreviewResponse)
def preview(resume: ResumeData):
    """Format-only preview: renders HTML and computes page count without invoking an AI backend."""
    try:
        html = render_html(resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview render failed: {e}")
    # Page count comes from the real PDF renderer; never estimated from text length.
    try:
        _, pages = render_pdf(resume)
        return PreviewResponse(html=html, pages=pages)
    except Exception as e:
        return PreviewResponse(html=html, pages=None, page_count_error=str(e))


@app.post("/api/render/pdf")
def pdf(resume: ResumeData):
    try:
        data, pages = render_pdf(resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF render failed: {e}")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=Resume.pdf",
            "X-Page-Count": str(pages),
        },
    )


@app.post("/api/render/docx")
def docx(resume: ResumeData):
    try:
        data = render_docx(resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX render failed: {e}")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=Resume.docx"},
    )


@app.post("/api/import/docx")
async def import_docx(file: UploadFile = File(...)):
    """Extract text from uploaded .docx file as HTML for field mapping."""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    try:
        import mammoth
        content = await file.read()
        import io
        result = mammoth.convert_to_html(io.BytesIO(content))
        return {"html": result.value, "messages": result.messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse DOCX: {e}")


# ---------------------------------------------------------------------------
# Serve the built web UI (web/dist) from the same server, so one process and
# one URL is enough. Must be mounted last so /api/* routes take precedence.
# ---------------------------------------------------------------------------
def _web_dist() -> Path:
    env = os.environ.get("RESUME_WEB_DIST")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "web" / "dist"


if (_web_dist() / "index.html").is_file():
    app.mount("/", StaticFiles(directory=_web_dist(), html=True), name="web")
