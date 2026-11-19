import { useState } from "react";

export interface EnhanceBulletModalProps {
  isOpen: boolean;
  bullet: string;
  jobDescription: string;
  onAccept: (enhancedBullet: string) => void;
  onClose: () => void;
}

export function EnhanceBulletModal({
  isOpen,
  bullet,
  jobDescription,
  onAccept,
  onClose,
}: EnhanceBulletModalProps) {
  const [backend, setBackend] = useState<"ollama" | "claude" | "litellm">("ollama");
  const [jdContext, setJdContext] = useState<string>(jobDescription);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [variations, setVariations] = useState<string[]>([]);
  const [selectedVariation, setSelectedVariation] = useState<string>("");
  const [disclosure, setDisclosure] = useState<string>("");

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setVariations([]);
    setSelectedVariation("");
    setDisclosure("");

    try {
      const res = await fetch("/api/enhance-bullet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bullet,
          job_description: jdContext || "General software / technical role",
          backend,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Enhancement failed" }));
        throw new Error(data.detail || `Server returned ${res.status}`);
      }

      const data = await res.json();
      setVariations(data.variations || []);
      setDisclosure(data.disclosure || "");
      if (data.variations && data.variations.length > 0) {
        setSelectedVariation(data.variations[0]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = () => {
    if (selectedVariation) {
      onAccept(selectedVariation);
      onClose();
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-container enhance-modal">
        <div className="modal-header">
          <h3>✨ Contextual Bullet Enhancement</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close dialog">
            &times;
          </button>
        </div>

        <div className="modal-body">
          <div className="enhance-section">
            <label className="enhance-label">Original Bullet Point</label>
            <div className="original-bullet-box">{bullet}</div>
          </div>

          <div className="enhance-grid">
            <div className="form-group">
              <label htmlFor="enhance-backend-select">AI Backend</label>
              <select
                id="enhance-backend-select"
                value={backend}
                onChange={(e) => setBackend(e.target.value as "ollama" | "claude" | "litellm")}
                className="select-input"
              >
                <option value="ollama">Ollama (Local &amp; Private)</option>
                <option value="claude">Anthropic Claude (Cloud)</option>
                <option value="litellm">LiteLLM (Cloud Multi-Provider)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="enhance-jd-context">Target Job Description Context</label>
              <textarea
                id="enhance-jd-context"
                rows={3}
                placeholder="Paste key responsibilities or requirements from the JD..."
                value={jdContext}
                onChange={(e) => setJdContext(e.target.value)}
              />
            </div>
          </div>

          {/* Privacy & Cloud Disclosure */}
          <div
            className={`disclosure-card ${
              backend === "ollama" ? "disclosure-local" : "disclosure-cloud"
            }`}
          >
            {backend === "ollama" ? (
              <p>
                🔒 <strong>Local Processing:</strong> Content is processed locally on your
                machine via Ollama. No resume data is transmitted externally.
              </p>
            ) : (
              <p>
                ☁️ <strong>Cloud Disclosure:</strong> Selected bullet text and JD context will
                be transmitted externally to {backend === "claude" ? "Anthropic Claude" : "LiteLLM"}.
                API credentials are kept server-side.
              </p>
            )}
          </div>

          {error && <div className="enhance-error-alert" role="alert">{error}</div>}

          {variations.length > 0 && (
            <div className="variations-container">
              <label className="enhance-label">
                Select an Enhanced Variation (2–3 factual, action-oriented options):
              </label>
              {disclosure && <div className="api-disclosure-tag">{disclosure}</div>}
              <div className="variations-list">
                {variations.map((v, i) => (
                  <label
                    key={i}
                    className={`variation-card ${selectedVariation === v ? "selected" : ""}`}
                  >
                    <input
                      type="radio"
                      name="bullet-variation"
                      value={v}
                      checked={selectedVariation === v}
                      onChange={() => setSelectedVariation(v)}
                    />
                    <div className="variation-text">{v}</div>
                  </label>
                ))}
              </div>
              <p className="factual-notice">
                ℹ️ Variations preserve factual accuracy and do not fabricate claims. Use
                [ADD METRIC] if specific numbers need to be confirmed.
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          {variations.length === 0 ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={loading || !bullet.trim()}
            >
              {loading ? "Generating..." : "Generate Variations"}
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleAccept}
              disabled={!selectedVariation}
            >
              Accept Variation
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
