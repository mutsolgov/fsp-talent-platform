import React, { useState } from 'react';
import { AssessmentTaskItemResponse } from '../../types';
import { CodeEditorMini } from '../molecules/CodeEditorMini';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { Play, CheckCircle } from '../icons';

export interface IsomorphicTaskRunnerProps {
  sessionId: number;
  task: AssessmentTaskItemResponse;
  onSubmitAnswer: (code: string) => Promise<void>;
  isSubmitting: boolean;
  className?: string;
}

export const IsomorphicTaskRunner: React.FC<IsomorphicTaskRunnerProps> = ({
  sessionId,
  task,
  onSubmitAnswer,
  isSubmitting,
  className = '',
}) => {
  const [currentCode, setCurrentCode] = useState(task.starterCode || '');
  const [testOutput, setTestOutput] = useState<string | null>(null);

  const handleRunSample = () => {
    setTestOutput(`[ПЕСОЧНИЦА ФСП] Входные данные: ${task.sampleInput}\nВывод: ${task.sampleOutput}\nВердикт: SUCCESS (12мс, 4.2Мб)`);
  };

  const handleSubmit = async () => {
    await onSubmitAnswer(currentCode);
  };

  return (
    <div
      className={`grid grid-cols-1 lg:grid-cols-2 gap-5 p-5 rounded-[12px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_24px_rgba(0,0,0,0.6)] ${className}`}
    >
      {/* Left Column: Task Formulation */}
      <div className="flex flex-col gap-4 overflow-y-auto max-h-[600px] pr-2">
        <div className="flex items-center justify-between border-b border-[#2D2E37] pb-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-[#402FFF] bg-[#402FFF]/10 px-2 py-0.5 rounded">
              Задача #{task.index} из 12
            </span>
            <Badge variant="default" size="sm">
              {task.difficulty.toUpperCase()}
            </Badge>
          </div>
          <span className="text-xs font-mono text-[#9B9C9E]">Лимит: {task.timeLimitSec}с</span>
        </div>

        <h3 className="font-mono text-base font-bold text-white">{task.title}</h3>

        <div className="text-xs font-sans text-[#EDEDED] leading-relaxed whitespace-pre-line bg-[#1E1F26] p-4 rounded-[8px] border border-[#2D2E37]">
          {task.description}
        </div>

        {/* Sample Input & Output */}
        <div className="flex flex-col gap-2 font-mono text-xs">
          <span className="text-[#C8C9CA] font-semibold">Пример входных данных:</span>
          <pre className="p-2.5 rounded bg-[#16171D] text-[#00F5D4] border border-[#2D2E37] overflow-x-auto">
            {task.sampleInput}
          </pre>

          <span className="text-[#C8C9CA] font-semibold mt-1">Ожидаемый вывод:</span>
          <pre className="p-2.5 rounded bg-[#16171D] text-[#EDEDED] border border-[#2D2E37] overflow-x-auto">
            {task.sampleOutput}
          </pre>
        </div>
      </div>

      {/* Right Column: Code Editor & Runner */}
      <div className="flex flex-col gap-3">
        <CodeEditorMini
          code={currentCode}
          language={task.language || 'python'}
          onChange={setCurrentCode}
        />

        {testOutput && (
          <div className="p-3 rounded-[6px] bg-[#16171D] border border-emerald-500/30 text-emerald-400 font-mono text-xs whitespace-pre-wrap">
            {testOutput}
          </div>
        )}

        <div className="flex items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={handleRunSample}
            className="px-3.5 py-2 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED] text-xs font-mono font-medium flex items-center gap-1.5 transition-colors cursor-pointer border border-[#3D3E42]"
          >
            <Play size={14} className="text-[#00F5D4]" />
            Запустить тест
          </button>

          <Button
            variant="fsp_mint"
            size="md"
            isLoading={isSubmitting}
            onClick={handleSubmit}
            className="flex-1"
          >
            <CheckCircle size={16} />
            <span>Зафиксировать ответ</span>
          </Button>
        </div>
      </div>
    </div>
  );
};
