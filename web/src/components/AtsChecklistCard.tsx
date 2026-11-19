import { useState } from "react";
import { useResumeStore } from "../store";
import { evaluateAtsChecklist } from "../utils/atsChecker";

export function AtsChecklistCard() {
  const resume = useResumeStore((s) => s.resume);
  const targetJobDescription = useResumeStore((s) => s.targetJobDescription);
  const setTargetJobDescription = useResumeStore((s) => s.setTargetJobDescription);
  const previewPages = useResumeStore((s) => s.previewPages);

  const [expanded, setExpanded] = useState<boolean>(true);
  const [filterMissing, setFilterMissing] = useState<boolean>(false);

  const report = evaluateAtsChecklist(resume, targetJobDescription, previewPages);

  const matchPercentage =
    report.keywords.total > 0
      ? Math.round((report.keywords.matchedCount / report.keywords.total) * 100)
      : 0;

  return (
    <div className="card ats-card" data-testid="ats-card">
      <div className="ats-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="ats-header-title">
          <h4>📊 ATS Match &amp; Verification Checklist</h4>
          <span className="heuristic-tag">Heuristic Guidance</span>
        </div>
        <button
          type="button"
          className="btn-toggle-expand"
          aria-label={expanded ? "Collapse ATS card" : "Expand ATS card"}
        >
          {expanded ? "▲" : "▼"}
        </button>
      </div>

      {expanded && (
        <div className="ats-card-body">
          {/* Heuristic Disclaimer */}
          <div className="heuristic-notice">
            <span className="notice-icon">ℹ️</span>
            <span>
              <strong>Note on ATS scoring:</strong> These checks are automated heuristics to
              improve clarity and keyword coverage, <em>not an ATS guarantee</em>. Tailor
              responsibilities authentically. Requirements are marked critical only when the JD
              explicitly states "required" or "must-have".
            </span>
          </div>

          {/* Job Description Input */}
          <div className="form-group ats-jd-group">
            <label htmlFor="ats-jd-input">Target Job Description (paste to analyze keywords)</label>
            <textarea
              id="ats-jd-input"
              rows={3}
              placeholder="Paste target job description to match skills and experience..."
              value={targetJobDescription}
              onChange={(e) => setTargetJobDescription(e.target.value)}
              className="ats-jd-textarea"
            />
          </div>

          {/* Real-time Checklist */}
          <div className="ats-checklist-section">
            <h5>Real-Time Format &amp; Content Checklist</h5>
            <ul className="ats-checklist">
              {/* Page count */}
              <li
                className={`checklist-item ${
                  report.pageCount.isOptimal ? "item-ok" : "item-warn"
                }`}
                data-testid="page-count-check"
              >
                <span className="checklist-icon">
                  {report.pageCount.isOptimal ? "✓" : "⚠️"}
                </span>
                <div className="checklist-details">
                  <strong>Actual Rendered Pages: {report.pageCount.pages}</strong>
                  <span> — {report.pageCount.message}</span>
                </div>
              </li>

              {/* Action Verbs */}
              <li
                className={`checklist-item ${
                  report.actionVerbs.isOptimal ? "item-ok" : "item-info"
                }`}
                data-testid="action-verbs-check"
              >
                <span className="checklist-icon">
                  {report.actionVerbs.isOptimal ? "✓" : "💡"}
                </span>
                <div className="checklist-details">
                  <strong>
                    Action Verbs: {report.actionVerbs.verbBullets} / {report.actionVerbs.totalBullets} bullets ({report.actionVerbs.percentage}%)
                  </strong>
                  <span> — Strong leading action verbs improve executive impact.</span>
                </div>
              </li>

              {/* Placeholders */}
              <li
                className={`checklist-item ${
                  report.placeholders.isResolved ? "item-ok" : "item-warn"
                }`}
                data-testid="placeholders-check"
              >
                <span className="checklist-icon">
                  {report.placeholders.isResolved ? "✓" : "⚠️"}
                </span>
                <div className="checklist-details">
                  <strong>
                    {report.placeholders.isResolved
                      ? "Metric Placeholders: All resolved"
                      : `Metric Placeholders: ${report.placeholders.count} unresolved`}
                  </strong>
                  {report.placeholders.count > 0 && (
                    <span className="placeholder-tags">
                      {" "}
                      (Found: {report.placeholders.items.slice(0, 3).join(", ")})
                    </span>
                  )}
                </div>
              </li>
            </ul>
          </div>

          {/* Keyword Matching */}
          <div className="ats-keywords-section">
            <div className="keywords-header">
              <h5>
                Keyword Coverage: {report.keywords.matchedCount} / {report.keywords.total}{" "}
                ({matchPercentage}%)
              </h5>
              {report.keywords.total > 0 && (
                <label className="checkbox-label filter-label">
                  <input
                    type="checkbox"
                    checked={filterMissing}
                    onChange={(e) => setFilterMissing(e.target.checked)}
                  />
                  Show missing only ({report.keywords.missingCount})
                </label>
              )}
            </div>

            {report.keywords.total === 0 ? (
              <p className="empty-keywords-hint">
                Paste a target job description above to extract keywords and verify alignment.
              </p>
            ) : (
              <div className="keywords-grid" data-testid="keywords-grid">
                {report.keywords.items
                  .filter((item) => (filterMissing ? !item.isMatched : true))
                  .map((item, idx) => (
                    <span
                      key={idx}
                      className={`keyword-pill ${
                        item.isMatched ? "keyword-matched" : "keyword-missing"
                      } ${item.isCritical ? "keyword-critical" : ""}`}
                      data-testid={`keyword-${item.term}`}
                    >
                      <span className="keyword-symbol">
                        {item.isMatched ? "✓" : "✕"}
                      </span>
                      {item.term}
                      {item.isCritical && (
                        <span className="critical-badge">Critical</span>
                      )}
                    </span>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
