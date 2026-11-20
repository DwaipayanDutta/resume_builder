from __future__ import annotations
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from ..models.resume import ResumeData, Source
from ..ai.orchestrator import tailor_resume, NoAIBackend
from ..ai.backends import OllamaBackend, ClaudeBackend
from ..verification.fact_checker import check_tailored
from ..rendering.html_renderer import render_pdf
from ..rendering.docx_renderer import render_docx

app = FastAPI(title="Resume Builder API")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


class TailorRequest(BaseModel):
    master: ResumeData
    job_description: str
    backend: str = "ollama"  # ollama | claude | none
    model: str | None = None


class TailorResponse(BaseModel):
    tailored: ResumeData
    flags: list[str]


@app.post("/api/tailor", response_model=TailorResponse)
def tailor(req: TailorRequest):
    if req.backend == "none":
        raise HTTPException(400, "Use /api/render for no-AI formatting")
    backend = (
        OllamaBackend(model=req.model or "qwen2.5:3b")
        if req.backend == "ollama"
        else ClaudeBackend(model=req.model or "claude-sonnet-4-20250514")
    )
    try:
        tailored = tailor_resume(req.master, req.job_description, backend)
    except Exception as e:
        raise HTTPException(502, f"Tailoring failed: {e}")

    checked = check_tailored(tailored, req.master)
    flags = [
        f"{f.value[:60]}…" for exp in checked.experience for f in exp.bullets
        if f.verification_status.value == "flagged"
    ]
    return TailorResponse(tailored=checked, flags=flags)


@app.post("/api/render/pdf")
def pdf(resume: ResumeData):
    try:
        data, pages = render_pdf(resume)
    except Exception as e:
        raise HTTPException(500, f"PDF render failed: {e}")
    return Response(
        content=data, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Resume.pdf",
                 "X-Page-Count": str(pages)},
    )


@app.post("/api/render/docx")
def docx(resume: ResumeData):
    try:
        data = render_docx(resume)
    except Exception as e:
        raise HTTPException(500, f"DOCX render failed: {e}")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=Resume.docx"},
    )


@app.post("/api/import/docx")
async def import_docx(file: UploadFile = File(...)):
    """DOCX 导入的最小实现：提取文本，返回给前端让用户手工映射到结构化字段。"""
    import mammoth
    if not file.filename.endswith(".docx"):
        raise HTTPException(400, "Only .docx is supported")
    result = await mammoth.convert_to_html(file.file)
    return {"html": result.value, "messages": result.messages}