import React, { useState, useEffect } from 'react';
import { CandidateAnonymizedSummary } from '../../types';
import { RadarMatchChart } from '../molecules/RadarMatchChart';
import { Badge } from '../atoms/Badge';
import { X, CheckCircle, ShieldCheck } from '../icons';

export interface ExplainabilityModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: CandidateAnonymizedSummary;
  needTitle?: string;
  className?: string;
}

export const ExplainabilityModal: React.FC<ExplainabilityModalProps> = ({
  isOpen,
  onClose,
  candidate,
  needTitle,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'radar' | 'factors' | 'fsp'>('radar');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const isFsp = candidate.isFspVerified;
  const weights = candidate.weights || (isFsp
    ? { isFspProfile: true, wTest: 0.35, wStack: 0.25, wFsp: 0.25, wFreshness: 0.15 }
    : { isFspProfile: false, wTest: 0.52, wStack: 0.30, wFsp: 0.00, wFreshness: 0.18 });

  const factors = candidate.factors || {
    testScore: candidate.theta,
    stackMatchPct: 88,
    fspScore: isFsp ? 85 : 0,
    freshnessScore: candidate.freshnessScore || 90,
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="explainability-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in"
    >
      <div
        className={`relative w-full max-w-2xl rounded-[16px] bg-[#1B1C21] border border-[#3D3E42] shadow-[0_20px_60px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[90vh] ${className}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#2D2E37] bg-[#202129]">
          <div className="flex flex-col">
            <h2 id="explainability-title" className="font-mono text-lg font-bold text-white flex items-center gap-2">
              <span>Обоснование скоринга S = {candidate.finalScore.toFixed(1)}</span>
              <Badge variant={isFsp ? 'fsp' : 'non_fsp'} size="sm">
                {candidate.maskedCode}
              </Badge>
            </h2>
            {needTitle && (
              <span className="text-xs font-sans text-[#9B9C9E] mt-0.5">
                Позиция: {needTitle}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть модальное окно"
            className="p-1.5 rounded-[6px] text-[#9B9C9E] hover:text-white hover:bg-[#2D2E37] transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Dynamic Weights Banner */}
        <div className={`p-3.5 border-b text-xs font-mono flex items-center justify-between ${
          isFsp
            ? 'bg-[#402FFF]/10 border-[#402FFF]/30 text-[#EDEDED]'
            : 'bg-[#00F5D4]/10 border-[#00F5D4]/30 text-[#00F5D4]'
        }`}>
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} />
            <span>
              {isFsp
                ? 'Формула ФСП: S = 0.35·S_test + 0.25·S_stack + 0.25·S_fsp + 0.15·S_freshness'
                : 'Динамическое перераспределение (Общий трек): S = 0.52·S_test + 0.30·S_stack + 0.18·S_freshness'}
            </span>
          </div>
          <span className="font-bold underline text-white">∑w = 1.00</span>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#2D2E37] bg-[#1E1F26] px-5 text-xs font-mono">
          <button
            type="button"
            onClick={() => setActiveTab('radar')}
            className={`py-3 px-4 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === 'radar'
                ? 'border-[#402FFF] text-white font-bold'
                : 'border-transparent text-[#9B9C9E] hover:text-[#EDEDED]'
            }`}
          >
            Радар факторов
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('factors')}
            className={`py-3 px-4 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === 'factors'
                ? 'border-[#402FFF] text-white font-bold'
                : 'border-transparent text-[#9B9C9E] hover:text-[#EDEDED]'
            }`}
          >
            Детализация слагаемых
          </button>
          {isFsp && (
            <button
              type="button"
              onClick={() => setActiveTab('fsp')}
              className={`py-3 px-4 border-b-2 font-medium transition-colors cursor-pointer ${
                activeTab === 'fsp'
                  ? 'border-[#402FFF] text-white font-bold'
                  : 'border-transparent text-[#9B9C9E] hover:text-[#EDEDED]'
              }`}
            >
              Достижения ФСП
            </button>
          )}
        </div>

        {/* Tab Content */}
        <div className="p-5 overflow-y-auto flex-1">
          {activeTab === 'radar' && (
            <div className="flex flex-col items-center justify-center gap-4">
              <RadarMatchChart
                testMatch={factors.testScore}
                stackMatch={factors.stackMatchPct}
                fspMatch={factors.fspScore}
                freshnessMatch={factors.freshnessScore}
                isFspProfile={isFsp}
                size={240}
              />
              <p className="text-xs font-sans text-[#9B9C9E] text-center max-w-md">
                Радарная диаграмма отражает относительную силу каждого из 4 независимых измерений. Для кандидатов без реестра ФСП вес автоматически перенесен на объективный тест KITE IRT (0.52) и актуальность стека (0.18).
              </p>
            </div>
          )}

          {activeTab === 'factors' && (
            <div className="flex flex-col gap-3 font-mono text-xs">
              <div className="p-3 rounded-[8px] bg-[#202129] border border-[#2D2E37] flex justify-between items-center">
                <div className="flex flex-col">
                  <span className="font-bold text-white">Психометрический тест KITE IRT (S_test)</span>
                  <span className="text-[11px] text-[#9B9C9E]">Вес w_test = {weights.wTest.toFixed(2)} • Оценка θ = {factors.testScore.toFixed(1)}/100</span>
                </div>
                <span className="text-sm font-bold text-[#402FFF]">{(factors.testScore * weights.wTest).toFixed(2)}</span>
              </div>

              <div className="p-3 rounded-[8px] bg-[#202129] border border-[#2D2E37] flex justify-between items-center">
                <div className="flex flex-col">
                  <span className="font-bold text-white">Соответствие стеку вакансии (S_stack)</span>
                  <span className="text-[11px] text-[#9B9C9E]">Вес w_stack = {weights.wStack.toFixed(2)} • Совпадение = {factors.stackMatchPct.toFixed(1)}%</span>
                </div>
                <span className="text-sm font-bold text-[#00F5D4]">{(factors.stackMatchPct * weights.wStack).toFixed(2)}</span>
              </div>

              {isFsp && (
                <div className="p-3 rounded-[8px] bg-[#202129] border border-[#2D2E37] flex justify-between items-center">
                  <div className="flex flex-col">
                    <span className="font-bold text-white">Спортивный разряд ФСП (S_fsp)</span>
                    <span className="text-[11px] text-[#9B9C9E]">Вес w_fsp = {weights.wFsp.toFixed(2)} • ЕВСК = {factors.fspScore.toFixed(1)}</span>
                  </div>
                  <span className="text-sm font-bold text-[#EC1D35]">{(factors.fspScore * weights.wFsp).toFixed(2)}</span>
                </div>
              )}

              <div className="p-3 rounded-[8px] bg-[#202129] border border-[#2D2E37] flex justify-between items-center">
                <div className="flex flex-col">
                  <span className="font-bold text-white">Свежесть активности (S_freshness)</span>
                  <span className="text-[11px] text-[#9B9C9E]">Вес w_freshness = {weights.wFreshness.toFixed(2)} • Микро-челленджи = {factors.freshnessScore.toFixed(1)}%</span>
                </div>
                <span className="text-sm font-bold text-[#7B2CBF]">{(factors.freshnessScore * weights.wFreshness).toFixed(2)}</span>
              </div>
            </div>
          )}

          {activeTab === 'fsp' && isFsp && (
            <div className="flex flex-col gap-2.5">
              {candidate.fspAchievements && candidate.fspAchievements.length > 0 ? (
                candidate.fspAchievements.map((ach, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-[8px] bg-[#202129] border border-[#2D2E37] flex items-center justify-between"
                  >
                    <div className="flex flex-col">
                      <span className="text-xs font-mono font-bold text-white">{ach.title}</span>
                      <span className="text-[11px] font-sans text-[#9B9C9E]">{ach.stage || 'Всероссийский турнир'} ({ach.year})</span>
                    </div>
                    <Badge variant="fsp" size="sm">{ach.rank}</Badge>
                  </div>
                ))
              ) : (
                <p className="text-xs font-sans text-[#9B9C9E]">Официальные протоколы синхронизированы из реестра ФСП России.</p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#2D2E37] bg-[#202129] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-white text-xs font-mono font-medium transition-colors cursor-pointer"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};
