from io import BytesIO
from docx import Document
from docx.shared import Pt
from ..models.resume import ResumeData


def render_docx(resume: ResumeData) -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    doc.add_heading(resume.contact.name.value, level=0)
    contact_parts = [
        f.value for f in [resume.contact.email, resume.contact.phone,
                          resume.contact.linkedin, resume.contact.location] if f
    ]
    if contact_parts:
        doc.add_paragraph(" · ".join(contact_parts))

    if resume.summary:
        doc.add_heading("Professional Summary", level=1)
        doc.add_paragraph(resume.summary.value)

    if resume.experience:
        doc.add_heading("Work Experience", level=1)
        for e in resume.experience:
            if not e.included:
                continue
            p = doc.add_paragraph()
            p.add_run(f"{e.title.value}  ").bold = True
            p.add_run(f"{e.start_date.value} – {e.end_date.value}")
            doc.add_paragraph(e.company.value)
            for b in e.bullets:
                doc.add_paragraph(b.value, style="List Bullet")

    if resume.education:
        doc.add_heading("Education", level=1)
        for ed in resume.education:
            if ed.included:
                doc.add_paragraph(f"{ed.degree.value} — {ed.institution.value}")

    if resume.skills:
        doc.add_heading("Skills", level=1)
        doc.add_paragraph(" · ".join(s.value for s in resume.skills))

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()