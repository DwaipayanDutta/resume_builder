from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..models.resume import ResumeData

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html(resume: ResumeData) -> str:
    """Render resume into formatted HTML using Jinja2."""
    template_file = f"{resume.template_id}.html"
    if not (TEMPLATE_DIR / template_file).is_file():
        raise FileNotFoundError(f"Template '{template_file}' not found in {TEMPLATE_DIR}")
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template(template_file)
    return template.render(r=resume)


def render_pdf(resume: ResumeData) -> tuple[bytes, int]:
    """Render resume HTML into PDF bytes and return (pdf_bytes, page_count)."""
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("PDF rendering requires 'weasyprint'. Install with: pip install resume-builder[web]")
    html = render_html(resume)
    try:
        doc = HTML(string=html).render()
        return doc.write_pdf(), len(doc.pages)
    except Exception as e:
        raise RuntimeError(f"WeasyPrint PDF rendering failed: {e}")
