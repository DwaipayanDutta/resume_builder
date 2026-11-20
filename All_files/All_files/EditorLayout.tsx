import { SectionNavigator } from "./SectionNavigator";
import { ExperienceForm } from "./SectionForm";
import { LivePreview } from "./LivePreview";
import { useResumeStore } from "../store";
import { ExportDialog } from "./ExportDialog";
import { useState } from "react";

export function EditorLayout() {
  const selected = useResumeStore((s) => s.selectedSection);
  const undo = useResumeStore((s) => s.undo);
  const redo = useResumeStore((s) => s.redo);
  const status = useResumeStore((s) => s.autoSaveStatus);
  const [exporting, setExporting] = useState(false);

  return (
    <div className="editor-root">
      <header className="editor-toolbar">
        <button onClick={undo}>Undo</button>
        <button onClick={redo}>Redo</button>
        <span className={`save-status ${status}`}>
          {status === "saved" ? "已自动保存" : status === "saving" ? "保存中…" : "未保存"}
        </span>
        <button onClick={() => setExporting(true)}>Export</button>
      </header>
      <div className="editor-panels">
        <aside className="panel-left"><SectionNavigator /></aside>
        <main className="panel-center">
          {selected === "experience" && (
            <div>
              <h3>Work Experience</h3>
              {useResumeStore.getState().resume.experience.map((_, i) => (
                <ExperienceForm key={i} index={i} />
              ))}
            </div>
          )}
          {selected !== "experience" && (
            <p className="hint">选中左侧区块以编辑。当前区块：{selected}</p>
          )}
        </main>
        <aside className="panel-right"><LivePreview /></aside>
      </div>
      {exporting && <ExportDialog onClose={() => setExporting(false)} />}
    </div>
  );
}