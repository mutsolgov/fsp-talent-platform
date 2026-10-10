// src/stores/useShortlistStore.ts
import { create } from './zustand-lite';

export interface ShortlistCandidate {
  id: number;
  maskedCode: string;
  specialization: string;
  verifiedGrade: string;
  finalScore: number;
  initialScore: number;
  isPinned: boolean;
}

export interface ShortlistState {
  shortlistId: number | null;
  needId: number | null;
  pinnedIds: number[];
  deltaScores: Record<number, number>;
  candidates: ShortlistCandidate[];
  setShortlist: (id: number, needId: number, items: ShortlistCandidate[]) => void;
  togglePin: (candidateId: number) => void;
  pinCandidate: (candidateId: number) => void;
  unpinCandidate: (candidateId: number) => void;
  updateScoresAfterRefine: (scoreDeltas: Record<number, number>) => void;
}

export const useShortlistStore = create<ShortlistState>((set) => ({
  shortlistId: null,
  needId: null,
  pinnedIds: [],
  deltaScores: {},
  candidates: [],
  setShortlist: (shortlistId, needId, candidates) =>
    set({
      shortlistId,
      needId,
      candidates,
      pinnedIds: candidates.filter((c) => c.isPinned).map((c) => c.id),
      deltaScores: {},
    }),
  togglePin: (candidateId) =>
    set((state) => {
      const isPinned = state.pinnedIds.includes(candidateId);
      const nextPinned = isPinned
        ? state.pinnedIds.filter((id) => id !== candidateId)
        : [...state.pinnedIds, candidateId];
      const nextCandidates = state.candidates.map((c) =>
        c.id === candidateId ? { ...c, isPinned: !isPinned } : c
      );
      return { pinnedIds: nextPinned, candidates: nextCandidates };
    }),
  pinCandidate: (candidateId) =>
    set((state) => ({
      pinnedIds: state.pinnedIds.includes(candidateId) ? state.pinnedIds : [...state.pinnedIds, candidateId],
      candidates: state.candidates.map((c) => (c.id === candidateId ? { ...c, isPinned: true } : c)),
    })),
  unpinCandidate: (candidateId) =>
    set((state) => ({
      pinnedIds: state.pinnedIds.filter((id) => id !== candidateId),
      candidates: state.candidates.map((c) => (c.id === candidateId ? { ...c, isPinned: false } : c)),
    })),
  updateScoresAfterRefine: (scoreDeltas) =>
    set((state) => ({
      deltaScores: { ...state.deltaScores, ...scoreDeltas },
      candidates: state.candidates.map((c) => ({
        ...c,
        finalScore: scoreDeltas[c.id] !== undefined ? scoreDeltas[c.id] : c.finalScore,
      })),
    })),
}));
