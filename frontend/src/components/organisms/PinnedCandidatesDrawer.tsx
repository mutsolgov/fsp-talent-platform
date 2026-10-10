import React from 'react';
import { CandidateAnonymizedSummary } from '../../types';
import { Avatar } from '../atoms/Avatar';
import { Badge } from '../atoms/Badge';
import { X, Pin, ArrowRight } from '../icons';

export interface PinnedCandidatesDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  pinnedCandidates: CandidateAnonymizedSummary[];
  onUnpin: (id: number) => void;
  onBatchInvite: () => void;
  className?: string;
}

export const PinnedCandidatesDrawer: React.FC<PinnedCandidatesDrawerProps> = ({
  isOpen,
  onClose,
  pinnedCandidates,
  onUnpin,
  onBatchInvite,
  className = '',
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <aside
        aria-label="Закрепленные кандидаты шортлиста"
        className={`absolute inset-y-0 right-0 max-w-full flex pl-10 ${className}`}
      >
        <div className="w-screen max-w-md bg-[#1B1C21] border-l border-[#3D3E42] shadow-2xl flex flex-col justify-between">
          {/* Header */}
          <div className="p-5 border-b border-[#2D2E37] bg-[#202129] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Pin size={18} className="text-[#402FFF]" />
              <h2 className="font-mono text-base font-bold text-white">
                Закрепленные ({pinnedCandidates.length})
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-[6px] text-[#9B9C9E] hover:text-white hover:bg-[#2D2E37]"
            >
              <X size={20} />
            </button>
          </div>

          {/* Candidate list */}
          <div className="p-5 overflow-y-auto flex-1 flex flex-col gap-3">
            {pinnedCandidates.length === 0 ? (
              <div className="text-center py-12 text-xs font-mono text-[#9B9C9E]">
                Нет закрепленных кандидатов. Нажмите на иконку булавки на карточке кандидата для добавления в шортлист.
              </div>
            ) : (
              pinnedCandidates.map((c) => (
                <div
                  key={c.id}
                  className="p-3.5 rounded-[8px] bg-[#202129] border border-[#2D2E37] flex items-center justify-between gap-3 hover:border-[#402FFF]/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Avatar isMasked size="sm" />
                    <div className="flex flex-col">
                      <span className="font-mono text-xs font-bold text-white">{c.maskedCode}</span>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Badge variant="default" size="sm">
                          {c.specialization.toUpperCase()}
                        </Badge>
                        <Badge variant="fsp" size="sm">
                          {c.verifiedGrade.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-[#00F5D4]">
                      {c.finalScore.toFixed(0)} б.
                    </span>
                    <button
                      type="button"
                      onClick={() => onUnpin(c.id)}
                      title="Открепить"
                      className="p-1.5 rounded-[4px] text-[#FB7185] hover:bg-rose-950/40"
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer Batch Actions */}
          <div className="p-4 border-t border-[#2D2E37] bg-[#202129] flex flex-col gap-2">
            <button
              type="button"
              onClick={onBatchInvite}
              disabled={pinnedCandidates.length === 0}
              className="w-full py-2.5 px-4 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white font-mono text-xs font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-[0_0_16px_rgba(64,47,255,0.4)]"
            >
              <span>Массовое приглашение ({pinnedCandidates.length})</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
};
