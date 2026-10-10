import React from 'react';
import { CandidateAnonymizedSummary } from '../../types';
import { Avatar } from '../atoms/Avatar';
import { Badge } from '../atoms/Badge';
import { FspRankBadge } from '../molecules/FspRankBadge';
import { ScoreBreakdownBar } from '../molecules/ScoreBreakdownBar';
import { DiffDeltaIndicator } from '../molecules/DiffDeltaIndicator';
import { Pin, ArrowRight } from '../icons';

export interface CandidateCardProps {
  candidate: CandidateAnonymizedSummary;
  isPinned: boolean;
  onPinToggle: () => void;
  onExplainClick: () => void;
  onInviteClick: () => void;
  className?: string;
}

export const CandidateCard: React.FC<CandidateCardProps> = ({
  candidate,
  isPinned,
  onPinToggle,
  onExplainClick,
  onInviteClick,
  className = '',
}) => {
  return (
    <article
      className={`relative p-5 rounded-[12px] bg-[#202129] border transition-all flex flex-col justify-between gap-4 shadow-[0_4px_20px_rgba(0,0,0,0.5)] ${
        isPinned
          ? 'border-[#402FFF] bg-[#202129]/95 shadow-[0_0_20px_rgba(64,47,255,0.2)]'
          : 'border-[#3D3E42] hover:border-[#402FFF]/60'
      } ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <Avatar isMasked size="md" />
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-white tracking-wide">
                {candidate.maskedCode}
              </span>
              {candidate.deltaScore !== undefined && (
                <DiffDeltaIndicator deltaS={candidate.deltaScore} />
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="default" size="sm">
                {candidate.specialization.toUpperCase()}
              </Badge>
              <Badge variant="fsp" size="sm">
                {candidate.verifiedGrade.toUpperCase()}
              </Badge>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onPinToggle}
          aria-label={isPinned ? 'Открепить кандидата' : 'Закрепить кандидата в шортлисте'}
          className={`p-2 rounded-[6px] border transition-all cursor-pointer ${
            isPinned
              ? 'bg-[#402FFF] text-white border-[#402FFF] shadow-[0_0_12px_rgba(64,47,255,0.4)]'
              : 'bg-[#1E1F26] text-[#9B9C9E] border-[#3D3E42] hover:text-white hover:border-[#5F5F66]'
          }`}
        >
          <Pin size={16} />
        </button>
      </div>

      {/* FSP Rank Badge */}
      <div>
        <FspRankBadge
          rank={candidate.sportRank}
          isFspVerified={candidate.isFspVerified}
          contestCount={candidate.fspAchievements?.length}
        />
      </div>

      {/* Skills list */}
      <div className="flex flex-wrap gap-1.5">
        {candidate.skills.slice(0, 6).map((skill) => (
          <span
            key={skill}
            className="px-2 py-0.5 rounded-[4px] bg-[#1E1F26] border border-[#2D2E37] text-[11px] font-mono text-[#C8C9CA]"
          >
            {skill}
          </span>
        ))}
      </div>

      {/* Score breakdown bar */}
      <ScoreBreakdownBar
        totalScore={candidate.finalScore}
        breakdown={{
          test: candidate.factors?.testScore || candidate.theta * 0.35,
          stack: candidate.factors?.stackMatchPct || 25,
          fsp: candidate.factors?.fspScore || (candidate.isFspVerified ? 18 : 0),
          freshness: candidate.factors?.freshnessScore || candidate.freshnessScore * 0.15,
        }}
        isFsp={candidate.isFspVerified}
      />

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-2 border-t border-[#2D2E37]">
        <button
          type="button"
          onClick={onExplainClick}
          className="flex-1 py-2 px-3 rounded-[6px] bg-[#1E1F26] hover:bg-[#2D2E37] text-[#C8C9CA] hover:text-white border border-[#3D3E42] text-xs font-mono font-medium transition-colors cursor-pointer text-center"
        >
          Обоснование скоринга
        </button>

        <button
          type="button"
          onClick={onInviteClick}
          className="flex-1 py-2 px-3 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white text-xs font-mono font-semibold transition-colors cursor-pointer flex items-center justify-center gap-1.5 shadow-[0_0_12px_rgba(64,47,255,0.3)]"
        >
          <span>Пригласить</span>
          <ArrowRight size={14} />
        </button>
      </div>
    </article>
  );
};
