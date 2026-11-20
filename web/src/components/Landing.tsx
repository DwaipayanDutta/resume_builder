import { useRef, type ReactNode } from "react";

type Props = {
  onGetStarted: () => void;
  onSignIn: () => void;
};

const year = new Date().getFullYear();

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const FEATURES: { title: string; body: string; icon: string }[] = [
  {
    title: "AI Resume Tailoring",
    body: "Rewrites your resume for one specific job using a local model or the AI provider you choose.",
    icon: "M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z M18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8z",
  },
  {
    title: "Job Link Import",
    body: "Paste the link to a posting and the job description, title and company are filled in for you.",
    icon: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  },
  {
    title: "Format-Only Builds",
    body: "Turn your plain-text resume into a polished 2-page PDF and Word file. No AI, nothing leaves your computer.",
    icon: "M7 3h7l5 5v13H7z M14 3v5h5 M10 13h6 M10 17h6",
  },
  {
    title: "Guided Editor & Live Preview",
    body: "Edit section by section, drag to reorder, undo and redo, and see the A4 page update as you type.",
    icon: "M4 20h4L19 9l-4-4L4 16z M13.5 6.5l4 4",
  },
  {
    title: "Keyword & ATS Checks",
    body: "See which job keywords your resume covers, plus checks for page count, action verbs and missing metrics.",
    icon: "M4 12l5 5L20 6",
  },
];

const STEPS = [
  { n: "01", title: "Upload Your Resume", body: "Start from a plain-text resume. The layout guide shows exactly how to structure it." },
  { n: "02", title: "Add the Job", body: "Paste the job posting link, or the description itself, and pick how you want to tailor." },
  { n: "03", title: "Download & Apply", body: "Review what changed, then download your PDF and Word files, ready to send." },
];

const FACTS = [
  { value: "100+", label: "AI providers supported" },
  { value: "2-page", label: "A4 PDF & Word" },
  { value: "Local", label: "Private AI option" },
  { value: "Seconds", label: "To format, no AI" },
];

export function Landing({ onGetStarted, onSignIn }: Props) {
  const scroller = useRef<HTMLDivElement>(null);
  const goTo = (id: string) => {
    const el = scroller.current?.querySelector<HTMLElement>(`#${id}`);
    el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  };

  const NavLink = ({ to, children }: { to: string; children: ReactNode }) => (
    <button type="button" className="lp-navlink" onClick={() => goTo(to)}>{children}</button>
  );

  return (
    <div className="lp" ref={scroller}>
      <div className="lp-strip">
        <span>New: paste a job link and Resume Studio reads the description for you.</span>
        <button type="button" onClick={onGetStarted}>Try it free <span aria-hidden="true">→</span></button>
      </div>

      <header className="lp-header">
        <div className="lp-wrap lp-nav">
          <button type="button" className="lp-logo" onClick={() => goTo("top")} aria-label="Resume Studio home">
            <img src="/brand/resume-studio-logo-on-light.svg" alt="Resume Studio" />
          </button>
          <nav className="lp-links" aria-label="Sections">
            <NavLink to="top">Home</NavLink>
            <NavLink to="features">Features</NavLink>
            <NavLink to="how">How it works</NavLink>
            <NavLink to="promise">Our promise</NavLink>
          </nav>
          <div className="lp-actions">
            <button type="button" className="lp-btn ghost" onClick={onSignIn}>Sign in</button>
            <button type="button" className="lp-btn primary" onClick={onGetStarted}>Get started</button>
          </div>
        </div>
      </header>

      <main>
        {/* ------------------------------------------------------------ hero */}
        <section className="lp-hero" id="top">
          <div className="lp-wrap lp-hero-grid">
            <div className="lp-hero-copy">
              <p className="lp-eyebrow">Resume builder &middot; AI tailoring</p>
              <h1>Tailor Your Resume to Every Job.</h1>
              <p className="lp-hero-sub">Upload once. Paste a job link. Download a 2-page PDF.</p>
              <p className="lp-hero-body">
                Resume Studio rewrites your resume around the role you want, keeps every employer, title
                and date exactly as you wrote them, and builds polished PDF and Word files.
              </p>
              <div className="lp-cta-row">
                <button type="button" className="lp-btn primary lg" onClick={onGetStarted}>
                  Create free account <span aria-hidden="true">→</span>
                </button>
                <button type="button" className="lp-btn outline lg" onClick={() => goTo("how")}>
                  See how it works
                </button>
              </div>
            </div>

            <div className="lp-hero-visual" aria-hidden="true">
              <div className="mock-doc">
                <div className="mock-head">
                  <div className="mock-name">Alex Morgan</div>
                  <div className="mock-role">Senior Program Manager</div>
                  <div className="mock-contact"><i /><i /><i /></div>
                </div>
                <div className="mock-cols">
                  <div className="mock-main">
                    <div className="mock-h">Work Experience</div>
                    <div className="mock-job">
                      <b>Senior Program Manager</b><span>03/2022 – Present</span>
                    </div>
                    <p>Led a <mark>cross-functional program</mark> across five work packages.</p>
                    <p>Built <mark>KPI dashboards</mark> for executive reviews.</p>
                    <p className="mock-line" /><p className="mock-line short" />
                    <div className="mock-job">
                      <b>Program Manager</b><span>01/2019 – 02/2022</span>
                    </div>
                    <p className="mock-line" /><p className="mock-line" /><p className="mock-line short" />
                  </div>
                  <div className="mock-side">
                    <div className="mock-h">Core Skills</div>
                    <div className="mock-chips">
                      <span className="hit">Roadmaps</span><span>Agile</span>
                      <span className="hit">Stakeholders</span><span>Budgets</span>
                      <span className="hit">Delivery</span>
                    </div>
                    <div className="mock-h">Summary</div>
                    <p className="mock-line" /><p className="mock-line" /><p className="mock-line short" />
                  </div>
                </div>
              </div>
              <div className="lp-float lp-float-badge">
                <strong>2 pages</strong>
                <span>PDF + Word, ready to send</span>
              </div>
              <div className="lp-float lp-float-chip">
                <img src="/brand/resume-studio-icon.svg" alt="" width="20" height="20" />
                Tailored for: Senior Program Manager
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------ facts */}
        <section className="lp-facts" aria-label="At a glance">
          <div className="lp-wrap lp-facts-grid">
            {FACTS.map((f) => (
              <div key={f.label} className="lp-fact">
                <strong>{f.value}</strong>
                <span>{f.label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------------------ features */}
        <section className="lp-section" id="features">
          <div className="lp-wrap">
            <p className="lp-eyebrow">What it does</p>
            <h2 className="lp-h2">Every Resume. Every Application.</h2>
            <div className="lp-cards">
              {FEATURES.map((f) => (
                <article key={f.title} className="lp-card">
                  <span className="lp-card-icon"><Icon d={f.icon} /></span>
                  <h3>{f.title}</h3>
                  <p>{f.body}</p>
                  <button type="button" className="lp-more" onClick={onGetStarted}>
                    Get started <span aria-hidden="true">→</span>
                  </button>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------ how */}
        <section className="lp-section alt" id="how">
          <div className="lp-wrap">
            <p className="lp-eyebrow">How it works</p>
            <h2 className="lp-h2">Three Steps to Your Next Application</h2>
            <div className="lp-steps">
              {STEPS.map((s) => (
                <div key={s.n} className="lp-step">
                  <span className="lp-step-num" aria-hidden="true">{s.n}</span>
                  <p className="lp-step-label">Step {s.n}</p>
                  <h3>{s.title}</h3>
                  <p>{s.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------ cta + promise */}
        <section className="lp-section" id="promise">
          <div className="lp-wrap lp-cta-grid">
            <div>
              <p className="lp-eyebrow">Get started</p>
              <h2 className="lp-h2 tight">Ready for Your Next Application?</h2>
              <p className="lp-muted">
                Create a free account, upload your resume and build your first tailored PDF in a few minutes.
              </p>
              <button type="button" className="lp-btn primary lg" onClick={onGetStarted}>
                Get started today <span aria-hidden="true">→</span>
              </button>
            </div>
            <figure className="lp-quote">
              <span className="lp-quote-mark" aria-hidden="true">“</span>
              <blockquote>
                Your employers, job titles and dates stay exactly as you wrote them. Numbers the AI
                can't verify are flagged, and missing ones become [ADD METRIC] for you to fill in.
              </blockquote>
              <figcaption>
                <img src="/brand/resume-studio-icon.svg" alt="" width="34" height="34" />
                <span><strong>Our promise</strong><small>Built into every tailored resume</small></span>
              </figcaption>
            </figure>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-grid">
          <div className="lp-footer-brand">
            <img src="/brand/resume-studio-logo-on-dark.svg" alt="Resume Studio" />
            <p>Tailor your resume to every job, keep every fact accurate, and download polished PDF and Word files.</p>
          </div>
          <div>
            <h4>Quick links</h4>
            <ul>
              <li><button type="button" onClick={() => goTo("top")}>Home</button></li>
              <li><button type="button" onClick={() => goTo("features")}>Features</button></li>
              <li><button type="button" onClick={() => goTo("how")}>How it works</button></li>
              <li><button type="button" onClick={onSignIn}>Sign in</button></li>
            </ul>
          </div>
          <div>
            <h4>Features</h4>
            <ul>
              <li>AI resume tailoring</li>
              <li>Job link import</li>
              <li>Format-only builds</li>
              <li>Guided editor</li>
              <li>Keyword checks</li>
            </ul>
          </div>
          <div>
            <h4>Privacy</h4>
            <ul className="plain">
              <li>Runs on your own computer</li>
              <li>Local AI keeps everything offline</li>
              <li>Cloud AI is always disclosed first</li>
            </ul>
          </div>
        </div>
        <div className="lp-wrap lp-footer-bottom">
          <span>© {year} Resume Studio. All rights reserved.</span>
          <span>Build. Tailor. Stand out.</span>
        </div>
      </footer>
    </div>
  );
}
