import { useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// API types (mirror src/resume_builder/api/studio.py)
// ---------------------------------------------------------------------------
export interface BackendInfo {
  id: string;
  label: string;
  cloud: boolean;
  configured: boolean;
  hint: string;
}

export interface StudioConfig {
  default_backend: string | null;
  default_model: string | null;
  backends: BackendInfo[];
}

export interface DownloadFile {
  filename: string;
  media_type: string;
  data_base64: string;
}

export interface BuildResult {
  mode: "format" | "tailor";
  backend: string | null;
  model: string | null;
  disclosure: string;
  pages: number;
  fits_two_pages: boolean;
  placeholders: number;
  warnings: string[];
  verification: string[];
  files: Record<string, DownloadFile>;
}

interface DownloadLink {
  url: string;
  filename: string;
}

interface BuildEntry extends Omit<BuildResult, "files"> {
  id: string;
  links: Record<string, DownloadLink>;
  name: string;
  jobLabel: string;
  createdAt: Date;
}

/** Turn the files returned by the server into in-browser (blob:) download links. */
function toLinks(files: Record<string, DownloadFile>): Record<string, DownloadLink> {
  const links: Record<string, DownloadLink> = {};
  for (const [kind, f] of Object.entries(files)) {
    const bytes = Uint8Array.from(atob(f.data_base64), (c) => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: f.media_type });
    links[kind] = { url: URL.createObjectURL(blob), filename: f.filename };
  }
  return links;
}

let buildCounter = 0;

async function errorDetail(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    return JSON.stringify(data?.detail ?? data);
  } catch {
    return `Server returned ${res.status}`;
  }
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ---------------------------------------------------------------------------
// Small presentational pieces
// ---------------------------------------------------------------------------
function StepCheck({ done, label }: { done: boolean; label: string }) {
  return (
    <li className={`gs-step ${done ? "done" : ""}`}>
      <span className="gs-icon" aria-hidden="true">
        {done ? (
          <svg viewBox="0 0 20 20" width="20" height="20">
            <circle cx="10" cy="10" r="9" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <path d="M6 10.4l2.6 2.6L14 7.6" fill="none" stroke="currentColor" strokeWidth="1.8"
              strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 20 20" width="20" height="20">
            <circle cx="10" cy="10" r="9" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <path d="M10 6v8M6 10h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        )}
      </span>
      <span>{label}</span>
      <span className="sr-only">{done ? "(done)" : "(to do)"}</span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export function StudioDashboard({ onOpenEditor }: { onOpenEditor?: () => void }) {
  const [config, setConfig] = useState<StudioConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  // Resume file
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Job
  const [jdUrl, setJdUrl] = useState("");
  const [jdText, setJdText] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [fetchingJd, setFetchingJd] = useState(false);
  const [jdError, setJdError] = useState<string | null>(null);
  const [jdNotice, setJdNotice] = useState<string | null>(null);

  // Build options
  const [mode, setMode] = useState<"tailor" | "format">("format");
  const [backend, setBackend] = useState("qwen");
  const [model, setModel] = useState("");
  const [includeReport, setIncludeReport] = useState(false);
  const [basename, setBasename] = useState("Resume");

  // Build state
  const [building, setBuilding] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [buildError, setBuildError] = useState<string | null>(null);
  const [history, setHistory] = useState<BuildEntry[]>([]);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const buildAbort = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/studio/config")
      .then(async (res) => {
        if (!res.ok) throw new Error(await errorDetail(res));
        return res.json() as Promise<StudioConfig>;
      })
      .then((cfg) => {
        if (cancelled) return;
        setConfig(cfg);
        if (cfg.default_backend) {
          setBackend(cfg.default_backend);
          setMode("tailor");
        }
        if (cfg.default_model) setModel(cfg.default_model);
      })
      .catch((e: unknown) => {
        if (!cancelled) setConfigError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!building) return;
    const started = Date.now();
    setElapsed(0);
    const t = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(t);
  }, [building]);

  const selectedBackend = config?.backends.find((b) => b.id === backend);
  const hasJob = jdText.trim().length >= 50;
  const latest = history[0] ?? null;
  const previewEntry = history.find((h) => h.id === previewId) ?? latest;

  // Free the in-browser file copies when the dashboard closes.
  const historyRef = useRef<BuildEntry[]>([]);
  historyRef.current = history;
  useEffect(() => () => {
    for (const h of historyRef.current) for (const l of Object.values(h.links)) URL.revokeObjectURL(l.url);
  }, []);

  const pickFile = (f: File | undefined | null) => {
    setBuildError(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".txt")) {
      setBuildError("Please choose a .txt resume (same layout as examples/New Resume.txt).");
      return;
    }
    setFile(f);
    if (basename === "Resume") {
      const stem = f.name.replace(/\.txt$/i, "").trim();
      if (stem) setBasename(stem);
    }
  };

  const fetchJd = async () => {
    setJdError(null);
    setJdNotice(null);
    if (!/^https?:\/\//i.test(jdUrl.trim())) {
      setJdError("Paste the full link to the job posting, starting with https://");
      return;
    }
    setFetchingJd(true);
    try {
      const res = await fetch("/api/studio/jd-from-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: jdUrl.trim() }),
      });
      if (!res.ok) throw new Error(await errorDetail(res));
      const data = await res.json();
      setJdText(data.text ?? "");
      if (data.title && !jobTitle) setJobTitle(data.title);
      if (data.company && !company) setCompany(data.company);
      setJdNotice(
        data.source === "json-ld"
          ? "Job description imported. Review it below before building."
          : "Imported the page text. Trim anything that isn't part of the job description."
      );
    } catch (e: unknown) {
      setJdError(e instanceof Error ? e.message : String(e));
    } finally {
      setFetchingJd(false);
    }
  };

  const build = async () => {
    if (!file) {
      setBuildError("Upload your resume .txt first.");
      return;
    }
    if (mode === "tailor") {
      if (!jobTitle.trim()) return setBuildError("Enter the target job title.");
      if (!hasJob) return setBuildError("Add the job description: fetch it from the link or paste it.");
      if (backend === "litellm" && !model.trim())
        return setBuildError("Enter a model name for LiteLLM, e.g. anthropic/claude-sonnet-5-5.");
    }
    setBuildError(null);
    setBuilding(true);
    const controller = new AbortController();
    buildAbort.current = controller;

    const form = new FormData();
    form.append("resume", file, file.name);
    form.append("mode", mode);
    form.append("basename", basename);
    if (mode === "tailor") {
      form.append("job_title", jobTitle.trim());
      form.append("company", company.trim());
      form.append("jd_text", jdText.trim());
      form.append("backend", backend);
      if (model.trim()) form.append("model", model.trim());
      form.append("include_report", includeReport ? "true" : "false");
    }

    try {
      const res = await fetch("/api/studio/build", {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(await errorDetail(res));
      const { files, ...data }: BuildResult = await res.json();
      const entry: BuildEntry = {
        ...data,
        id: `build-${++buildCounter}`,
        links: toLinks(files),
        name: basename || "Resume",
        jobLabel: mode === "tailor" ? [jobTitle, company].filter(Boolean).join(" · ") : "Format only",
        createdAt: new Date(),
      };
      setHistory((h) => [entry, ...h]);
      setPreviewId(entry.id);
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") {
        setBuildError("Build cancelled.");
      } else {
        setBuildError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setBuilding(false);
      buildAbort.current = null;
    }
  };

  return (
    <div className="studio">
      <div className="studio-grid">
        {/* ------------------------------------------------------------ main */}
        <div className="studio-main">
          {/* Resume upload */}
          <section className="studio-section">
            <div className="studio-section-head">
              <h2>Your resume</h2>
              <a className="studio-link" href="#layout-help" onClick={(e) => {
                e.preventDefault();
                document.getElementById("layout-help")?.scrollIntoView({ behavior: "smooth" });
              }}>
                TXT layout guide
              </a>
            </div>
            <div
              className={`dropzone ${dragOver ? "drag" : ""} ${file ? "has-file" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                pickFile(e.dataTransfer.files?.[0]);
              }}
              data-testid="dropzone"
            >
              <div className="dropzone-text">
                {file ? (
                  <>
                    <strong data-testid="file-name">{file.name}</strong>
                    <span>{(file.size / 1024).toFixed(1)} KB · ready to build</span>
                  </>
                ) : (
                  <>
                    <strong>Upload your resume (.txt)</strong>
                    <span>Drag and drop here, or choose a file</span>
                  </>
                )}
              </div>
              <button
                type="button"
                className="btn-studio primary"
                onClick={() => fileInputRef.current?.click()}
              >
                <span aria-hidden="true">＋</span> {file ? "Replace file" : "Choose .txt"}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,text/plain"
                className="sr-only"
                aria-label="Resume TXT file"
                data-testid="file-input"
                onChange={(e) => pickFile(e.target.files?.[0])}
              />
            </div>
          </section>

          {/* Target job */}
          <section className="studio-section">
            <div className="studio-section-head">
              <h2>Target job</h2>
              {mode === "format" && <span className="studio-muted">Optional for format-only builds</span>}
            </div>
            <div className="studio-card">
              <label className="studio-label" htmlFor="jd-url">Job posting link</label>
              <div className="url-row">
                <input
                  id="jd-url"
                  type="url"
                  inputMode="url"
                  placeholder="https://company.com/careers/senior-program-manager"
                  value={jdUrl}
                  onChange={(e) => setJdUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      fetchJd();
                    }
                  }}
                />
                <button
                  type="button"
                  className="btn-studio primary"
                  onClick={fetchJd}
                  disabled={fetchingJd || !jdUrl.trim()}
                >
                  {fetchingJd ? "Fetching…" : "Fetch job"}
                </button>
              </div>
              {jdError && <p className="studio-alert error" role="alert">{jdError}</p>}
              {jdNotice && <p className="studio-alert ok">{jdNotice}</p>}

              <div className="studio-two">
                <div>
                  <label className="studio-label" htmlFor="job-title">Job title</label>
                  <input id="job-title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)}
                    placeholder="e.g. Senior Program Manager" />
                </div>
                <div>
                  <label className="studio-label" htmlFor="company">Company (optional)</label>
                  <input id="company" value={company} onChange={(e) => setCompany(e.target.value)}
                    placeholder="e.g. Northwind" />
                </div>
              </div>

              <label className="studio-label" htmlFor="jd-text">
                Job description <span className="studio-muted">· fetched from the link, or paste it</span>
              </label>
              <textarea
                id="jd-text"
                rows={7}
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the job description here if the link can't be read (e.g. sign-in required)."
              />
            </div>
          </section>

          {/* Build */}
          <section className="studio-section">
            <div className="studio-section-head">
              <h2>Build</h2>
            </div>
            <div className="studio-card">
              <div className="mode-toggle" role="radiogroup" aria-label="Build mode">
                <button
                  type="button"
                  role="radio"
                  aria-checked={mode === "tailor"}
                  className={`mode-option ${mode === "tailor" ? "active" : ""}`}
                  onClick={() => setMode("tailor")}
                >
                  <strong>Tailor with AI</strong>
                  <span>Rewrite for this job, then build PDF + Word</span>
                </button>
                <button
                  type="button"
                  role="radio"
                  aria-checked={mode === "format"}
                  className={`mode-option ${mode === "format" ? "active" : ""}`}
                  onClick={() => setMode("format")}
                >
                  <strong>Format only</strong>
                  <span>Keep my words exactly; no AI</span>
                </button>
              </div>

              {mode === "tailor" && (
                <>
                  <div className="studio-two">
                    <div>
                      <label className="studio-label" htmlFor="backend">AI model</label>
                      <select id="backend" value={backend} onChange={(e) => setBackend(e.target.value)}>
                        {(config?.backends ?? [{ id: "qwen", label: "Local Qwen 2.5 3B (Ollama)", cloud: false, configured: true, hint: "" }]).map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.label}{b.configured ? "" : " (needs API key)"}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="studio-label" htmlFor="model">
                        {backend === "litellm" ? "Model name" : "Model name (optional)"}
                      </label>
                      <input id="model" value={model} onChange={(e) => setModel(e.target.value)}
                        placeholder={backend === "litellm" ? "e.g. anthropic/claude-sonnet-5-5" : "default"} />
                    </div>
                  </div>
                  <div
                    className={`privacy-note ${selectedBackend?.cloud ? "cloud" : "local"}`}
                    data-testid="privacy-note"
                  >
                    {selectedBackend?.cloud
                      ? `Your resume and the job description will be sent to ${selectedBackend.label}. API keys stay on this computer's server.`
                      : "Runs on your computer with Ollama. Nothing is sent to the cloud. Local models can take several minutes."}
                    {selectedBackend && !selectedBackend.configured && (
                      <div className="privacy-hint">{selectedBackend.hint}</div>
                    )}
                  </div>
                  <label className="studio-check">
                    <input type="checkbox" checked={includeReport}
                      onChange={(e) => setIncludeReport(e.target.checked)} />
                    Also write a fit &amp; keyword report (runs the model twice)
                  </label>
                </>
              )}

              <div className="build-row">
                <div className="build-name">
                  <label className="studio-label" htmlFor="basename">File name</label>
                  <input id="basename" value={basename} onChange={(e) => setBasename(e.target.value)} />
                </div>
                {building ? (
                  <button type="button" className="btn-studio ghost"
                    onClick={() => buildAbort.current?.abort()}>
                    Cancel ({elapsed}s)
                  </button>
                ) : null}
                <button
                  type="button"
                  className="btn-studio primary lg"
                  onClick={build}
                  disabled={building}
                  data-testid="build-button"
                >
                  {building
                    ? mode === "tailor" ? "Tailoring…" : "Building…"
                    : mode === "tailor" ? "Tailor & build PDF" : "Build PDF"}
                </button>
              </div>
              {buildError && <p className="studio-alert error" role="alert">{buildError}</p>}
            </div>
          </section>

          {/* Documents */}
          <section className="studio-section">
            <div className="studio-section-head">
              <h2>Documents</h2>
              {onOpenEditor && (
                <button type="button" className="studio-link as-button" onClick={onOpenEditor}>
                  Open guided editor
                </button>
              )}
            </div>

            {history.length === 0 ? (
              <div className="studio-empty">Your built resumes will appear here, ready to download.</div>
            ) : (
              <div className="doc-table" role="table" aria-label="Built documents">
                <div className="doc-row head" role="row">
                  <span role="columnheader">Name</span>
                  <span role="columnheader">Job</span>
                  <span role="columnheader">Pages</span>
                  <span role="columnheader">Created</span>
                  <span role="columnheader" className="right">Download</span>
                </div>
                {history.map((h) => (
                  <div
                    key={h.id}
                    className={`doc-row ${previewEntry?.id === h.id ? "selected" : ""}`}
                    role="row"
                    data-testid="doc-row"
                  >
                    <span role="cell">
                      <button type="button" className="doc-name" onClick={() => setPreviewId(h.id)}>
                        {h.name}
                      </button>
                      <span className={`doc-tag ${h.mode}`}>{h.mode === "tailor" ? "AI tailored" : "Formatted"}</span>
                    </span>
                    <span role="cell" className="doc-job">{h.jobLabel}</span>
                    <span role="cell">
                      <span className={h.fits_two_pages ? "pages-ok" : "pages-warn"}>{h.pages}</span>
                    </span>
                    <span role="cell">{formatTime(h.createdAt)}</span>
                    <span role="cell" className="right doc-actions">
                      <a className="btn-studio primary sm" href={h.links.pdf.url} download={h.links.pdf.filename}>PDF</a>
                      <a className="btn-studio ghost sm" href={h.links.docx.url} download={h.links.docx.filename}>Word</a>
                      <a className="btn-studio ghost sm" href={h.links.txt.url} download={h.links.txt.filename}>TXT</a>
                      {h.links.report && (
                        <a className="btn-studio ghost sm" href={h.links.report.url} download={h.links.report.filename}>Report</a>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {previewEntry && (
              <div className="result-panel" data-testid="result-panel">
                <p className="result-disclosure">{previewEntry.disclosure}</p>
                {previewEntry.warnings.length > 0 && (
                  <ul className="result-warnings">
                    {previewEntry.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                )}
                <iframe
                  title="PDF preview"
                  className="pdf-frame"
                  src={previewEntry.links.pdf.url}
                />
              </div>
            )}
          </section>
        </div>

        {/* ------------------------------------------------------------ side */}
        <aside className="studio-side">
          <section className="studio-section">
            <div className="studio-section-head"><h2>Get started</h2></div>
            <ul className="gs-list studio-card" data-testid="get-started">
              <StepCheck done={!!file} label="Upload your resume (.txt)" />
              <StepCheck done={hasJob} label="Add the job link or description" />
              <StepCheck done={history.length > 0} label="Build and download your PDF" />
            </ul>
          </section>

          <div className="promo-card">
            <span className="promo-pill">Private by default</span>
            <h3>Upload. Tailor. Download.</h3>
            <p>Format-only builds use no AI at all, and your files are never stored. AI tailoring keeps every employer, title and date from your TXT.</p>
            <ol className="promo-steps">
              <li><span>1</span>Your TXT stays the source of truth</li>
              <li><span>2</span>Missing numbers become [ADD METRIC]</li>
              <li><span>3</span>Changed roles are flagged for review</li>
            </ol>
          </div>

          <section className="studio-section" id="layout-help">
            <div className="studio-section-head"><h2>TXT layout</h2></div>
            <pre className="layout-sample studio-card">{`Your Name
Target Headline
City, Country
+1 555 0100
you@example.com

WORK EXPERIENCE
================

Job Title
Company
MM/YYYY - Present
City, Country
- Achievement bullet

PROFESSIONAL SUMMARY
====================
One paragraph...`}</pre>
          </section>

          {configError && (
            <p className="studio-alert error" role="alert">
              Can't reach the local server: {configError}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
