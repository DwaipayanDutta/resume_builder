"""Resume Studio endpoints: upload a TXT resume, pull a job description from a
link, optionally tailor with AI, and download the PDF/DOCX.

This reuses the exact CLI pipeline (``tailor.py`` + ``create_resume.py``), so the
web app produces the same files as ``run_resume.bat`` / ``tailor-resume``.
API keys are only read from the server's environment, never from the browser.
"""
from __future__ import annotations

import base64
import contextlib
import io
import ipaddress
import json
import os
import re
import shutil
import socket
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .. import create_resume as cr
from .. import tailor as tl

router = APIRouter(prefix="/api/studio", tags=["studio"])

MAX_TXT_BYTES = 512 * 1024
MAX_JD_BYTES = 3 * 1024 * 1024
MAX_JD_CHARS = 20000
FILE_KINDS = {
    "pdf": ("pdf", "application/pdf"),
    "docx": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "txt": ("txt", "text/plain; charset=utf-8"),
    "report": ("md", "text/markdown; charset=utf-8"),
}
BACKENDS = {
    "qwen": {"label": "Local Qwen 2.5 3B (Ollama)", "cloud": False},
    "litellm": {"label": "Any provider via LiteLLM (Claude, Gemini, OpenAI, ...)", "cloud": True},
    # Still accepted for API/CLI compatibility, but not offered in the UI:
    # Claude is reached through LiteLLM (model "anthropic/...").
    "claude": {"label": "Claude API (Anthropic)", "cloud": True},
}
LISTED_BACKENDS = ("qwen", "litellm")
_LITELLM_KEY_VARS = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
    "COHERE_API_KEY", "OPENROUTER_API_KEY", "TOGETHER_API_KEY", "DEEPSEEK_API_KEY", "XAI_API_KEY",
    "AZURE_API_KEY", "FIREWORKS_API_KEY", "PERPLEXITY_API_KEY", "HUGGINGFACE_API_KEY",
    "REPLICATE_API_KEY",
)


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
class BackendInfo(BaseModel):
    id: str
    label: str
    cloud: bool
    configured: bool
    hint: str = ""


class StudioConfig(BaseModel):
    default_backend: Optional[str]
    default_model: Optional[str]
    backends: list[BackendInfo]


def _backend_status(name: str) -> tuple[bool, str]:
    if name == "claude":
        ok = bool(os.environ.get("ANTHROPIC_API_KEY"))
        return ok, "" if ok else "Set ANTHROPIC_API_KEY before starting the server (run_resume.bat asks for it)."
    if name == "litellm":
        ok = any(os.environ.get(v) for v in _LITELLM_KEY_VARS)
        return ok, "" if ok else ("No API key found. Start the app from run_resume.bat and choose "
                                  "'Any provider', or set your provider's key env var (e.g. ANTHROPIC_API_KEY).")
    return True, "Requires Ollama running locally with the model pulled."


def is_hosted() -> bool:
    """True on a hosted deployment (Vercel sets VERCEL=1; others can set RESUME_HOSTED=1)."""
    return bool(os.environ.get("VERCEL") or os.environ.get("RESUME_HOSTED"))


def listed_backends() -> tuple[str, ...]:
    # Local Ollama (qwen) can't be reached from a hosted server, so it isn't offered there.
    return tuple(b for b in LISTED_BACKENDS if not (is_hosted() and b == "qwen"))


@router.get("/config", response_model=StudioConfig)
def config() -> StudioConfig:
    backends = []
    for bid in listed_backends():
        meta = BACKENDS[bid]
        ok, hint = _backend_status(bid)
        backends.append(BackendInfo(id=bid, label=meta["label"], cloud=meta["cloud"],
                                    configured=ok, hint=hint))
    default = os.environ.get("RESUME_BACKEND") or None
    if default not in listed_backends():
        default = None
    return StudioConfig(default_backend=default,
                        default_model=os.environ.get("RESUME_MODEL") or None,
                        backends=backends)


# --------------------------------------------------------------------------
# Job description from a link
# --------------------------------------------------------------------------
class JDFetchRequest(BaseModel):
    url: str


class JDFetchResponse(BaseModel):
    url: str
    title: Optional[str] = None
    company: Optional[str] = None
    text: str
    source: str  # "json-ld" | "page-text"


def _assert_public_http_url(url: str) -> None:
    """Block non-http(s) schemes and hosts that resolve to private/loopback addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Enter a full http(s):// link to the job posting.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        raise HTTPException(status_code=400, detail=f"Could not resolve host '{parsed.hostname}'.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise HTTPException(status_code=400, detail="Links to local or private network addresses are not allowed.")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "header", "footer", "form", "button", "iframe"}
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
             "section", "article", "tr", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "li" and not self.skip_depth:
            self.parts.append("\n- ")
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    p = _TextExtractor()
    p.feed(html)
    text = "".join(p.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, p.title.strip()


def _find_job_posting(node):
    if isinstance(node, list):
        for n in node:
            found = _find_job_posting(n)
            if found:
                return found
    elif isinstance(node, dict):
        t = node.get("@type")
        if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
            return node
        if "@graph" in node:
            return _find_job_posting(node["@graph"])
    return None


def extract_job_description(html: str) -> dict:
    """Prefer schema.org JobPosting (used by most job boards); fall back to page text."""
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html, flags=re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        job = _find_job_posting(data)
        if job and job.get("description"):
            desc, _ = html_to_text(str(job["description"]))
            org = job.get("hiringOrganization")
            company = org.get("name") if isinstance(org, dict) else (org if isinstance(org, str) else None)
            return {"title": job.get("title"), "company": company, "text": desc, "source": "json-ld"}
    text, title = html_to_text(html)
    return {"title": title or None, "company": None, "text": text, "source": "page-text"}


def _fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResumeStudio/1.0)",
               "Accept": "text/html,application/xhtml+xml"}
    current = url
    with httpx.Client(timeout=15, follow_redirects=False, headers=headers) as client:
        for _ in range(6):
            _assert_public_http_url(current)
            resp = client.get(current)
            if resp.is_redirect and resp.headers.get("location"):
                current = urljoin(current, resp.headers["location"])
                continue
            if resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"The job site returned HTTP {resp.status_code}.")
            if len(resp.content) > MAX_JD_BYTES:
                raise HTTPException(status_code=413, detail="That page is too large to read.")
            return resp.text
    raise HTTPException(status_code=502, detail="Too many redirects.")


@router.post("/jd-from-url", response_model=JDFetchResponse)
def jd_from_url(req: JDFetchRequest) -> JDFetchResponse:
    url = req.url.strip()
    try:
        html = _fetch_html(url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not download the job page: {e}")
    info = extract_job_description(html)
    text = info["text"][:MAX_JD_CHARS].strip()
    if len(text) < 200:
        raise HTTPException(
            status_code=422,
            detail="Couldn't find a job description on that page (some sites require sign-in, e.g. "
                   "LinkedIn). Paste the description text instead.",
        )
    return JDFetchResponse(url=url, title=info["title"], company=info["company"],
                           text=text, source=info["source"])


# --------------------------------------------------------------------------
# Build (format only, or tailor + format)
#
# Stateless: each build runs in its own temporary folder that is deleted before the
# response is sent, and the files come back inside the response. Nothing about a user's
# resume is kept on the server, and it works on serverless hosts (e.g. Vercel) where the
# next request may land on a different machine.
# --------------------------------------------------------------------------
class DownloadFile(BaseModel):
    filename: str
    media_type: str
    data_base64: str


class BuildResponse(BaseModel):
    mode: str
    backend: Optional[str] = None
    model: Optional[str] = None
    disclosure: str
    pages: int
    fits_two_pages: bool
    placeholders: int
    warnings: list[str]
    verification: list[str]
    files: dict[str, DownloadFile]


def _safe_basename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9 _.-]", "", (name or "").strip()).strip(" .")
    return name[:60] or "Resume"


def _download(path: Path, kind: str) -> DownloadFile:
    _, media = FILE_KINDS[kind]
    return DownloadFile(filename=path.name, media_type=media,
                        data_base64=base64.b64encode(path.read_bytes()).decode("ascii"))


@router.post("/build", response_model=BuildResponse)
def build(
    resume: UploadFile = File(...),
    mode: str = Form("format"),
    job_title: str = Form(""),
    company: str = Form(""),
    jd_text: str = Form(""),
    backend: str = Form("qwen"),
    model: str = Form(""),
    include_report: bool = Form(False),
    basename: str = Form("Resume"),
) -> BuildResponse:
    if mode not in ("format", "tailor"):
        raise HTTPException(status_code=400, detail="mode must be 'format' or 'tailor'")
    if not (resume.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Upload your resume as a .txt file.")
    raw = resume.file.read(MAX_TXT_BYTES + 1)
    if len(raw) > MAX_TXT_BYTES:
        raise HTTPException(status_code=413, detail="Resume file is too large (max 512 KB).")
    try:
        cv_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        cv_text = raw.decode("cp1252", errors="replace")

    with tempfile.TemporaryDirectory(prefix="resume_studio_") as tmp:
        return _build_in(Path(tmp), cv_text, mode, job_title, company, jd_text, backend, model,
                         include_report, _safe_basename(basename))


def _build_in(out: Path, cv_text: str, mode: str, job_title: str, company: str, jd_text: str,
              backend: str, model: str, include_report: bool, base: str) -> BuildResponse:
    src = out / "source.txt"
    src.write_text(cv_text, encoding="utf-8")

    header, main_blocks, _ = cr.parse(src)
    if not header["name"] or not any(b[0] == "job" for b in main_blocks):
        raise HTTPException(
            status_code=422,
            detail="This TXT doesn't match the expected layout (name on line 1, then sections with "
                   "'=====' underlines and 4-line job entries). Compare with examples/New Resume.txt.",
        )

    warnings: list[str] = []
    files: dict[str, DownloadFile] = {}
    used_model = None
    disclosure = ("Format only: no AI was used. Your files were generated and are not stored on the server."
                  if is_hosted() else "Format only: no AI was used and nothing left your computer.")
    txt_path = out / f"{base}.txt"

    if mode == "tailor":
        if backend not in BACKENDS:
            raise HTTPException(status_code=400, detail=f"Unsupported backend '{backend}'")
        if not job_title.strip():
            raise HTTPException(status_code=400, detail="Enter the target job title.")
        if len(jd_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Add the job description (paste it or fetch it from the link).")
        chosen_model = model.strip() or os.environ.get("RESUME_MODEL") or None
        if backend == "litellm" and not chosen_model:
            raise HTTPException(
                status_code=400,
                detail="Enter a model name for LiteLLM, e.g. anthropic/claude-sonnet-5-5 or gemini/gemini-2.5-flash.",
            )
        try:
            run, used_model = tl.make_runner(backend, chosen_model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        try:
            tailored, raw_cv, report = tl.tailor_cv_text(
                run, cv_text, job_title.strip(), company.strip(), jd_text.strip()[:MAX_JD_CHARS],
                with_report=include_report)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=f"AI backend failed: {e}")
        txt_path.write_text(tailored, encoding="utf-8")
        if report:
            report_path = out / f"{base}_report.md"
            report_path.write_text(report, encoding="utf-8")
            files["report"] = _download(report_path, "report")
        header, main_blocks, side_blocks = cr.parse(txt_path)
        if not any(b[0] == "job" for b in main_blocks):
            raise HTTPException(
                status_code=502,
                detail="The AI's output didn't follow the resume layout (no job entries found). "
                       "Try again or choose a stronger model.",
            )
        warnings += tl.role_warnings(src, txt_path)
        disclosure = (
            f"Your resume and the job description were sent to {BACKENDS[backend]['label']}."
            if BACKENDS[backend]["cloud"]
            else "Processed locally with Ollama: nothing left your computer."
        )
    else:
        shutil.copyfile(src, txt_path)
        header, main_blocks, side_blocks = cr.parse(txt_path)

    docx_path, pdf_path = out / f"{base}.docx", out / f"{base}.pdf"
    try:
        cr.build_docx(header, main_blocks, side_blocks, docx_path)
        fits = cr.build_pdf(header, main_blocks, side_blocks, pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Building the documents failed: {e}")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            cr.verify(txt_path, docx_path, pdf_path)
        except Exception as e:
            print(f"Verification skipped: {e}")
    verification = [l for l in buf.getvalue().splitlines() if l.strip()]
    _, pages = cr._pdf_stream(pdf_path)

    placeholders = txt_path.read_text(encoding="utf-8").count("[ADD METRIC]")
    if not fits:
        warnings.append("Content does not fit on 2 pages; shorten the resume text.")
    if placeholders:
        warnings.append(f"{placeholders} [ADD METRIC] placeholder(s): replace with real numbers or delete them.")

    files.update({"pdf": _download(pdf_path, "pdf"), "docx": _download(docx_path, "docx"),
                  "txt": _download(txt_path, "txt")})
    return BuildResponse(
        mode=mode, backend=backend if mode == "tailor" else None, model=used_model,
        disclosure=disclosure, pages=pages, fits_two_pages=fits, placeholders=placeholders,
        warnings=warnings, verification=verification, files=files,
    )
