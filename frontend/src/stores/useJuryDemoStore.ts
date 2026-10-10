// src/stores/useJuryDemoStore.ts
import { create } from './zustand-lite';

export type DemoPersona =
  | 'candidate_with_fsp'
  | 'candidate_without_fsp'
  | 'candidate_fsp'
  | 'candidate_non_fsp'
  | 'employer'
  | 'admin';

export interface JuryDemoState {
  activePersona: DemoPersona;
  isCooldownBypassActive: boolean;
  benchmarkRunning: boolean;
  benchmarkProgress: number; // 0..100
  switchPersona: (persona: DemoPersona) => void;
  setActivePersona: (persona: DemoPersona) => void;
  toggleCooldownBypass: () => void;
  setCooldownBypass: (active: boolean) => void;
  setBenchmarkProgress: (running: boolean, progress: number) => void;
}

export const useJuryDemoStore = create<JuryDemoState>((set) => ({
  activePersona: 'candidate_with_fsp',
  isCooldownBypassActive: false,
  benchmarkRunning: false,
  benchmarkProgress: 0,
  switchPersona: (activePersona) => set({ activePersona }),
  setActivePersona: (activePersona) => set({ activePersona }),
  toggleCooldownBypass: () =>
    set((state) => ({ isCooldownBypassActive: !state.isCooldownBypassActive })),
  setCooldownBypass: (isCooldownBypassActive) => set({ isCooldownBypassActive }),
  setBenchmarkProgress: (benchmarkRunning, benchmarkProgress) =>
    set({ benchmarkRunning, benchmarkProgress }),
}));
