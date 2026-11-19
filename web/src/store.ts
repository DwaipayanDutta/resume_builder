import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { current } from "immer";
import {
  type Resume,
  createDefaultResume,
  createDefaultVerifiable,
} from "./schemas";

type Snapshot = Resume;

export interface ResumeState {
  resume: Resume;
  isLoaded: boolean;
  past: Snapshot[];
  future: Snapshot[];
  selectedSection: string;
  autoSaveStatus: "saved" | "saving" | "unsaved";

  // Actions
  setResume: (r: Resume) => void;
  resetResume: () => void;
  selectSection: (s: string) => void;
  reorderSections: (from: number, to: number) => void;

  // Contact & Summary
  updateContact: (
    field: "name" | "email" | "phone" | "linkedin" | "location",
    value: string
  ) => void;
  updateSummary: (value: string) => void;

  // Experience
  addExperience: () => void;
  deleteExperience: (index: number) => void;
  reorderExperience: (from: number, to: number) => void;
  updateExperienceField: (
    index: number,
    field: "company" | "title" | "start_date" | "end_date",
    value: string
  ) => void;
  toggleExperienceIncluded: (index: number) => void;

  // Bullets
  addBullet: (expIndex: number, value?: string) => void;
  deleteBullet: (expIndex: number, bulletIndex: number) => void;
  updateBullet: (expIndex: number, bulletIndex: number, value: string) => void;
  reorderBullets: (expIndex: number, from: number, to: number) => void;

  // Education
  addEducation: () => void;
  deleteEducation: (index: number) => void;
  updateEducationField: (
    index: number,
    field: "institution" | "degree",
    value: string
  ) => void;
  toggleEducationIncluded: (index: number) => void;

  // Skills
  addSkill: (value?: string) => void;
  deleteSkill: (index: number) => void;
  updateSkill: (index: number, value: string) => void;

  // History & Status
  undo: () => void;
  redo: () => void;
  markUnsaved: () => void;
  markSaved: () => void;
}

const pushPast = (state: ResumeState) => {
  state.past.push(current(state.resume));
  if (state.past.length > 50) state.past.shift();
  state.future = [];
  state.autoSaveStatus = "unsaved";
};

export const useResumeStore = create<ResumeState>()(
  immer((set) => ({
    resume: createDefaultResume(),
    isLoaded: true,
    past: [],
    future: [],
    selectedSection: "experience",
    autoSaveStatus: "saved",

    setResume: (r) =>
      set((s) => {
        s.resume = r;
        s.isLoaded = true;
        s.past = [];
        s.future = [];
        s.autoSaveStatus = "saved";
      }),

    resetResume: () =>
      set((s) => {
        s.resume = createDefaultResume();
        s.past = [];
        s.future = [];
        s.autoSaveStatus = "saved";
      }),

    selectSection: (sec) =>
      set((s) => {
        s.selectedSection = sec;
      }),

    reorderSections: (from, to) =>
      set((s) => {
        if (from === to) return;
        if (
          from < 0 ||
          from >= s.resume.section_order.length ||
          to < 0 ||
          to >= s.resume.section_order.length
        )
          return;
        pushPast(s);
        const [moved] = s.resume.section_order.splice(from, 1);
        s.resume.section_order.splice(to, 0, moved);
      }),

    updateContact: (field, value) =>
      set((s) => {
        pushPast(s);
        if (field === "name") {
          s.resume.contact.name.value = value;
          s.resume.contact.name.source = "user_provided";
          s.resume.contact.name.verification_status = "verified";
        } else {
          if (!s.resume.contact[field]) {
            s.resume.contact[field] = createDefaultVerifiable(value);
          } else {
            s.resume.contact[field]!.value = value;
            s.resume.contact[field]!.source = "user_provided";
            s.resume.contact[field]!.verification_status = "verified";
          }
        }
      }),

    updateSummary: (value) =>
      set((s) => {
        pushPast(s);
        if (!s.resume.summary) {
          s.resume.summary = createDefaultVerifiable(value);
        } else {
          s.resume.summary.value = value;
          s.resume.summary.source = "user_provided";
          s.resume.summary.verification_status = "verified";
        }
      }),

    addExperience: () =>
      set((s) => {
        pushPast(s);
        s.resume.experience.push({
          company: createDefaultVerifiable(""),
          title: createDefaultVerifiable(""),
          start_date: createDefaultVerifiable(""),
          end_date: createDefaultVerifiable("Present"),
          bullets: [createDefaultVerifiable("")],
          included: true,
        });
      }),

    deleteExperience: (index) =>
      set((s) => {
        if (index < 0 || index >= s.resume.experience.length) return;
        pushPast(s);
        s.resume.experience.splice(index, 1);
      }),

    reorderExperience: (from, to) =>
      set((s) => {
        if (from === to) return;
        if (
          from < 0 ||
          from >= s.resume.experience.length ||
          to < 0 ||
          to >= s.resume.experience.length
        )
          return;
        pushPast(s);
        const [moved] = s.resume.experience.splice(from, 1);
        s.resume.experience.splice(to, 0, moved);
      }),

    updateExperienceField: (index, field, value) =>
      set((s) => {
        const exp = s.resume.experience[index];
        if (!exp) return;
        pushPast(s);
        exp[field].value = value;
        exp[field].source = "user_provided";
        exp[field].verification_status = "verified";
      }),

    toggleExperienceIncluded: (index) =>
      set((s) => {
        const exp = s.resume.experience[index];
        if (!exp) return;
        pushPast(s);
        exp.included = !exp.included;
      }),

    addBullet: (expIndex, value = "") =>
      set((s) => {
        const exp = s.resume.experience[expIndex];
        if (!exp) return;
        pushPast(s);
        exp.bullets.push(createDefaultVerifiable(value));
      }),

    deleteBullet: (expIndex, bulletIndex) =>
      set((s) => {
        const exp = s.resume.experience[expIndex];
        if (!exp || bulletIndex < 0 || bulletIndex >= exp.bullets.length) return;
        pushPast(s);
        exp.bullets.splice(bulletIndex, 1);
      }),

    updateBullet: (expIndex, bulletIndex, value) =>
      set((s) => {
        const exp = s.resume.experience[expIndex];
        if (!exp || !exp.bullets[bulletIndex]) return;
        pushPast(s);
        exp.bullets[bulletIndex].value = value;
        exp.bullets[bulletIndex].source = "user_provided";
        exp.bullets[bulletIndex].verification_status = "verified";
      }),

    reorderBullets: (expIndex, from, to) =>
      set((s) => {
        if (from === to) return;
        const exp = s.resume.experience[expIndex];
        if (
          !exp ||
          from < 0 ||
          from >= exp.bullets.length ||
          to < 0 ||
          to >= exp.bullets.length
        )
          return;
        pushPast(s);
        const [moved] = exp.bullets.splice(from, 1);
        exp.bullets.splice(to, 0, moved);
      }),

    addEducation: () =>
      set((s) => {
        pushPast(s);
        s.resume.education.push({
          institution: createDefaultVerifiable(""),
          degree: createDefaultVerifiable(""),
          details: [],
          included: true,
        });
      }),

    deleteEducation: (index) =>
      set((s) => {
        if (index < 0 || index >= s.resume.education.length) return;
        pushPast(s);
        s.resume.education.splice(index, 1);
      }),

    updateEducationField: (index, field, value) =>
      set((s) => {
        const edu = s.resume.education[index];
        if (!edu) return;
        pushPast(s);
        edu[field].value = value;
        edu[field].source = "user_provided";
        edu[field].verification_status = "verified";
      }),

    toggleEducationIncluded: (index) =>
      set((s) => {
        const edu = s.resume.education[index];
        if (!edu) return;
        pushPast(s);
        edu.included = !edu.included;
      }),

    addSkill: (value = "") =>
      set((s) => {
        pushPast(s);
        s.resume.skills.push(createDefaultVerifiable(value));
      }),

    deleteSkill: (index) =>
      set((s) => {
        if (index < 0 || index >= s.resume.skills.length) return;
        pushPast(s);
        s.resume.skills.splice(index, 1);
      }),

    updateSkill: (index, value) =>
      set((s) => {
        const skill = s.resume.skills[index];
        if (!skill) return;
        pushPast(s);
        skill.value = value;
        skill.source = "user_provided";
        skill.verification_status = "verified";
      }),

    undo: () =>
      set((s) => {
        if (!s.past.length) return;
        s.future.push(current(s.resume));
        s.resume = s.past.pop()!;
        s.autoSaveStatus = "unsaved";
      }),

    redo: () =>
      set((s) => {
        if (!s.future.length) return;
        s.past.push(current(s.resume));
        s.resume = s.future.pop()!;
        s.autoSaveStatus = "unsaved";
      }),

    markUnsaved: () =>
      set((s) => {
        s.autoSaveStatus = "unsaved";
      }),
    markSaved: () =>
      set((s) => {
        s.autoSaveStatus = "saved";
      }),
  }))
);
