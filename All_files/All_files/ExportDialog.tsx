import { useState } from "react";
import { useResumeStore } from "../store";

export function ExportDialog({ onClose }: { onClose: () => void }) {
  const resume = useResumeStore((s) => s.resume);
  const [busy, setBusy] = useState(false);

  const placeholders = JSON.stringify(resume).match(/\[ADD METRIC\]/g)?.length ?? 0;
  const flagged = JSON.stringify(resume).match(/"verification_status":"flagged"/g)?.length ?? 0;

  const download = async (format: "pdf" | "docx") => {
    setBusy(true);
    const res = await fetch(`/api/render/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(resume),
    });
    if (!res.ok) { alert(await res.text()); setBusy(false); return; }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `Resume.${format}`;
    a.click();
    URL.revokeObjectURL(a.href);
    setBusy(false);
    onClose();
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>Export checklist</h3>
        {placeholders > 0 && <p className="warn">{placeholders} 处 [ADD METRIC] 尚未填写。</p>}
        {flagged > 0 && <p className="warn">{flagged} 个字段被事实核查标记为待确认。</p>}
        {placeholders === 0 && flagged === 0 && <p className="ok">所有事实字段均已核实。</p>}
        <div className="actions">
          <button disabled={busy} onClick={() => download("pdf")}>Download PDF</button>
          <button disabled={busy} onClick={() => download("docx")}>Download DOCX</button>
          <button onClick={onClose}>Back to editor</button>
        </div>
      </div>
    </div>
  );
}