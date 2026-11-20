import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { Resume } from "./schemas";

type Snapshot = Resume;

interface State {
  resume: Resume;
  past: Snapshot[];
  future: Snapshot[];
  selectedSection: string;
  autoSaveStatus: "saved" | "saving" | "unsaved";
  setResume: (r: Resume) => void;
  reorderSections: (from: number, to: number) => void;
  reorderExperience: (from: number, to: number) => void;
  updateBullet: (expIndex: number, bulletIndex: number, value: string) => void;
  selectSection: (s: string) => void;
  undo: () => void;
  redo: () => void;
  markUnsaved: () => void;
  markSaved: () => void;
}

const pushPast = (state: State) => {
  state.past.push(structuredClone(state.resume));
  if (state.past.length > 50) state.past.shift();
  state.future = [];
  state.autoSaveStatus = "unsaved";
};

export const useResumeStore = create<State>()(
  immer((set) => ({
    resume: null as unknown as Resume,
    past: [],
    future: [],
    selectedSection: "experience",
    autoSaveStatus: "saved",

    setResume: (r) => set((s) => { s.resume = r; }),

    reorderSections: (from, to) => set((s) => {
      if (from === to) return;
      pushPast(s);
      const [moved] = s.resume.section_order.splice(from, 1);
      s.resume.section_order.splice(to, 0, moved);
    }),

    reorderExperience: (from, to) => set((s) => {
      if (from === to) return;
      pushPast(s);
      const [moved] = s.resume.experience.splice(from, 1);
      s.resume.experience.splice(to, 0, moved);
    }),

    updateBullet: (expIndex, bulletIndex, value) => set((s) => {
      pushPast(s);
      s.resume.experience[expIndex].bullets[bulletIndex].value = value;
      s.resume.experience[expIndex].bullets[bulletIndex].source = "user_provided";
      s.resume.experience[expIndex].bullets[bulletIndex].verification_status = "verified";
    }),

    selectSection: (sec) => set((s) => { s.selectedSection = sec; }),

    undo: () => set((s) => {
      if (!s.past.length) return;
      s.future.push(structuredClone(s.resume));
      s.resume = s.past.pop()!;
      s.autoSaveStatus = "unsaved";
    }),

    redo: () => set((s) => {
      if (!s.future.length) return;
      s.past.push(structuredClone(s.resume));
      s.resume = s.future.pop()!;
      s.autoSaveStatus = "unsaved";
    }),

    markUnsaved: () => set((s) => { s.autoSaveStatus = "unsaved"; }),
    markSaved: () => set((s) => { s.autoSaveStatus = "saved"; }),
  }))
);