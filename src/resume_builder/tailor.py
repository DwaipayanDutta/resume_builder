"""Tailor a CV to a job description, then build Resume.docx / Resume.pdf.

Pipeline:
  1. Fill the bundled prompt template (prompt_template.txt) with the target role,
     company, job description and the current CV text.
  2. Send it to a backend: local Qwen 2.5 3B (via Ollama) or the Claude API.
  3. Clean the model's CV into the TXT layout create_resume.py expects.
  4. Build DOCX + PDF with create_resume.py (unchanged).

Usage:
    python -m resume_builder.tailor "New Resume.txt" --job-title "Senior Program Manager" \
        --company "Acme" --jd job.txt --backend qwen
    tailor-resume resume.txt --job-title "..." --jd job.txt --backend claude
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path

from . import create_resume as cr

DEFAULT_QWEN = "qwen2.5:3b"
DEFAULT_CLAUDE = "claude-sonnet-5-5"
DEFAULT_EMPHASIS = "program management and delivery work most relevant to the job description"

# --------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------
CV_ADDENDUM = """

OUTPUT OVERRIDE (this takes priority over the DELIVERABLES order, the Markdown instruction and the date format above):
Return ONLY deliverable C, the rewritten CV, between a line containing BEGIN_CV and a line containing END_CV. Write nothing before BEGIN_CV or after END_CV.
Plain text only: no Markdown, no bold, no tables, no code fences.
Use exactly the same layout as MY CURRENT CV, because a script parses it:
- Line 1: full name. Line 2: headline (the target job title). Then the contact lines exactly as in my current CV.
- Each section is an all-capitals heading line followed by a line of equals signs. Section order: WORK EXPERIENCE, PROFESSIONAL SUMMARY, CORE COMPETENCIES, EDUCATION, CERTIFICATIONS, KEY ACHIEVEMENTS, then any other section from my current CV (for example INTERESTS).
- In WORK EXPERIENCE every role is exactly four lines, then its bullets, then one blank line:
  Job title
  Company
  MM/YYYY - MM/YYYY   (or MM/YYYY - Present)
  City, Country
  - bullet text (one line each, starting with "- ")
- Dates use MM/YYYY. Keep every employer, job title, date and location exactly as in my current CV.
- PROFESSIONAL SUMMARY is one paragraph. CORE COMPETENCIES and KEY ACHIEVEMENTS are one "- " bullet per line. EDUCATION and CERTIFICATIONS keep the two-line entry format of my current CV.
"""

REPORT_ADDENDUM = """

OUTPUT OVERRIDE: Deliver ONLY A, B, D, E and F, in that order, as Markdown. Do NOT output the rewritten CV (C).
"""


def load_template() -> str:
    return resources.files("resume_builder").joinpath("prompt_template.txt").read_text(encoding="utf-8")


def build_prompt(template: str, job_title: str, company: str, jd: str, cv: str,
                 emphasis: str, addendum: str) -> str:
    text = template
    text = re.sub(r"\[choose/replace with:[^\]]*\]", emphasis, text)
    for key, val in (
        ("[PASTE EXACT JOB TITLE]", job_title),
        ("[PASTE COMPANY NAME, IF APPLICABLE]", company or "Not specified"),
        ("[PASTE FULL JOB DESCRIPTION]", jd),
        ("[PASTE FULL CV TEXT]", cv),
    ):
        # use a function so backslashes in the CV/JD are not treated as escapes
        text = text.replace(key, val)
    return text + addendum


# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------
def _post(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_claude(prompt: str, model: str, api_key: str, max_tokens: int = 8000) -> str:
    try:
        data = _post("https://api.anthropic.com/v1/messages",
                     {"model": model, "max_tokens": max_tokens,
                      "messages": [{"role": "user", "content": prompt}]},
                     {"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout=600)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API error {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach the Claude API: {e.reason}")
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def call_ollama(prompt: str, model: str, host: str, num_ctx: int) -> str:
    try:
        data = _post(host.rstrip("/") + "/api/chat",
                     {"model": model, "stream": False,
                      "messages": [{"role": "user", "content": prompt}],
                      "options": {"temperature": 0.2, "num_ctx": num_ctx}}, {}, timeout=3600)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Ollama error {e.code}: {e.read().decode('utf-8', 'replace')[:500]} "
                           f"(is the model installed? run: ollama pull {model})")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Ollama at {host} ({e.reason}). "
                           "Run run_resume.bat and choose option 1, or start it with: ollama serve")
    return data.get("message", {}).get("content", "")


# --------------------------------------------------------------------------
# Cleaning the model output into the create_resume TXT layout
# --------------------------------------------------------------------------
HEADINGS = {
    "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "EXPERIENCE", "PROFESSIONAL SUMMARY", "SUMMARY",
    "CORE COMPETENCIES", "SKILLS", "EDUCATION", "CERTIFICATIONS", "SELECTED ACHIEVEMENTS",
    "KEY ACHIEVEMENTS", "ACHIEVEMENTS", "INTERESTS",
}
CHAR_MAP = {"–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
            " ": " ", "•": "-", "●": "-", "▪": "-", "…": "..."}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
_D = r"(?:[A-Za-z]{3,9}\.?\s+\d{4}|\d{1,2}/\d{4})"
RANGE_RE = re.compile(rf"({_D})\s*(?:-|to)\s*({_D}|Present|Current|Now)", re.IGNORECASE)


def _one_date(s: str):
    s = s.strip().rstrip(".")
    if s.lower() in ("present", "current", "now"):
        return "Present"
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", s)
    if m:
        return f"{int(m.group(1)):02d}/{m.group(2)}"
    m = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{4})", s)
    if m and m.group(1)[:3].lower() in MONTHS:
        return f"{MONTHS.index(m.group(1)[:3].lower()) + 1:02d}/{m.group(2)}"
    return None


def _fix_range(m: re.Match) -> str:
    a, b = _one_date(m.group(1)), _one_date(m.group(2))
    return f"{a} - {b}" if a and b else m.group(0)


def clean_cv(raw: str) -> str:
    """Turn raw model output into the TXT layout that create_resume.parse() reads."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    m = re.search(r"BEGIN_CV\s*(.*?)(?:END_CV|\Z)", text, flags=re.DOTALL)
    if m:
        text = m.group(1)
    for k, v in CHAR_MAP.items():
        text = text.replace(k, v)

    header, sections, cur = [], [], None
    for line in text.splitlines():
        line = line.rstrip()
        if line.strip().startswith("```") or re.fullmatch(r"\s*=+\s*", line):
            continue
        line = re.sub(r"^\s*#+\s*", "", line)
        line = re.sub(r"\*\*|__|`", "", line)
        line = re.sub(r"^(\s*)[*+]\s+", r"\1- ", line)           # * bullets -> "- "
        line = RANGE_RE.sub(_fix_range, line)
        key = line.strip().rstrip(":").upper()
        if key in HEADINGS:
            cur = [key, []]
            sections.append(cur)
        elif cur is None:
            header.append(line)
        else:
            cur[1].append(line)

    # the first section becomes the wide left column, so make that the experience section
    sections.sort(key=lambda s: "EXPERIENCE" not in s[0])
    out = [l for l in header if l.strip()]
    for name, lines in sections:
        while lines and not lines[-1].strip():
            lines.pop()
        out += ["", name, "=" * len(name)] + lines
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def _jobs(txt_path):
    _, main, _ = cr.parse(txt_path)
    return {(b[2], b[3]) for b in main if b[0] == "job"}


# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tailor-resume",
                                 description="Tailor a CV to a job with local Qwen or the Claude API, then build DOCX + PDF.")
    ap.add_argument("resume", help="current CV .txt (same layout as examples/New Resume.txt)")
    ap.add_argument("--job-title", required=True, help="exact target job title")
    ap.add_argument("--company", default="", help="target company (optional)")
    jd = ap.add_mutually_exclusive_group(required=True)
    jd.add_argument("--jd", help="path to a .txt file containing the job description")
    jd.add_argument("--jd-text", help="job description pasted as text")
    ap.add_argument("--backend", choices=["qwen", "claude"],
                    default="claude" if os.environ.get("ANTHROPIC_API_KEY") else "qwen")
    ap.add_argument("--model", help=f"default: {DEFAULT_QWEN} (qwen) or {DEFAULT_CLAUDE} (claude)")
    ap.add_argument("--api-key", help="Anthropic API key (default: ANTHROPIC_API_KEY env var)")
    ap.add_argument("--ollama-host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    ap.add_argument("--num-ctx", type=int, default=12288, help="Ollama context window (default 12288)")
    ap.add_argument("--emphasis", default=DEFAULT_EMPHASIS, help="experience to emphasise (fills the prompt's choose/replace slot)")
    ap.add_argument("--no-report", action="store_true", help="skip the assessment/keyword report")
    ap.add_argument("-o", "--out-dir", default=".", help="output folder")
    ap.add_argument("--basename", default="Resume", help="output file name without extension")
    ap.add_argument("--verify", action="store_true", help="check DOCX/PDF against the tailored TXT")
    args = ap.parse_args(argv)

    src = Path(args.resume)
    if not src.is_file():
        sys.exit(f"Resume file not found: {src}")
    jd_text = args.jd_text if args.jd_text else Path(args.jd).read_text(encoding="utf-8-sig")
    cv_text = src.read_text(encoding="utf-8-sig")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.backend == "claude":
        key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            sys.exit("Claude backend needs an API key: set ANTHROPIC_API_KEY or pass --api-key")
        model = args.model or DEFAULT_CLAUDE
        run = lambda p: call_claude(p, model, key)
    else:
        model = args.model or DEFAULT_QWEN
        run = lambda p: call_ollama(p, model, args.ollama_host, args.num_ctx)
    print(f"Backend: {args.backend} ({model})")

    template = load_template()
    mk = lambda add: build_prompt(template, args.job_title, args.company, jd_text, cv_text, args.emphasis, add)

    try:
        print("Tailoring CV (this can take several minutes on a local model)...")
        raw_cv = run(mk(CV_ADDENDUM))
        raw_path = out / f"{args.basename}_raw.txt"
        raw_path.write_text(raw_cv, encoding="utf-8")

        if not args.no_report:
            print("Writing assessment and keyword report...")
            report = run(mk(REPORT_ADDENDUM))
            (out / f"{args.basename}_report.md").write_text(report, encoding="utf-8")
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")

    tailored = clean_cv(raw_cv)
    txt_path = out / f"{args.basename}.txt"
    txt_path.write_text(tailored, encoding="utf-8")

    header, main_blocks, side_blocks = cr.parse(txt_path)
    if not any(b[0] == "job" for b in main_blocks):
        sys.exit(f"ERROR: the model's CV did not follow the required layout (no job blocks found).\n"
                 f"Raw output: {raw_path}\nTry again, edit {txt_path}, or use --backend claude.")

    # truthfulness guard: employers and dates must not change
    try:
        before, after = _jobs(src), _jobs(txt_path)
        for company, dates in sorted(before - after):
            print(f"WARNING: original role missing or changed: {company} | {dates}")
        for company, dates in sorted(after - before):
            print(f"WARNING: new or altered role in output (check it): {company} | {dates}")
    except Exception:
        pass
    n = tailored.count("[ADD METRIC]")
    if n:
        print(f"NOTE: {n} [ADD METRIC] placeholder(s) in the CV - fill in real numbers or delete them.")

    docx_path, pdf_path = out / f"{args.basename}.docx", out / f"{args.basename}.pdf"
    cr.build_docx(header, main_blocks, side_blocks, docx_path)
    fits = cr.build_pdf(header, main_blocks, side_blocks, pdf_path)
    print(f"Created {txt_path}, {docx_path} and {pdf_path}")
    report_done(args, out)
    if not fits:
        print("WARNING: PDF content does not fit on 2 pages - shorten the TXT or reduce BODY in create_resume.py")
    if args.verify and not cr.verify(txt_path, docx_path, pdf_path):
        return 1
    return 0


def report_done(args, out: Path) -> bool:
    p = out / f"{args.basename}_report.md"
    if p.is_file():
        print(f"Report (fit rating, keyword table, questions, LinkedIn About): {p}")
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
