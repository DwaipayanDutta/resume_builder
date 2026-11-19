from __future__ import annotations
from io import BytesIO
from docx import Document
from docx.shared import Pt
from ..models.resume import ResumeData


def render_docx(resume: ResumeData) -> bytes:
    try:
        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(10.5)

        if resume.contact.name.value:
            doc.add_heading(resume.contact.name.value, level=0)
        contact_parts = [
            f.value for f in [resume.contact.email, resume.contact.phone,
                              resume.contact.linkedin, resume.contact.location]
            if f and f.value.strip()
        ]
        if contact_parts:
            doc.add_paragraph(" · ".join(contact_parts))

        if resume.summary and resume.summary.value.strip():
            doc.add_heading("Professional Summary", level=1)
            doc.add_paragraph(resume.summary.value)

        if resume.experience:
            included_exp = [e for e in resume.experience if e.included]
            if included_exp:
                doc.add_heading("Work Experience", level=1)
                for e in included_exp:
                    p = doc.add_paragraph()
                    p.add_run(f"{e.title.value}  ").bold = True
                    p.add_run(f"{e.start_date.value} – {e.end_date.value}")
                    if e.company.value:
                        doc.add_paragraph(e.company.value)
                    for b in e.bullets:
                        if b.value.strip():
                            doc.add_paragraph(b.value, style="List Bullet")

        if resume.education:
            included_edu = [ed for ed in resume.education if ed.included]
            if included_edu:
                doc.add_heading("Education", level=1)
                for ed in included_edu:
                    parts = [p for p in [ed.degree.value, ed.institution.value] if p.strip()]
                    if parts:
                        doc.add_paragraph(" — ".join(parts))

        if resume.skills:
            skill_vals = [s.value for s in resume.skills if s.value.strip()]
            if skill_vals:
                doc.add_heading("Skills", level=1)
                doc.add_paragraph(" · ".join(skill_vals))

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
    except Exception as e:
        raise RuntimeError(f"DOCX rendering failed: {e}")
