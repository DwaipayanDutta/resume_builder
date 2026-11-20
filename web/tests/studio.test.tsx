import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { StudioDashboard } from "../src/components/StudioDashboard";
import { App } from "../src/App";

const CONFIG = {
  default_backend: null,
  default_model: null,
  backends: [
    { id: "qwen", label: "Local Qwen 2.5 3B (Ollama)", cloud: false, configured: true, hint: "" },
    { id: "litellm", label: "Any provider via LiteLLM (Claude, Gemini, OpenAI, ...)", cloud: true, configured: false, hint: "No API key found. Set ANTHROPIC_API_KEY" },
  ],
};

const BUILD = {
  job_id: "a".repeat(32),
  mode: "tailor",
  backend: "qwen",
  model: "qwen2.5:3b",
  disclosure: "Processed locally with Ollama: nothing left your computer.",
  pages: 2,
  fits_two_pages: true,
  placeholders: 1,
  warnings: ["1 [ADD METRIC] placeholder(s): replace with real numbers or delete them."],
  verification: ["DOCX OK"],
  files: {
    pdf: `/api/studio/files/${"a".repeat(32)}/pdf`,
    docx: `/api/studio/files/${"a".repeat(32)}/docx`,
    txt: `/api/studio/files/${"a".repeat(32)}/txt`,
  },
};

function json(data: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => data } as Response);
}

type Route = (url: string, init?: RequestInit) => Promise<Response>;

function mockFetch(routes: Record<string, Route>) {
  const fn = vi.fn((url: string, init?: RequestInit) => {
    const handler = routes[url];
    if (!handler) throw new Error(`Unexpected fetch ${url}`);
    return handler(url, init);
  });
  globalThis.fetch = fn as unknown as typeof fetch;
  return fn;
}

function uploadTxt(name = "New Resume.txt") {
  const input = screen.getByTestId("file-input") as HTMLInputElement;
  const file = new File(["Alex Morgan\nPM\n"], name, { type: "text/plain" });
  fireEvent.change(input, { target: { files: [file] } });
  return file;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("StudioDashboard", () => {
  it("uploads a TXT and builds a format-only PDF", async () => {
    const fetchMock = mockFetch({
      "/api/studio/config": () => json(CONFIG),
      "/api/studio/build": () => json({ ...BUILD, mode: "format", backend: null, disclosure: "Format only: no AI was used." }),
    });
    render(<StudioDashboard />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/studio/config"));

    uploadTxt();
    expect(screen.getByTestId("file-name").textContent).toBe("New Resume.txt");

    fireEvent.click(screen.getByTestId("build-button"));
    await screen.findByTestId("doc-row");

    const [, init] = fetchMock.mock.calls.find(([u]) => u === "/api/studio/build")!;
    const form = init!.body as FormData;
    expect(form.get("mode")).toBe("format");
    expect(form.get("basename")).toBe("New Resume");
    expect(form.get("jd_text")).toBeNull();

    const pdfLink = screen.getByRole("link", { name: "PDF" });
    expect(pdfLink.getAttribute("href")).toBe(`${BUILD.files.pdf}?download=1`);
    expect(screen.getByTitle("PDF preview").getAttribute("src")).toBe(BUILD.files.pdf);
    expect(screen.getByText(/no AI was used/)).toBeDefined();
  });

  it("rejects non-txt uploads", async () => {
    mockFetch({ "/api/studio/config": () => json(CONFIG) });
    render(<StudioDashboard />);
    uploadTxt("resume.pdf");
    expect(screen.getByRole("alert").textContent).toMatch(/\.txt/);
  });

  it("fetches the job description from a link and fills the form", async () => {
    mockFetch({
      "/api/studio/config": () => json(CONFIG),
      "/api/studio/jd-from-url": (_u, init) => {
        expect(JSON.parse(init!.body as string)).toEqual({ url: "https://jobs.example.com/42" });
        return json({ url: "x", title: "Senior PM", company: "Acme", text: "Lead programs. ".repeat(10), source: "json-ld" });
      },
    });
    render(<StudioDashboard />);
    fireEvent.change(screen.getByLabelText("Job posting link"), { target: { value: "https://jobs.example.com/42" } });
    fireEvent.click(screen.getByText("Fetch job"));

    await waitFor(() =>
      expect((screen.getByLabelText(/^Job description/) as HTMLTextAreaElement).value).toContain("Lead programs.")
    );
    expect((screen.getByLabelText("Job title") as HTMLInputElement).value).toBe("Senior PM");
    expect((screen.getByLabelText("Company (optional)") as HTMLInputElement).value).toBe("Acme");
    expect(screen.getByText(/Job description imported/)).toBeDefined();
  });

  it("shows a helpful error when the link can't be read", async () => {
    mockFetch({
      "/api/studio/config": () => json(CONFIG),
      "/api/studio/jd-from-url": () => json({ detail: "Paste the description text instead." }, false, 422),
    });
    render(<StudioDashboard />);
    fireEvent.change(screen.getByLabelText("Job posting link"), { target: { value: "https://linkedin.com/jobs/1" } });
    fireEvent.click(screen.getByText("Fetch job"));
    expect((await screen.findByRole("alert")).textContent).toContain("Paste the description");
  });

  it("tailors with the chosen backend and shows the cloud disclosure", async () => {
    const fetchMock = mockFetch({
      "/api/studio/config": () => json(CONFIG),
      "/api/studio/build": () => json(BUILD),
    });
    render(<StudioDashboard />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    uploadTxt();
    fireEvent.click(screen.getByRole("radio", { name: /Tailor with AI/ }));
    fireEvent.change(screen.getByLabelText("AI model"), { target: { value: "litellm" } });
    expect(screen.getByTestId("privacy-note").textContent).toMatch(/will be sent to Any provider via LiteLLM/);
    expect(screen.getByLabelText("Model name")).toBeDefined();
    expect(screen.getByTestId("privacy-note").textContent).toMatch(/ANTHROPIC_API_KEY/);
    fireEvent.change(screen.getByLabelText("AI model"), { target: { value: "qwen" } });
    expect(screen.getByTestId("privacy-note").textContent).toMatch(/Nothing is sent to the cloud/);

    // Validation before calling the server
    fireEvent.click(screen.getByTestId("build-button"));
    expect(screen.getByRole("alert").textContent).toMatch(/job title/);

    fireEvent.change(screen.getByLabelText("Job title"), { target: { value: "Senior PM" } });
    fireEvent.change(screen.getByLabelText(/^Job description/), { target: { value: "Own delivery. ".repeat(10) } });
    fireEvent.click(screen.getByTestId("build-button"));
    await screen.findByTestId("doc-row");

    const [, init] = fetchMock.mock.calls.find(([u]) => u === "/api/studio/build")!;
    const form = init!.body as FormData;
    expect(form.get("mode")).toBe("tailor");
    expect(form.get("backend")).toBe("qwen");
    expect(form.get("job_title")).toBe("Senior PM");
    expect(form.get("api_key")).toBeNull();
    expect(screen.getByText(/\[ADD METRIC\] placeholder/)).toBeDefined();
    expect(screen.getByText("AI tailored")).toBeDefined();
  });

  it("requires a model name for LiteLLM before building", async () => {
    const fetchMock = mockFetch({ "/api/studio/config": () => json(CONFIG) });
    render(<StudioDashboard />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    uploadTxt();
    fireEvent.click(screen.getByRole("radio", { name: /Tailor with AI/ }));
    fireEvent.change(screen.getByLabelText("AI model"), { target: { value: "litellm" } });
    fireEvent.change(screen.getByLabelText("Job title"), { target: { value: "PM" } });
    fireEvent.change(screen.getByLabelText(/^Job description/), { target: { value: "Own delivery. ".repeat(10) } });
    fireEvent.click(screen.getByTestId("build-button"));
    expect(screen.getByRole("alert").textContent).toMatch(/anthropic\/claude-sonnet-5-5/);
    expect(fetchMock).not.toHaveBeenCalledWith("/api/studio/build", expect.anything());
  });

  it("surfaces backend failures", async () => {
    mockFetch({
      "/api/studio/config": () => json(CONFIG),
      "/api/studio/build": () => json({ detail: "AI backend failed: Could not reach Ollama" }, false, 502),
    });
    render(<StudioDashboard />);
    uploadTxt();
    fireEvent.click(screen.getByTestId("build-button"));
    expect((await screen.findByRole("alert")).textContent).toContain("Could not reach Ollama");
  });

  it("preselects AI tailoring when the launcher configured a backend", async () => {
    mockFetch({
      "/api/studio/config": () => json({ ...CONFIG, default_backend: "litellm", default_model: "anthropic/claude-sonnet-5-5" }),
    });
    render(<StudioDashboard />);
    await waitFor(() =>
      expect(screen.getByRole("radio", { name: /Tailor with AI/ }).getAttribute("aria-checked")).toBe("true")
    );
    expect((screen.getByLabelText("AI model") as HTMLSelectElement).value).toBe("litellm");
    expect((screen.getByLabelText("Model name") as HTMLInputElement).value).toBe("anthropic/claude-sonnet-5-5");
  });

  it("ticks the get-started checklist as steps complete", async () => {
    mockFetch({ "/api/studio/config": () => json(CONFIG) });
    render(<StudioDashboard />);
    const list = screen.getByTestId("get-started");
    expect(list.querySelectorAll(".gs-step.done")).toHaveLength(0);
    uploadTxt();
    fireEvent.change(screen.getByLabelText(/^Job description/), { target: { value: "x".repeat(60) } });
    expect(list.querySelectorAll(".gs-step.done")).toHaveLength(2);
  });
});

describe("App navigation", () => {
  it("switches between dashboard and guided editor", async () => {
    mockFetch({
      "/api/auth/me": () => json({ id: 1, email: "a@example.com", name: "Alex Morgan" }),
      "/api/studio/config": () => json(CONFIG),
      "/api/render/preview": () => json({ html: "<p>x</p>", pages: 1 }),
    });
    render(<App />);
    expect((await screen.findByRole("tab", { name: "Dashboard" })).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByText("Your resume")).toBeDefined();
    fireEvent.click(screen.getByRole("tab", { name: "Guided editor" }));
    expect(screen.getByTitle("Resume Live Preview")).toBeDefined();
  });
});
