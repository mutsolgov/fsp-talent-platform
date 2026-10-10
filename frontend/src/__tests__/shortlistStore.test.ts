import { useShortlistStore, ShortlistCandidate } from '../stores/useShortlistStore';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const beforeEach: (fn: () => void | Promise<void>) => void;
declare const expect: any;

describe('useShortlistStore & Snapshot Diff-Ranking (LHH Reverse-Recruiting)', () => {
  const sampleCandidates: ShortlistCandidate[] = [
    {
      id: 101,
      maskedCode: 'CAND-0101',
      specialization: 'backend',
      verifiedGrade: 'senior',
      finalScore: 88.0,
      initialScore: 88.0,
      isPinned: false,
    },
    {
      id: 102,
      maskedCode: 'CAND-0102',
      specialization: 'backend',
      verifiedGrade: 'lead',
      finalScore: 92.5,
      initialScore: 92.5,
      isPinned: true,
    },
    {
      id: 103,
      maskedCode: 'CAND-0103',
      specialization: 'backend',
      verifiedGrade: 'middle',
      finalScore: 78.4,
      initialScore: 78.4,
      isPinned: false,
    },
  ];

  beforeEach(() => {
    // Reset store to initial state
    useShortlistStore.setState({
      shortlistId: null,
      needId: null,
      pinnedIds: [],
      deltaScores: {},
      candidates: [],
    });
  });

  describe('Initial Default State', () => {
    it('initializes with empty collection and zero pinned candidates', () => {
      const state = useShortlistStore.getState();

      expect(state.shortlistId).toBeNull();
      expect(state.needId).toBeNull();
      expect(state.pinnedIds).toEqual([]);
      expect(state.deltaScores).toEqual({});
      expect(state.candidates).toEqual([]);
    });
  });

  describe('Shortlist Ingestion via setShortlist', () => {
    it('populates candidates and automatically synchronizes pre-pinned IDs', () => {
      useShortlistStore.getState().setShortlist(5, 12, sampleCandidates);

      const state = useShortlistStore.getState();
      expect(state.shortlistId).toBe(5);
      expect(state.needId).toBe(12);
      expect(state.candidates).toHaveLength(3);

      // Candidate 102 was pre-pinned in sampleCandidates
      expect(state.pinnedIds).toEqual([102]);
    });
  });

  describe('Pinning Transitions: togglePin', () => {
    beforeEach(() => {
      useShortlistStore.getState().setShortlist(5, 12, sampleCandidates);
    });

    it('toggles unpinned candidate to pinned state', () => {
      // Toggle candidate 101 from unpinned to pinned
      useShortlistStore.getState().togglePin(101);

      const state = useShortlistStore.getState();
      expect(state.pinnedIds).toContain(101);
      expect(state.pinnedIds).toContain(102);

      const cand101 = state.candidates.find((c) => c.id === 101);
      expect(cand101?.isPinned).toBe(true);
    });

    it('toggles pinned candidate to unpinned state', () => {
      // Candidate 102 is currently pinned -> toggle should unpin
      useShortlistStore.getState().togglePin(102);

      const state = useShortlistStore.getState();
      expect(state.pinnedIds).not.toContain(102);

      const cand102 = state.candidates.find((c) => c.id === 102);
      expect(cand102?.isPinned).toBe(false);
    });
  });

  describe('Direct Pinning: pinCandidate & unpinCandidate', () => {
    beforeEach(() => {
      useShortlistStore.getState().setShortlist(5, 12, sampleCandidates);
    });

    it('idempotently pins candidate without duplicating IDs', () => {
      useShortlistStore.getState().pinCandidate(103);
      useShortlistStore.getState().pinCandidate(103);

      const state = useShortlistStore.getState();
      expect(state.pinnedIds.filter((id) => id === 103)).toHaveLength(1);

      const cand103 = state.candidates.find((c) => c.id === 103);
      expect(cand103?.isPinned).toBe(true);
    });

    it('unpins candidate and updates both array and candidate object', () => {
      useShortlistStore.getState().unpinCandidate(102);

      const state = useShortlistStore.getState();
      expect(state.pinnedIds).toEqual([]);

      const cand102 = state.candidates.find((c) => c.id === 102);
      expect(cand102?.isPinned).toBe(false);
    });
  });

  describe('Score Delta Updating: updateScoresAfterRefine', () => {
    beforeEach(() => {
      useShortlistStore.getState().setShortlist(5, 12, sampleCandidates);
    });

    it('updates candidate final scores and tracks delta deltas for explainability', () => {
      // Refinement updates: candidate 101 gains boost to 94.0, candidate 103 to 82.5
      const deltas = {
        101: 94.0,
        103: 82.5,
      };

      useShortlistStore.getState().updateScoresAfterRefine(deltas);

      const state = useShortlistStore.getState();
      expect(state.deltaScores[101]).toBe(94.0);
      expect(state.deltaScores[103]).toBe(82.5);

      const cand101 = state.candidates.find((c) => c.id === 101);
      expect(cand101?.finalScore).toBe(94.0);

      const cand103 = state.candidates.find((c) => c.id === 103);
      expect(cand103?.finalScore).toBe(82.5);

      // Candidate 102 score was not in deltas, should remain at 92.5
      const cand102 = state.candidates.find((c) => c.id === 102);
      expect(cand102?.finalScore).toBe(92.5);
    });

    it('preserves pinned status during criteria refinement', () => {
      // Candidate 102 is pinned
      useShortlistStore.getState().updateScoresAfterRefine({ 102: 95.0 });

      const state = useShortlistStore.getState();
      expect(state.pinnedIds).toContain(102);
      expect(state.candidates.find((c) => c.id === 102)?.isPinned).toBe(true);
    });
  });
});
