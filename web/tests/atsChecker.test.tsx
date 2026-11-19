import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  extractJobKeywords,
  checkPlaceholders,
  checkActionVerbs,
  evaluateAtsChecklist,
} from "../src/utils/atsChecker";
import { AtsChecklistCard } from "../src/components/AtsChecklistCard";
import { useResumeStore } from "../src/store";
import { createDefaultResume, createDefaultVerifiable } from "../src/schemas";

describe("ATS Checker utilities", () => {
  it("extracts keywords and tags critical requirements accurately", () => {
    const jd = `
      We are looking for a Senior Python Developer.
      Required: Kubernetes and Docker experience is mandatory.
      Nice to have: GraphQL familiarity.
    `;
    const keywords = extractJobKeywords(jd);
    const kubernetes = keywords.find((k) => k.term === "kubernetes");
    const python = keywords.find((k) => k.term === "python");
    const graphql = keywords.find((k) => k.term === "graphql");

    expect(kubernetes).toBeDefined();
    expect(kubernetes?.isCritical).toBe(true);

    expect(python).toBeDefined();
    expect(python?.isCritical).toBe(false);

    expect(graphql).toBeDefined();
    expect(graphql?.isCritical).toBe(false);
  });

  it("identifies unresolved placeholders", () => {
    const resume = createDefaultResume();
    resume.experience = [
      {
        company: createDefaultVerifiable("TechCorp"),
        title: createDefaultVerifiable("Engineer"),
        start_date: createDefaultVerifiable("2020"),
        end_date: createDefaultVerifiable("Present"),
        bullets: [
          createDefaultVerifiable("Improved query latency by [ADD METRIC]."),
          createDefaultVerifiable("Completed [TODO] feature rollout."),
        ],
        included: true,
      },
    ];

    const placeholders = checkPlaceholders(resume);
    expect(placeholders.length).toBe(2);
    expect(placeholders).toContain("[ADD METRIC]");
    expect(placeholders).toContain("[TODO]");

    resume.experience[0].bullets[0].value = "Improved query latency by 45%.";
    resume.experience[0].bullets[1].value = "Completed core billing feature rollout.";
    expect(checkPlaceholders(resume).length).toBe(0);
  });

  it("checks action verbs for experience bullets", () => {
    const resume = createDefaultResume();
    resume.experience = [
      {
        company: createDefaultVerifiable("TechCorp"),
        title: createDefaultVerifiable("Engineer"),
        start_date: createDefaultVerifiable("2020"),
        end_date: createDefaultVerifiable("Present"),
        bullets: [
          createDefaultVerifiable("Architected cloud native telemetry platform."),
          createDefaultVerifiable("Led team of 5 engineers to deliver quarterly goals."),
          createDefaultVerifiable("Responsible for daily maintenance of databases."),
        ],
        included: true,
      },
    ];

    const result = checkActionVerbs(resume);
    expect(result.total).toBe(3);
    expect(result.withVerb).toBe(2);
    expect(result.percentage).toBe(67);
  });

  it("evaluates page count limits correctly without text-length estimation", () => {
    const resume = createDefaultResume();
    const optimalReport = evaluateAtsChecklist(resume, "python developer", 2);
    expect(optimalReport.pageCount.isOptimal).toBe(true);
    expect(optimalReport.pageCount.pages).toBe(2);

    const exceedReport = evaluateAtsChecklist(resume, "python developer", 3);
    expect(exceedReport.pageCount.isOptimal).toBe(false);
    expect(exceedReport.pageCount.message).toContain("exceeds recommended 2-page limit");
  });

  it("computes matched and missing keywords against resume content", () => {
    const resume = createDefaultResume();
    resume.skills = [createDefaultVerifiable("Python"), createDefaultVerifiable("FastAPI")];
    resume.experience = [
      {
        company: createDefaultVerifiable("TechCorp"),
        title: createDefaultVerifiable("Engineer"),
        start_date: createDefaultVerifiable("2020"),
        end_date: createDefaultVerifiable("Present"),
        bullets: [
          createDefaultVerifiable("Engineered high-throughput microservices using Docker."),
        ],
        included: true,
      },
    ];

    const jd = "Seeking Python engineer with Docker and Rust background.";
    const report = evaluateAtsChecklist(resume, jd, 1);

    const matched = report.keywords.items.filter((k) => k.isMatched).map((k) => k.term);
    const missing = report.keywords.items.filter((k) => !k.isMatched).map((k) => k.term);

    expect(matched).toContain("python");
    expect(matched).toContain("docker");
    expect(missing).toContain("rust");
  });
});

describe("AtsChecklistCard Component", () => {
  beforeEach(() => {
    useResumeStore.getState().resetResume();
    useResumeStore.getState().setTargetJobDescription("");
    useResumeStore.getState().setPreviewPages(1);
  });

  it("renders heuristic notice and updates checklist live", () => {
    render(<AtsChecklistCard />);

    expect(screen.getByText("Heuristic Guidance")).toBeDefined();
    expect(screen.getByText(/not an ATS guarantee/i)).toBeDefined();

    // Check page count display
    const pageCheck = screen.getByTestId("page-count-check");
    expect(pageCheck.textContent).toContain("Actual Rendered Pages: 1");

    // Check placeholder display
    const placeholdersCheck = screen.getByTestId("placeholders-check");
    expect(placeholdersCheck.textContent).toContain("Metric Placeholders: All resolved");
  });

  it("displays missing keywords when target job description is provided", () => {
    render(<AtsChecklistCard />);

    const textarea = screen.getByPlaceholderText(/Paste target job description/i);
    fireEvent.change(textarea, {
      target: { value: "Must have Kubernetes and Terraform certifications." },
    });

    expect(useResumeStore.getState().targetJobDescription).toBe(
      "Must have Kubernetes and Terraform certifications."
    );

    expect(screen.getByTestId("keywords-grid")).toBeDefined();
    expect(screen.getByTestId("keyword-kubernetes")).toBeDefined();
    expect(screen.getByTestId("keyword-terraform")).toBeDefined();
  });
});
