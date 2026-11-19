import { useEffect, useState, useRef } from "react";
import { useResumeStore } from "../store";

export interface PreviewData {
  html: string;
  pages: number;
}

export function LivePreview() {
  const resume = useResumeStore((s) => s.resume);
  const isLoaded = useResumeStore((s) => s.isLoaded);
  const setPreviewPages = useResumeStore((s) => s.setPreviewPages);

  const [html, setHtml] = useState<string>("");
  const [pages, setPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef<number>(0);

  useEffect(() => {
    if (!isLoaded || !resume) return;

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    const currentReqId = ++requestIdRef.current;

    setLoading(true);
    setError(null);

    const timer = setTimeout(async () => {
      try {
        const res = await fetch("/api/render/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(resume),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`Preview failed (${res.status}): ${errText}`);
        }

        const data: PreviewData = await res.json();

        // Ensure latest edit wins
        if (currentReqId === requestIdRef.current) {
          setHtml(data.html);
          setPages(data.pages);
          setPreviewPages(data.pages);
          setLoading(false);
          setError(null);
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // Stale request cancelled; ignore
          return;
        }
        if (currentReqId === requestIdRef.current) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    }, 300); // 300ms debounce

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [resume, isLoaded]);

  if (!isLoaded) {
    return (
      <div className="preview-container">
        <p className="loading-text">Loading preview...</p>
      </div>
    );
  }

  return (
    <div className="preview-container">
      <div className="preview-header-bar">
        <div className="preview-header-left">
          <span className="preview-title">Live Preview (A4)</span>
          {loading && <span className="preview-badge rendering">Rendering...</span>}
        </div>
        <div className="preview-header-right">
          <span className={`page-count-badge ${pages > 2 ? "badge-danger" : "badge-info"}`}>
            {pages} {pages === 1 ? "page" : "pages"}
          </span>
        </div>
      </div>

      {error ? (
        <div className="preview-error-card">
          <h4>Preview Error</h4>
          <p>{error}</p>
        </div>
      ) : (
        <div className="preview-frame-wrapper">
          <iframe
            title="Resume Live Preview"
            srcDoc={html}
            sandbox="allow-same-origin"
            className="preview-iframe"
          />
        </div>
      )}
    </div>
  );
}
