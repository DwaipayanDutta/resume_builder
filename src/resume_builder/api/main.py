from __future__ import annotations
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from ..models.resume import ResumeData, Source
from ..ai.orchestrator import tailor_resume
from ..ai.backends import OllamaBackend, ClaudeBackend, LiteLLMBackend, NoAIBackend
from ..verification.fact_checker import check_tailored
from ..rendering.html_renderer import render_html, render_pdf
from ..rendering.docx_renderer import render_docx

app = FastAPI(title="Resume Builder API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Page-Count", "Content-Disposition"],
)


class TailorRequest(BaseModel):
    master: ResumeData
    job_description: str
    backend: str = "ollama"  # ollama | claude | litellm | none
    model: str | None = None
    api_key: str | None = None
    api_base: str | None = None


class TailorResponse(BaseModel):
    tailored: ResumeData
    flags: list[str]


class PreviewResponse(BaseModel):
    html: str
    pages: int


class EnhanceBulletRequest(BaseModel):
    bullet: str
    job_description: str
    backend: str = "ollama"  # ollama | claude | litellm
    model: str | None = None
    api_key: str | None = None
    api_base: str | None = None


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


def _extract_variations(text: str) -> list[str]:
    import re, json
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
    if len(variations) < 2:
        raise ValueError(f"Expected at least 2 variations, but received {len(variations)}")
    return variations[:3]


@app.post("/api/enhance-bullet", response_model=EnhanceBulletResponse)
def enhance_bullet(req: EnhanceBulletRequest):
    """Contextual enhancement: sends only the selected bullet and JD context to LLM."""
    if not req.bullet.strip():
        raise HTTPException(status_code=400, detail="Bullet text cannot be empty")

    if req.backend == "claude":
        backend = ClaudeBackend(model=req.model or "claude-sonnet-4-20250514")
        disclosure = "Disclosed: Content sent externally to cloud provider (Anthropic Claude API)."
    elif req.backend == "litellm":
        backend = LiteLLMBackend(model=req.model or "gpt-4o", api_key=req.api_key, api_base=req.api_base)
        disclosure = f"Disclosed: Content sent to cloud provider ({req.model or 'gpt-4o'})."
    elif req.backend == "ollama":
        backend = OllamaBackend(model=req.model or "qwen2.5:3b")
        disclosure = "Private: Content processed locally on your machine via Ollama (no external cloud transmission)."
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported backend '{req.backend}'")

    prompt = _build_bullet_prompt(req.bullet, req.job_description)
    try:
        raw = backend.complete(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Enhancement failed: {e}")

    try:
        variations = _extract_variations(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse enhanced variations: {e}")

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

    if req.backend == "claude":
        backend = ClaudeBackend(model=req.model or "claude-sonnet-4-20250514")
    elif req.backend == "litellm":
        backend = LiteLLMBackend(model=req.model or "gpt-4o", api_key=req.api_key, api_base=req.api_base)
    elif req.backend == "ollama":
        backend = OllamaBackend(model=req.model or "qwen2.5:3b")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported backend '{req.backend}'")

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
        # Attempt to determine page count via WeasyPrint, falling back to 1 if WeasyPrint fails
        pages = 1
        try:
            _, pages = render_pdf(resume)
        except Exception:
            pass
        return PreviewResponse(html=html, pages=pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview render failed: {e}")


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
