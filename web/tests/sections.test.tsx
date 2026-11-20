import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, act, cleanup } from "@testing-library/react";
import { useResumeStore } from "../src/store";
import { SectionForm } from "../src/components/SectionForm";
import { LivePreview } from "../src/components/LivePreview";
import { AtsChecklistCard } from "../src/components/AtsChecklistCard";
import { evaluateAtsChecklist, checkPlaceholders } from "../src/utils/atsChecker";
import { createDefaultResume, createDefaultVerifiable } from "../src/schemas";

describe("Projects and Certifications editing", () => {
  beforeEach(() => {
    cleanup();
    useResumeStore.getState().resetResume();
  });

  it("routes navigation to real Projects and Certifications forms", () => {
    useResumeStore.getState().selectSection("projects");
    const { rerender } = render(<SectionForm />);
    expect(screen.getByRole("heading", { name: "Projects" })).toBeDefined();

    act(() => useResumeStore.getState().selectSection("certifications"));
    rerender(<SectionForm />);
    expect(screen.getByRole("heading", { name: "Certifications" })).toBeDefined();
  });

  it("adds, edits, toggles and deletes projects with undo", () => {
    const s = useResumeStore.getState();
    s.addProject();
    s.updateProjectField(0, "name", "OSS Toolkit");
    s.updateProjectBullet(0, 0, "Built a CLI");
    s.addProjectBullet(0, "Wrote docs");
    s.toggleProjectIncluded(0);

    let proj = useResumeStore.getState().resume.projects[0];
    expect(proj.name.value).toBe("OSS Toolkit");
    expect(proj.bullets.map((b) => b.value)).toEqual(["Built a CLI", "Wrote docs"]);
    expect(proj.included).toBe(false);

    useResumeStore.getState().undo();
    expect(useResumeStore.getState().resume.projects[0].included).toBe(true);

    useResumeStore.getState().deleteProjectBullet(0, 0);
    proj = useResumeStore.getState().resume.projects[0];
    expect(proj.bullets.map((b) => b.value)).toEqual(["Wrote docs"]);

    useResumeStore.getState().deleteProject(0);
    expect(useResumeStore.getState().resume.projects).toHaveLength(0);
  });

  it("adds certifications through the form", () => {
    useResumeStore.getState().selectSection("certifications");
    render(<SectionForm />);
    const input = screen.getByPlaceholderText(/AWS Certified/i);
    fireEvent.change(input, { target: { value: "CKA" } });
    fireEvent.click(screen.getByText("Add Certification"));
    expect(useResumeStore.getState().resume.certifications[0].value).toBe("CKA");

    act(() => useResumeStore.getState().updateCertification(0, "CKAD"));
    expect(useResumeStore.getState().resume.certifications[0].value).toBe("CKAD");
    act(() => useResumeStore.getState().deleteCertification(0));
    expect(useResumeStore.getState().resume.certifications).toHaveLength(0);
  });
});

describe("Page count is never estimated", () => {
  beforeEach(() => {
    cleanup();
    useResumeStore.getState().resetResume();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("reports unknown page count instead of assuming 1", () => {
    const report = evaluateAtsChecklist(createDefaultResume(), "", null, "weasyprint missing");
    expect(report.pageCount.pages).toBeNull();
    expect(report.pageCount.isOptimal).toBe(false);
    expect(report.pageCount.message).toContain("weasyprint missing");
  });

  it("preview propagates a null page count and error into the store", async () => {
    vi.useFakeTimers();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ html: "<p>x</p>", pages: null, page_count_error: "no pango" }),
    });
    render(<LivePreview />);
    await act(async () => {
      vi.advanceTimersByTime(350);
    });
    expect(screen.getByText("Page count unavailable")).toBeDefined();
    expect(useResumeStore.getState().previewPages).toBeNull();
    expect(useResumeStore.getState().previewPageError).toBe("no pango");

    render(<AtsChecklistCard />);
    expect(screen.getByTestId("page-count-check").textContent).toContain(
      "Actual Rendered Pages: unknown"
    );
  });

  it("preview iframe is fully sandboxed", async () => {
    vi.useFakeTimers();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ html: "<p>x</p>", pages: 1 }),
    });
    render(<LivePreview />);
    await act(async () => {
      vi.advanceTimersByTime(350);
    });
    const iframe = screen.getByTitle("Resume Live Preview");
    expect(iframe.getAttribute("sandbox")).toBe("");
  });

  it("detects placeholders in project bullets", () => {
    const resume = createDefaultResume();
    resume.projects.push({
      name: createDefaultVerifiable("Tool"),
      bullets: [createDefaultVerifiable("Sped up builds by [ADD METRIC]")],
      included: true,
    });
    expect(checkPlaceholders(resume)).toEqual(["[ADD METRIC]"]);
  });
});
