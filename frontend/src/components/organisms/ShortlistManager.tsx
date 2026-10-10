import React, { useState } from 'react';
import { SavedShortlistDetailResponse } from '../../types';
import { CandidateCard } from './CandidateCard';
import { Pin, Filter, RefreshCw, X } from '../icons';

export interface ShortlistManagerProps {
  shortlist: SavedShortlistDetailResponse;
  onRefine: (criteria: Record<string, unknown>) => void;
  onDelete: () => void;
  className?: string;
}

export const ShortlistManager: React.FC<ShortlistManagerProps> = ({
  shortlist,
  onRefine,
  onDelete,
  className = '',
}) => {
  const [pinnedCandidateIds, setPinnedCandidateIds] = useState<number[]>(shortlist.pinnedIds || []);
  const [refineQuery, setRefineQuery] = useState('');

  const togglePin = (id: number) => {
    setPinnedCandidateIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleRefineSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onRefine({ query: refineQuery });
  };

  // Sort: pinned first, then by finalScore descending
  const sortedCandidates = [...shortlist.candidates].sort((a, b) => {
    const aPinned = pinnedCandidateIds.includes(a.id);
    const bPinned = pinnedCandidateIds.includes(b.id);
    if (aPinned && !bPinned) return -1;
    if (!aPinned && bPinned) return 1;
    return b.finalScore - a.finalScore;
  });

  return (
    <div className={`flex flex-col gap-5 ${className}`}>
      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-[12px] bg-[#202129] border border-[#3D3E42]">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <h2 className="font-mono text-base font-bold text-white">{shortlist.title}</h2>
            <span className="text-xs font-mono text-[#00F5D4]">({sortedCandidates.length} кандидатов)</span>
          </div>
          <span className="text-xs font-sans text-[#9B9C9E]">
            {pinnedCandidateIds.length} закреплено в топе выдачи
          </span>
        </div>

        <form onSubmit={handleRefineSubmit} className="flex items-center gap-2 w-full sm:w-auto">
          <input
            type="text"
            value={refineQuery}
            onChange={(e) => setRefineQuery(e.target.value)}
            placeholder="Уточнить фильтры (навык, опыт)..."
            className="px-3 py-1.5 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-xs border border-[#3D3E42] focus:border-[#402FFF] outline-none"
          />
          <button
            type="submit"
            className="px-3 py-1.5 rounded-[6px] bg-[#402FFF] text-white font-mono text-xs font-medium cursor-pointer"
          >
            Уточнить
          </button>
          <button
            type="button"
            onClick={onDelete}
            title="Удалить шортлист"
            className="p-1.5 rounded-[6px] text-[#FB7185] hover:bg-rose-950/40 border border-transparent"
          >
            <X size={16} />
          </button>
        </form>
      </div>

      {/* Grid of candidates */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedCandidates.map((candidate) => {
          const isPinned = pinnedCandidateIds.includes(candidate.id);
          return (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              isPinned={isPinned}
              onPinToggle={() => togglePin(candidate.id)}
              onExplainClick={() => {}}
              onInviteClick={() => {}}
            />
          );
        })}
      </div>
    </div>
  );
};
