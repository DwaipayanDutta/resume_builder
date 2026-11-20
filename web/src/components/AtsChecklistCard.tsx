import { useState } from "react";
import { useResumeStore } from "../store";
import { evaluateAtsChecklist } from "../utils/atsChecker";

export function AtsChecklistCard() {
  const resume = useResumeStore((s) => s.resume);
  const targetJobDescription = useResumeStore((s) => s.targetJobDescription);
  const setTargetJobDescription = useResumeStore((s) => s.setTargetJobDescription);
  const previewPages = useResumeStore((s) => s.previewPages);
  const previewPageError = useResumeStore((s) => s.previewPageError);

  const [expanded, setExpanded] = useState<boolean>(true);
  const [filterMissing, setFilterMissing] = useState<boolean>(false);

  const report = evaluateAtsChecklist(resume, targetJobDescription, previewPages, previewPageError);
  const pagesLabel =
    report.pageCount.pages === null
      ? "? Pages"
      : `${report.pageCount.pages} ${report.pageCount.pages === 1 ? "Page" : "Pages"}`;

  const matchPercentage =
    report.keywords.total > 0
      ? Math.round((report.keywords.matchedCount / report.keywords.total) * 100)
      : 0;

  return (
    <div className={`card ats-card ${expanded ? "expanded" : "collapsed"}`} data-testid="ats-card">
      {/* Sleek Header Bar */}
      <div className="ats-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="ats-header-left">
          <span className="ats-icon">🎯</span>
          <span className="ats-title">ATS Alignment &amp; Verification</span>
          <span className="heuristic-tag">Heuristic Guidance</span>
        </div>

        {/* Quick Micro-KPIs */}
        <div className="ats-quick-stats">
          <span className={`kpi-chip ${report.pageCount.isOptimal ? "kpi-ok" : "kpi-warn"}`}>
            <span className="kpi-dot"></span>
            {pagesLabel}
          </span>
          <span className={`kpi-chip ${report.actionVerbs.isOptimal ? "kpi-ok" : "kpi-info"}`}>
            <span className="kpi-dot"></span>
            {report.actionVerbs.percentage}% Verbs
          </span>
          <span className={`kpi-chip ${report.placeholders.isResolved ? "kpi-ok" : "kpi-warn"}`}>
            <span className="kpi-dot"></span>
            {report.placeholders.isResolved ? "0 Placeholders" : `${report.placeholders.count} Needed`}
          </span>
          {report.keywords.total > 0 && (
            <span className="kpi-chip kpi-neutral">
              {report.keywords.matchedCount}/{report.keywords.total} Keywords
            </span>
          )}
        </div>

        <button
          type="button"
          className="btn-toggle-expand"
          aria-label={expanded ? "Collapse ATS card" : "Expand ATS card"}
        >
          {expanded ? "Collapse ▲" : "Details ▼"}
        </button>
      </div>

      {expanded && (
        <div className="ats-card-body">
          {/* Format & Content KPI Grid (Modern 3-stat cards) */}
          <div className="ats-kpi-grid">
            {/* Rendered Page Count */}
            <div
              className={`ats-metric-tile ${report.pageCount.isOptimal ? "tile-ok" : "tile-warn"}`}
              data-testid="page-count-check"
            >
              <div className="tile-top">
                <span className="tile-label">Actual Rendered Pages: {report.pageCount.pages ?? "unknown"}</span>
                <span className="tile-status-icon">{report.pageCount.isOptimal ? "✓" : "⚠️"}</span>
              </div>
              <div className="tile-value">{report.pageCount.pages ?? "?"} / 2 Standard</div>
              <div className="tile-caption">{report.pageCount.message}</div>
            </div>

            {/* Action Verbs */}
            <div
              className={`ats-metric-tile ${report.actionVerbs.isOptimal ? "tile-ok" : "tile-info"}`}
              data-testid="action-verbs-check"
            >
              <div className="tile-top">
                <span className="tile-label">Action Verbs: {report.actionVerbs.verbBullets} / {report.actionVerbs.totalBullets} bullets ({report.actionVerbs.percentage}%)</span>
                <span className="tile-status-icon">{report.actionVerbs.isOptimal ? "✓" : "💡"}</span>
              </div>
              <div className="tile-value">{report.actionVerbs.percentage}% Active</div>
              <div className="tile-caption">Strong verbs lead executive impact</div>
            </div>

            {/* Placeholders */}
            <div
              className={`ats-metric-tile ${report.placeholders.isResolved ? "tile-ok" : "tile-warn"}`}
              data-testid="placeholders-check"
            >
              <div className="tile-top">
                <span className="tile-label">
                  {report.placeholders.isResolved
                    ? "Metric Placeholders: All resolved"
                    : `Metric Placeholders: ${report.placeholders.count} unresolved`}
                </span>
                <span className="tile-status-icon">{report.placeholders.isResolved ? "✓" : "⚠️"}</span>
              </div>
              <div className="tile-value">
                {report.placeholders.isResolved ? "0 Flags" : `${report.placeholders.count} Found`}
              </div>
              <div className="tile-caption">
                {report.placeholders.count > 0
                  ? `Replace ${report.placeholders.items.slice(0, 2).join(", ")}`
                  : "All [ADD METRIC] tags resolved"}
              </div>
            </div>
          </div>

          {/* Job Description Context Input */}
          <div className="ats-jd-wrapper">
            <div className="ats-jd-header">
              <label htmlFor="ats-jd-input" className="ats-jd-label">
                Target Job Description
              </label>
              <span className="ats-jd-hint">Paste to extract keywords and evaluate coverage</span>
            </div>
            <textarea
              id="ats-jd-input"
              rows={2}
              placeholder="Paste target job description to match skills and experience..."
              value={targetJobDescription}
              onChange={(e) => setTargetJobDescription(e.target.value)}
              className="ats-jd-textarea"
            />
          </div>

          {/* Keyword Matching Section */}
          <div className="ats-keywords-section">
            <div className="keywords-header">
              <div className="keywords-title-group">
                <span className="keywords-title">Keyword Coverage</span>
                <span className="keywords-count-pill">
                  {report.keywords.matchedCount} of {report.keywords.total} matched ({matchPercentage}%)
                </span>
              </div>
              {report.keywords.total > 0 && (
                <label className="checkbox-label filter-label">
                  <input
                    type="checkbox"
                    checked={filterMissing}
                    onChange={(e) => setFilterMissing(e.target.checked)}
                  />
                  Missing only ({report.keywords.missingCount})
                </label>
              )}
            </div>

            {report.keywords.total === 0 ? (
              <div className="empty-keywords-box">
                <span>📋</span>
                <span>Add a target job description above to analyze keyword coverage.</span>
              </div>
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
                      <span className="keyword-dot"></span>
                      <span className="keyword-text">{item.term}</span>
                      {item.isCritical && <span className="critical-badge">Required</span>}
                    </span>
                  ))}
              </div>
            )}
          </div>

          {/* Subtle Heuristic Disclaimer Footnote */}
          <div className="heuristic-footnote">
            ℹ️ <strong>Heuristic Guidance:</strong> Automated checks are recommendations to enhance clarity and term presence, not an ATS guarantee. Only requirements explicitly stated as required in the JD are marked critical.
          </div>
        </div>
      )}
    </div>
  );
}
