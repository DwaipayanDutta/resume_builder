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
