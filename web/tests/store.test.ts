import { describe, it, expect, beforeEach } from "vitest";
import { useResumeStore } from "../src/store";

describe("useResumeStore", () => {
  beforeEach(() => {
    useResumeStore.getState().resetResume();
  });

  it("handles initial loaded state safely", () => {
    const state = useResumeStore.getState();
    expect(state.isLoaded).toBe(true);
    expect(state.resume).toBeDefined();
    expect(state.resume.section_order.length).toBeGreaterThan(0);
    expect(state.selectedSection).toBe("experience");
  });

  it("updates contact and summary fields and updates history", () => {
    const store = useResumeStore.getState();
    store.updateContact("name", "Jane Doe");
    expect(useResumeStore.getState().resume.contact.name.value).toBe("Jane Doe");
    expect(useResumeStore.getState().past.length).toBe(1);

    store.updateSummary("Experienced Engineering Leader");
    expect(useResumeStore.getState().resume.summary?.value).toBe(
      "Experienced Engineering Leader"
    );
    expect(useResumeStore.getState().past.length).toBe(2);

    // Test Undo
    useResumeStore.getState().undo();
    expect(useResumeStore.getState().resume.summary?.value).toBe("");

    // Test Redo
    useResumeStore.getState().redo();
    expect(useResumeStore.getState().resume.summary?.value).toBe(
      "Experienced Engineering Leader"
    );
  });

  it("adds, edits, and reorders experience entries", () => {
    const store = useResumeStore.getState();
    store.addExperience();
    expect(useResumeStore.getState().resume.experience.length).toBe(1);

    store.updateExperienceField(0, "title", "Lead Architect");
    store.updateExperienceField(0, "company", "Acme Inc");
    expect(useResumeStore.getState().resume.experience[0].title.value).toBe(
      "Lead Architect"
    );
    expect(useResumeStore.getState().resume.experience[0].company.value).toBe(
      "Acme Inc"
    );

    // Add a second experience entry
    store.addExperience();
    store.updateExperienceField(1, "title", "Staff Engineer");

    // Reorder experience
    useResumeStore.getState().reorderExperience(0, 1);
    expect(useResumeStore.getState().resume.experience[0].title.value).toBe(
      "Staff Engineer"
    );
    expect(useResumeStore.getState().resume.experience[1].title.value).toBe(
      "Lead Architect"
    );
  });

  it("reorders experience bullets and updates store state", () => {
    const store = useResumeStore.getState();
    store.addExperience();
    store.updateBullet(0, 0, "Bullet 1: Initial deployment");
    store.addBullet(0, "Bullet 2: Automated CI/CD");
    store.addBullet(0, "Bullet 3: Optimized latency");

    const bulletsBefore = useResumeStore.getState().resume.experience[0].bullets;
    expect(bulletsBefore.length).toBe(3);
    expect(bulletsBefore[0].value).toBe("Bullet 1: Initial deployment");
    expect(bulletsBefore[1].value).toBe("Bullet 2: Automated CI/CD");
    expect(bulletsBefore[2].value).toBe("Bullet 3: Optimized latency");

    // Reorder Bullet 0 to position 2
    useResumeStore.getState().reorderBullets(0, 0, 2);

    const bulletsAfter = useResumeStore.getState().resume.experience[0].bullets;
    expect(bulletsAfter[0].value).toBe("Bullet 2: Automated CI/CD");
    expect(bulletsAfter[1].value).toBe("Bullet 3: Optimized latency");
    expect(bulletsAfter[2].value).toBe("Bullet 1: Initial deployment");

    // Verify undo restores original bullet order
    useResumeStore.getState().undo();
    const bulletsRestored = useResumeStore.getState().resume.experience[0].bullets;
    expect(bulletsRestored[0].value).toBe("Bullet 1: Initial deployment");
  });

  it("handles navigation and section reordering", () => {
    const store = useResumeStore.getState();
    store.selectSection("education");
    expect(useResumeStore.getState().selectedSection).toBe("education");

    const initialFirst = useResumeStore.getState().resume.section_order[0];
    const initialSecond = useResumeStore.getState().resume.section_order[1];

    store.reorderSections(0, 1);
    expect(useResumeStore.getState().resume.section_order[0]).toBe(initialSecond);
    expect(useResumeStore.getState().resume.section_order[1]).toBe(initialFirst);
  });

  it("edits education and skills", () => {
    const store = useResumeStore.getState();
    store.addEducation();
    store.updateEducationField(0, "institution", "MIT");
    store.updateEducationField(0, "degree", "M.S.");
    expect(useResumeStore.getState().resume.education[0].institution.value).toBe("MIT");
    expect(useResumeStore.getState().resume.education[0].degree.value).toBe("M.S.");

    store.addSkill("TypeScript");
    store.addSkill("React");
    expect(useResumeStore.getState().resume.skills.length).toBe(2);
    expect(useResumeStore.getState().resume.skills[0].value).toBe("TypeScript");

    store.deleteSkill(0);
    expect(useResumeStore.getState().resume.skills.length).toBe(1);
    expect(useResumeStore.getState().resume.skills[0].value).toBe("React");
  });
});
