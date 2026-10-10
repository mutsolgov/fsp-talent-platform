import React, { useState } from 'react';
import { MicroChallengeDetailResponse } from '../../types';
import { CodeEditorMini } from '../molecules/CodeEditorMini';
import { TestResultBadge } from '../molecules/TestResultBadge';
import { Button } from '../atoms/Button';
import { Badge } from '../atoms/Badge';
import { Play, Check, AlertCircle } from '../icons';
import { api } from '../../api/client';

export interface MicroChallengeSolverProps {
  challenge: MicroChallengeDetailResponse;
  onSubmitted: () => void;
  className?: string;
}

export interface ChallengeDryRunResponse {
  all_passed: boolean;
  passed_count: number;
  total_count: number;
  logs: string;
  execution_time_ms: number;
  memory_used_mb: number;
  public_results?: Array<{ test_index: number; passed: boolean; status?: string }>;
}

export const MicroChallengeSolver: React.FC<MicroChallengeSolverProps> = ({
  challenge,
  onSubmitted,
  className = '',
}) => {
  const [code, setCode] = useState(challenge.starterCode || '');
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    status: 'passed' | 'failed' | 'tle' | 'ce';
    timeMs: number;
    memoryKb: number;
    logs?: string;
  } | null>(null);

  const handleRunTests = async () => {
    setIsRunning(true);
    setRunError(null);
    try {
      const res = await api.post<ChallengeDryRunResponse>(
        `/micro-challenges/${challenge.id}/run-tests`,
        { code, solution_code: code }
      );
      const isPassed = Boolean(res.all_passed);
      setTestResult({
        status: isPassed ? 'passed' : 'failed',
        timeMs: Math.round(res.execution_time_ms || 0),
        memoryKb: Math.round((res.memory_used_mb || 0) * 1024),
        logs: res.logs,
      });
    } catch (err: unknown) {
      setTestResult(null);
      setRunError(
        err instanceof Error ? err.message : 'Ошибка при выполнении тестов в песочнице'
      );
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await api.post(`/micro-challenges/${challenge.id}/submit`, {
        code,
        solution_code: code,
      });
      onSubmitted();
    } catch (err: unknown) {
      setSubmitError(
        err instanceof Error ? err.message : 'Не удалось отправить решение на сервер'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className={`grid grid-cols-1 lg:grid-cols-2 gap-5 p-5 rounded-[12px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_24px_rgba(0,0,0,0.5)] ${className}`}
    >
      <div className="flex flex-col gap-4 overflow-y-auto max-h-[600px] pr-2">
        <div className="flex items-center justify-between border-b border-[#2D2E37] pb-3">
          <h2 className="font-mono text-base font-bold text-white">{challenge.title}</h2>
          <Badge variant="fsp" size="sm">
            +{challenge.points} очков
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="default" size="sm">
            {challenge.specialization.toUpperCase()}
          </Badge>
          <Badge variant="warning" size="sm">
            {challenge.difficulty.toUpperCase()}
          </Badge>
        </div>

        <p className="text-xs font-sans text-[#EDEDED] leading-relaxed bg-[#1E1F26] p-4 rounded-[8px] border border-[#2D2E37] whitespace-pre-line">
          {challenge.description}
        </p>

        {runError && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-[8px] text-xs font-mono flex items-center justify-between gap-2 mt-2">
            <div className="flex items-center gap-1.5">
              <AlertCircle size={14} className="shrink-0" />
              <span>{runError}</span>
            </div>
            <button type="button" onClick={() => setRunError(null)} className="cursor-pointer">✕</button>
          </div>
        )}

        {testResult && (
          <div className="flex flex-col gap-2 mt-2">
            <span className="text-xs font-mono text-[#C8C9CA]">Вердикт тестов песочницы:</span>
            <TestResultBadge
              status={testResult.status}
              executionTimeMs={testResult.timeMs}
              memoryKb={testResult.memoryKb}
            />
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <CodeEditorMini
          code={code}
          language="python"
          onChange={setCode}
        />

        {submitError && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-[8px] text-xs font-mono flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <AlertCircle size={14} className="shrink-0" />
              <span>{submitError}</span>
            </div>
            <button type="button" onClick={() => setSubmitError(null)} className="cursor-pointer">✕</button>
          </div>
        )}

        <div className="flex items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={handleRunTests}
            disabled={isRunning}
            className="px-3.5 py-2 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED] text-xs font-mono font-medium flex items-center gap-1.5 transition-colors cursor-pointer border border-[#3D3E42]"
          >
            <Play size={14} className="text-[#00F5D4]" />
            <span>{isRunning ? 'Тестирование...' : 'Запустить тесты'}</span>
          </button>

          <Button
            variant="fsp_mint"
            size="md"
            isLoading={isSubmitting}
            onClick={handleSubmit}
            className="flex-1"
          >
            <Check size={16} />
            <span>Сдать решение (+{challenge.points} б.)</span>
          </Button>
        </div>
      </div>
    </div>
  );
};
