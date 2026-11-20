import { useState } from "react";
import { SectionNavigator } from "./SectionNavigator";
import { SectionForm } from "./SectionForm";
import { LivePreview } from "./LivePreview";
import { AtsChecklistCard } from "./AtsChecklistCard";
import { useResumeStore } from "../store";
import { ExportDialog } from "./ExportDialog";

export function EditorLayout() {
  const isLoaded = useResumeStore((s) => s.isLoaded);
  const undo = useResumeStore((s) => s.undo);
  const redo = useResumeStore((s) => s.redo);
  const pastCount = useResumeStore((s) => s.past.length);
  const futureCount = useResumeStore((s) => s.future.length);
  const status = useResumeStore((s) => s.autoSaveStatus);
  const resetResume = useResumeStore((s) => s.resetResume);
  const [exporting, setExporting] = useState(false);

  if (!isLoaded) {
    return (
      <div className="editor-loading">
        <h2>Loading Resume...</h2>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => resetResume()}
        >
          Create New Resume
        </button>
      </div>
    );
  }

  return (
    <div className="editor-root">
      <header className="editor-toolbar">
        <div className="toolbar-left">
          <div className="history-buttons">
            <button
              type="button"
              className="btn-history"
              onClick={undo}
              disabled={pastCount === 0}
              title="Undo last change"
            >
              ↶ Undo
            </button>
            <button
              type="button"
              className="btn-history"
              onClick={redo}
              disabled={futureCount === 0}
              title="Redo last change"
            >
              ↷ Redo
            </button>
          </div>
        </div>

        <div className="toolbar-center">
          <div className={`save-status-indicator ${status}`}>
            <span className="status-dot"></span>
            <span className="status-text">
              {status === "saved"
                ? "All changes saved"
                : status === "saving"
                ? "Saving changes..."
                : "Unsaved edits"}
            </span>
          </div>
        </div>

        <div className="toolbar-right">
          <button
            type="button"
            className="btn btn-export"
            onClick={() => setExporting(true)}
          >
            Export Resume ▾
          </button>
        </div>
      </header>

      <div className="editor-panels">
        <aside className="panel-left">
          <SectionNavigator />
        </aside>

        <main className="panel-center">
          <AtsChecklistCard />
          <SectionForm />
        </main>

        <aside className="panel-right">
          <LivePreview />
        </aside>
      </div>

      {exporting && <ExportDialog onClose={() => setExporting(false)} />}
    </div>
  );
}
