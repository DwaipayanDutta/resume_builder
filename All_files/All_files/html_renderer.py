from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from ..models.resume import ResumeData

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_pdf(resume: ResumeData) -> tuple[bytes, int]:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template(f"{resume.template_id}.html")
    html = template.render(r=resume)
    doc = HTML(string=html).render()
    return doc.write_pdf(), len(doc.pages)