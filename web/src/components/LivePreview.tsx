import { useResumeStore } from "../store";

export function LivePreview() {
  const resume = useResumeStore((s) => s.resume);
  const isLoaded = useResumeStore((s) => s.isLoaded);

  if (!isLoaded || !resume) {
    return (
      <div className="preview-sheet empty">
        <p className="loading-text">Loading preview...</p>
      </div>
    );
  }

  const renderSection = (key: string) => {
    switch (key) {
      case "summary":
        return resume.summary && resume.summary.value.trim() ? (
          <section key={key} className="preview-section">
            <h2>Professional Summary</h2>
            <p className={resume.summary.verification_status === "flagged" ? "flag" : ""}>
              {resume.summary.value}
            </p>
          </section>
        ) : null;

      case "experience":
        return resume.experience && resume.experience.length ? (
          <section key={key} className="preview-section">
            <h2>Work Experience</h2>
            {resume.experience
              .filter((e) => e.included)
              .map((e, i) => (
                <div key={i} className="preview-entry">
                  <div className="preview-head">
                    <strong>{e.title.value || "Untitled Role"}</strong>
                    <span>
                      {e.start_date.value} – {e.end_date.value}
                    </span>
                  </div>
                  {e.company.value && <div className="muted">{e.company.value}</div>}
                  <ul>
                    {e.bullets.map((b, j) => (
                      <li
                        key={j}
                        className={b.verification_status === "flagged" ? "flag" : ""}
                      >
                        {b.value}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
          </section>
        ) : null;

      case "education":
        return resume.education && resume.education.length ? (
          <section key={key} className="preview-section">
            <h2>Education</h2>
            {resume.education
              .filter((ed) => ed.included)
              .map((ed, i) => (
                <div key={i} className="preview-entry">
                  <strong>{ed.degree.value}</strong> — {ed.institution.value}
                </div>
              ))}
          </section>
        ) : null;

      case "skills":
        return resume.skills && resume.skills.length ? (
          <section key={key} className="preview-section">
            <h2>Skills</h2>
            <p>
              {resume.skills
                .map((s) => s.value)
                .filter(Boolean)
                .join(" · ")}
            </p>
          </section>
        ) : null;

      default:
        return null;
    }
  };

  return (
    <div className="preview-container">
      <div className="preview-header-bar">
        <span>A4 Format Preview</span>
      </div>
      <div className="preview-sheet">
        <h1 className="preview-name">{resume.contact.name.value || "Your Name"}</h1>
        <div className="preview-contact">
          {[
            resume.contact.email,
            resume.contact.phone,
            resume.contact.location,
            resume.contact.linkedin,
          ]
            .filter((f) => Boolean(f?.value))
            .map((f, i) => (
              <span key={i} className="contact-item">
                {f!.value}
              </span>
            ))}
        </div>
        {resume.section_order.map(renderSection)}
      </div>
    </div>
  );
}
