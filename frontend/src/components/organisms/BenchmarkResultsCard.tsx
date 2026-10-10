import React from 'react';
import { BenchmarkReportResponse } from '../../types';
import { BenchmarkMetricTile } from '../molecules/BenchmarkMetricTile';
import { Button } from '../atoms/Button';
import { ProgressBar } from '../atoms/ProgressBar';
import { Play, ShieldCheck } from '../icons';

export interface BenchmarkResultsCardProps {
  report: BenchmarkReportResponse | null;
  isRunning: boolean;
  onRunBenchmark: () => void;
  className?: string;
}

export const BenchmarkResultsCard: React.FC<BenchmarkResultsCardProps> = ({
  report,
  isRunning,
  onRunBenchmark,
  className = '',
}) => {
  const metrics = report
    ? [
        {
          label: 'NDCG@5',
          value: report.ndcgAt5 ?? (report as any).mean_ndcg_5 ?? 0.0,
          threshold: 0.85,
          desc: 'Качество топ-5 рекомендаций ранжирования',
        },
        {
          label: 'NDCG@10',
          value: report.ndcgAt10 ?? (report as any).mean_ndcg_10 ?? 0.0,
          threshold: 0.88,
          desc: 'Ранжирование первой страницы выдачи',
        },
        {
          label: 'Precision@5',
          value: report.precisionAt5 ?? (report as any).mean_p_5 ?? 0.0,
          threshold: 0.80,
          desc: 'Точность попадания релевантных талантов в топ-5',
        },
        {
          label: 'Pearson r_xx',
          value: report.pearsonR ?? (report as any).test_retest_r ?? 0.0,
          threshold: 0.85,
          desc: 'Надежность психометрического теста KITE IRT',
        },
        {
          label: 'Дискриминативность D',
          value: report.itemDiscriminationD ?? (report as any).kelley_d ?? 0.0,
          threshold: 0.35,
          desc: 'Индекс различения уровней способностей',
        },
        {
          label: 'Стойкость к сливу',
          value: report.leakResistance ?? (report as any).leak_index ?? 0.0,
          threshold: 0.85,
          desc: 'Антислив изоморфных сессий HMAC-SHA256',
        },
      ]
    : [];

  return (
    <div
      className={`p-6 rounded-[14px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_24px_rgba(0,0,0,0.5)] flex flex-col gap-5 ${className}`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#2D2E37] pb-4">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <ShieldCheck size={20} className="text-[#00F5D4]" />
            <h2 className="font-mono text-lg font-bold text-white">
              Валидационный бенчмарк (Golden Dataset 60×15 = 900 пар)
            </h2>
          </div>
          <span className="text-xs font-sans text-[#9B9C9E] mt-0.5">
            Строгая математическая верификация критериев хакатона ЛЦТ 2026 без искусственных заглушек
          </span>
        </div>

        <Button
          variant="fsp_mint"
          size="md"
          isLoading={isRunning}
          onClick={onRunBenchmark}
          className="shrink-0"
        >
          <Play size={16} />
          <span>{isRunning ? 'Расчет бенчмарка...' : 'Запустить бенчмарк'}</span>
        </Button>
      </div>

      {isRunning && (
        <div className="flex flex-col gap-2 p-4 rounded-[8px] bg-[#1E1F26] border border-[#402FFF]/30">
          <div className="flex justify-between text-xs font-mono text-[#00F5D4]">
            <span>Вычисление 900 матричных пар relevance y ∈ {'{0,1,2,3}'}...</span>
            <span>Расчет...</span>
          </div>
          <ProgressBar value={78} color="gradient" />
        </div>
      )}

      {/* Empty State when report is not yet run */}
      {!report && !isRunning && (
        <div className="p-8 text-center bg-[#1B1C21] rounded-[10px] border border-dashed border-[#3D3E42] flex flex-col items-center gap-3">
          <ShieldCheck size={36} className="text-[#00F5D4]/70" />
          <div className="font-mono text-sm text-white font-medium">
            Бенчмарк готов к расчету
          </div>
          <p className="text-xs text-[#9B9C9E] max-w-md">
            Нажмите кнопку «Запустить бенчмарк» для выполнения полного прогона 900 пар и получения актуальных психометрических и ранжирующих метрик.
          </p>
        </div>
      )}

      {/* 6 Metric Tiles when report is available */}
      {report && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {metrics.map((m) => (
            <BenchmarkMetricTile
              key={m.label}
              label={m.label}
              value={m.value}
              threshold={m.threshold}
            />
          ))}
        </div>
      )}
    </div>
  );
};
