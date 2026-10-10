import React from 'react';
import { CandidateFullProfileResponse } from '../../types';
import { Avatar } from '../atoms/Avatar';
import { Badge } from '../atoms/Badge';
import { FspRankBadge } from '../molecules/FspRankBadge';
import { UnmaskedContactCard } from '../molecules/UnmaskedContactCard';
import { Download, FileText } from '../icons';

export interface CandidateCardUnmaskedProps {
  candidate: CandidateFullProfileResponse;
  onPdfDownload: () => void;
  className?: string;
}

export const CandidateCardUnmasked: React.FC<CandidateCardUnmaskedProps> = ({
  candidate,
  onPdfDownload,
  className = '',
}) => {
  return (
    <article
      className={`p-6 rounded-[12px] bg-[#202129] border border-[#00F5D4]/40 shadow-[0_0_24px_rgba(0,245,212,0.15)] flex flex-col gap-5 ${className}`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <Avatar initials={candidate.fullName.slice(0, 2).toUpperCase()} size="lg" />
          <div className="flex flex-col">
            <h3 className="font-mono text-lg font-bold text-white">{candidate.fullName}</h3>
            <span className="text-xs font-mono text-[#00F5D4]">{candidate.maskedCode}</span>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="default" size="sm">
                {candidate.specialization.toUpperCase()}
              </Badge>
              <Badge variant="fsp" size="sm">
                {candidate.verifiedGrade.toUpperCase()}
              </Badge>
              {candidate.experienceYears && (
                <span className="text-xs font-mono text-[#9B9C9E]">
                  Опыт: {candidate.experienceYears} лет
                </span>
              )}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onPdfDownload}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white text-xs font-mono font-semibold transition-colors cursor-pointer shrink-0"
        >
          <Download size={14} />
          Экспорт PDF ФСП
        </button>
      </div>

      <div>
        <FspRankBadge
          rank={candidate.sportRank}
          isFspVerified={candidate.isFspVerified}
          contestCount={candidate.fspAchievements?.length}
        />
      </div>

      {candidate.summaryBio && (
        <p className="text-sm font-sans text-[#EDEDED] leading-relaxed bg-[#1E1F26] p-3 rounded-[6px] border border-[#2D2E37]">
          {candidate.summaryBio}
        </p>
      )}

      {/* Unmasked contacts */}
      <UnmaskedContactCard
        email={candidate.email}
        phone={candidate.phone}
        telegram={candidate.telegram}
        githubUrl={candidate.githubUrl}
        pdfUrl={candidate.pdfResumeUrl}
      />
    </article>
  );
};
