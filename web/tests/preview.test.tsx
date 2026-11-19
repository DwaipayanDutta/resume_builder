import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { LivePreview } from "../src/components/LivePreview";
import { useResumeStore } from "../src/store";

describe("LivePreview component", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useResumeStore.getState().resetResume();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("successfully fetches and displays HTML preview and page count", async () => {
    const mockHtml = "<html><body><h1>Alex Morgan</h1></body></html>";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ html: mockHtml, pages: 1 }),
    });
    globalThis.fetch = fetchMock;

    render(<LivePreview />);

    // Fast-forward debounce timer
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/render/preview",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
    );

    const iframe = screen.getByTitle("Resume Live Preview") as HTMLIFrameElement;
    expect(iframe).toBeDefined();
    expect(iframe.srcdoc).toBe(mockHtml);
    expect(screen.getByText("1 page")).toBeDefined();
  });

  it("surfaces render errors explicitly", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "WeasyPrint syntax error",
    });
    globalThis.fetch = fetchMock;

    render(<LivePreview />);

    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(screen.getByText("Preview Error")).toBeDefined();
    expect(screen.getByText(/WeasyPrint syntax error/)).toBeDefined();
  });

  it("cancels stale requests and ensures the latest edit wins", async () => {
    const fetchMock = vi.fn().mockImplementation((_url, options) => {
      return new Promise((resolve, reject) => {
        // If aborted, reject with AbortError
        if (options.signal) {
          options.signal.addEventListener("abort", () => {
            const err = new DOMException("The user aborted a request.", "AbortError");
            reject(err);
          });
        }
        const body = JSON.parse(options.body);
        const text = body.summary?.value || "default";
        setTimeout(() => {
          resolve({
            ok: true,
            json: async () => ({
              html: `<html><body>${text}</body></html>`,
              pages: 1,
            }),
          });
        }, 100);
      });
    });
    globalThis.fetch = fetchMock;

    render(<LivePreview />);

    // Fast-forward initial mount
    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    // Trigger edit 1
    act(() => {
      useResumeStore.getState().updateSummary("Edit 1");
    });
    // Trigger edit 2 before edit 1 debounce finishes
    act(() => {
      vi.advanceTimersByTime(150);
      useResumeStore.getState().updateSummary("Edit 2");
    });

    // Advance timer past debounce (300ms) and latency (100ms)
    await act(async () => {
      vi.advanceTimersByTime(450);
    });

    // Latest edit wins: Edit 2 should be in iframe, Edit 1 was debounced/cancelled
    const iframe = screen.getByTitle("Resume Live Preview") as HTMLIFrameElement;
    expect(iframe.srcdoc).toContain("Edit 2");
    expect(iframe.srcdoc).not.toContain("Edit 1");
  });
});
