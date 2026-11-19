import { describe, it, expect } from "vitest";
import {
  resumeSchema,
  createDefaultResume,
  createDefaultVerifiable,
} from "../src/schemas";

describe("schemas validation", () => {
  it("validates a default resume structure", () => {
    const resume = createDefaultResume();
    const parsed = resumeSchema.safeParse(resume);
    expect(parsed.success).toBe(true);
  });

  it("validates a complete resume with all sections typed", () => {
    const fullResume = {
      contact: {
        name: createDefaultVerifiable("Alex Morgan"),
        email: createDefaultVerifiable("alex@example.com"),
        phone: createDefaultVerifiable("+1 555-0100"),
        linkedin: createDefaultVerifiable("https://linkedin.com/in/alex"),
        location: createDefaultVerifiable("San Francisco, CA"),
      },
      summary: createDefaultVerifiable("Senior Program Manager"),
      experience: [
        {
          company: createDefaultVerifiable("Northwind"),
          title: createDefaultVerifiable("Senior PM"),
          start_date: createDefaultVerifiable("03/2021"),
          end_date: createDefaultVerifiable("Present"),
          bullets: [
            createDefaultVerifiable("Delivered 6 cloud programs."),
            createDefaultVerifiable("Reduced latency by 20%."),
          ],
          included: true,
        },
      ],
      projects: [
        {
          name: createDefaultVerifiable("AI Resume Tailor"),
          description: createDefaultVerifiable("ATS resume generator"),
          bullets: [createDefaultVerifiable("Implemented with React and Python")],
          included: true,
        },
      ],
      education: [
        {
          institution: createDefaultVerifiable("UC Berkeley"),
          degree: createDefaultVerifiable("B.S. Computer Science"),
          details: [],
          included: true,
        },
      ],
      skills: [createDefaultVerifiable("TypeScript"), createDefaultVerifiable("Python")],
      certifications: [createDefaultVerifiable("PMP")],
      custom_sections: [
        {
          name: "Interests",
          items: [createDefaultVerifiable("Open Source"), createDefaultVerifiable("Running")],
          included: true,
        },
      ],
      section_order: ["summary", "experience", "education", "skills"],
      template_id: "ats_classic",
    };

    const parsed = resumeSchema.safeParse(fullResume);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.projects.length).toBe(1);
      expect(parsed.data.projects[0].name.value).toBe("AI Resume Tailor");
      expect(parsed.data.education[0].degree.value).toBe("B.S. Computer Science");
      expect(parsed.data.custom_sections[0].name).toBe("Interests");
    }
  });

  it("fails validation when fields are invalid", () => {
    const invalidResume = {
      contact: {
        name: { value: 12345 }, // invalid type
      },
    };
    const parsed = resumeSchema.safeParse(invalidResume);
    expect(parsed.success).toBe(false);
  });
});
