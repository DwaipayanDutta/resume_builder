import { useState } from "react";
import { useResumeStore } from "../store";

export function ExportDialog({ onClose }: { onClose: () => void }) {
  const resume = useResumeStore((s) => s.resume);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const jsonStr = JSON.stringify(resume);
  const placeholders = jsonStr.match(/\[ADD METRIC\]/g)?.length ?? 0;
  const flagged =
    jsonStr.match(/"verification_status":"flagged"/g)?.length ?? 0;

  const download = async (format: "pdf" | "docx") => {
    setBusy(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/render/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resume),
      });
      if (!res.ok) {
        const errText = await res.text();
        setErrorMsg(`Export failed: ${errText}`);
        setBusy(false);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Resume.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setBusy(false);
      onClose();
    } catch (err: unknown) {
      setErrorMsg(`Network or render error: ${String(err)}`);
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>Export Checklist</h3>
        <div className="checklist">
          {placeholders > 0 && (
            <div className="check-item warn">
              ⚠️ {placeholders} unresolved [ADD METRIC] placeholder(s) in resume.
            </div>
          )}
          {flagged > 0 && (
            <div className="check-item warn">
              ⚠️ {flagged} unverified claim(s) flagged by fact-checker.
            </div>
          )}
          {placeholders === 0 && flagged === 0 && (
            <div className="check-item ok">
              ✅ All verifiable metrics and claims passed truthfulness checks.
            </div>
          )}
        </div>

        {errorMsg && <div className="error-banner">{errorMsg}</div>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={() => download("pdf")}
          >
            {busy ? "Rendering..." : "Download PDF"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() => download("docx")}
          >
            {busy ? "Rendering..." : "Download Word (.docx)"}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
            disabled={busy}
          >
            Back to editor
          </button>
        </div>
      </div>
    </div>
  );
}
