import { useResumeStore } from "../store";

export function LivePreview() {
  const resume = useResumeStore((s) => s.resume);
  if (!resume) return <p>Loading…</p>;

  const renderSection = (key: string) => {
    switch (key) {
      case "summary":
        return resume.summary ? (
          <section key={key}><h2>Professional Summary</h2>
            <p className={resume.summary.verification_status === "flagged" ? "flag" : ""}>
              {resume.summary.value}</p></section>
        ) : null;
      case "experience":
        return resume.experience.length ? (
          <section key={key}><h2>Work Experience</h2>
            {resume.experience.filter((e) => e.included).map((e, i) => (
              <div key={i} className="preview-entry">
                <div className="preview-head"><strong>{e.title.value}</strong>
                  <span>{e.start_date.value} – {e.end_date.value}</span></div>
                <div className="muted">{e.company.value}</div>
                <ul>{e.bullets.map((b, j) => (
                  <li key={j} className={b.verification_status === "flagged" ? "flag" : ""}>
                    {b.value}</li>
                ))}</ul>
              </div>
            ))}</section>
        ) : null;
      case "education":
        return resume.education.length ? (
          <section key={key}><h2>Education</h2>
            {resume.education.filter((ed: any) => ed.included).map((ed: any, i: number) => (
              <div key={i}><strong>{ed.degree.value}</strong> — {ed.institution.value}</div>
            ))}</section>
        ) : null;
      case "skills":
        return resume.skills.length ? (
          <section key={key}><h2>Skills</h2>
            <p>{resume.skills.map((s) => s.value).join(" · ")}</p></section>
        ) : null;
      default:
        return null;
    }
  };

  return (
    <div className="preview-sheet">
      <h1>{resume.contact.name.value || "Your Name"}</h1>
      <div className="contact">
        {[resume.contact.email, resume.contact.phone, resume.contact.linkedin]
          .filter(Boolean).map((f: any, i) => <span key={i}>{f.value}</span>)}
      </div>
      {resume.section_order.map(renderSection)}
    </div>
  );
}