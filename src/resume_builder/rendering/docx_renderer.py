from __future__ import annotations
from io import BytesIO
from docx import Document
from docx.shared import Pt
from ..models.resume import ResumeData


def _vals(fields) -> list[str]:
    return [f.value for f in fields if f and f.value.strip()]


def render_docx(resume: ResumeData) -> bytes:
    """Render the resume to DOCX bytes, following ``resume.section_order``."""
    try:
        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(10.5)

        if resume.contact.name.value:
            doc.add_heading(resume.contact.name.value, level=0)
        contact_parts = _vals([resume.contact.email, resume.contact.phone,
                               resume.contact.linkedin, resume.contact.location])
        if contact_parts:
            doc.add_paragraph(" · ".join(contact_parts))

        def summary():
            if resume.summary and resume.summary.value.strip():
                doc.add_heading("Professional Summary", level=1)
                doc.add_paragraph(resume.summary.value)

        def experience():
            items = [e for e in resume.experience if e.included]
            if not items:
                return
            doc.add_heading("Work Experience", level=1)
            for e in items:
                p = doc.add_paragraph()
                p.add_run(f"{e.title.value}  ").bold = True
                p.add_run(f"{e.start_date.value} – {e.end_date.value}")
                if e.company.value:
                    doc.add_paragraph(e.company.value)
                for b in _vals(e.bullets):
                    doc.add_paragraph(b, style="List Bullet")

        def projects():
            items = [p for p in resume.projects if p.included]
            if not items:
                return
            doc.add_heading("Projects", level=1)
            for pr in items:
                doc.add_paragraph().add_run(pr.name.value).bold = True
                if pr.description and pr.description.value.strip():
                    doc.add_paragraph(pr.description.value)
                for b in _vals(pr.bullets):
                    doc.add_paragraph(b, style="List Bullet")

        def education():
            items = [ed for ed in resume.education if ed.included]
            if not items:
                return
            doc.add_heading("Education", level=1)
            for ed in items:
                parts = [p for p in [ed.degree.value, ed.institution.value] if p.strip()]
                if parts:
                    doc.add_paragraph(" — ".join(parts))
                for d in _vals(ed.details):
                    doc.add_paragraph(d, style="List Bullet")

        def skills():
            vals = _vals(resume.skills)
            if vals:
                doc.add_heading("Skills", level=1)
                doc.add_paragraph(" · ".join(vals))

        def certifications():
            vals = _vals(resume.certifications)
            if vals:
                doc.add_heading("Certifications", level=1)
                for c in vals:
                    doc.add_paragraph(c, style="List Bullet")

        renderers = {
            "summary": summary, "experience": experience, "projects": projects,
            "education": education, "skills": skills, "certifications": certifications,
        }
        for section in resume.section_order:
            fn = renderers.get(section)
            if fn:
                fn()

        for cs in resume.custom_sections:
            vals = _vals(cs.items)
            if cs.included and vals:
                doc.add_heading(cs.name or "Additional", level=1)
                for v in vals:
                    doc.add_paragraph(v, style="List Bullet")

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
    except Exception as e:
        raise RuntimeError(f"DOCX rendering failed: {e}")
