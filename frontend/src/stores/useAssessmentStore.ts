// src/stores/useAssessmentStore.ts
import { create } from './zustand-lite';

export interface AssessmentState {
  sessionId: number | null;
  currentTaskIndex: number; // 1..12
  totalTasks: number; // 12
  timeRemainingSeconds: number;
  codeDrafts: Record<string | number, string>; // taskId -> uncommitted code
  setSession: (sessionId: number, currentTaskIndex: number, seconds: number) => void;
  setDraftCode: (taskId: string | number, code: string) => void;
  autoSaveDraft: (taskId: string | number, code: string) => void;
  setTaskIndex: (index: number) => void;
  tickTimer: () => void;
  nextTask: () => void;
  prevTask: () => void;
  submitCurrentTask: () => void;
}

export const useAssessmentStore = create<AssessmentState>((set) => ({
  sessionId: null,
  currentTaskIndex: 1,
  totalTasks: 12,
  timeRemainingSeconds: 5400,
  codeDrafts: {},
  setSession: (sessionId, currentTaskIndex, timeRemainingSeconds) =>
    set({ sessionId, currentTaskIndex, timeRemainingSeconds }),
  setDraftCode: (taskId, code) =>
    set((state) => ({ codeDrafts: { ...state.codeDrafts, [taskId]: code } })),
  autoSaveDraft: (taskId, code) =>
    set((state) => ({ codeDrafts: { ...state.codeDrafts, [taskId]: code } })),
  setTaskIndex: (index) =>
    set((state) => ({
      currentTaskIndex: Math.max(1, Math.min(state.totalTasks, index)),
    })),
  tickTimer: () =>
    set((state) => ({
      timeRemainingSeconds: Math.max(0, state.timeRemainingSeconds - 1),
    })),
  nextTask: () =>
    set((state) => ({
      currentTaskIndex: Math.min(state.totalTasks, state.currentTaskIndex + 1),
    })),
  prevTask: () =>
    set((state) => ({
      currentTaskIndex: Math.max(1, state.currentTaskIndex - 1),
    })),
  submitCurrentTask: () => {
    // Submits active draft
  },
}));
