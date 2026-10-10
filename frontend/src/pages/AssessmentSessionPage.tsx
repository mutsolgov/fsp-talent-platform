import React, { useState, useEffect } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { IsomorphicTaskRunner } from '../components/organisms/IsomorphicTaskRunner';
import { TaskTimer } from '../components/molecules/TaskTimer';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { AssessmentTaskItemResponse } from '../types';
import { ArrowRight, ChevronLeft, ChevronRight, CheckCircle, Code, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const AssessmentSessionPage: React.FC = () => {
  const [sessionId, setSessionId] = useState<number>(1);
  const [currentTaskIndex, setCurrentTaskIndex] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentTask, setCurrentTask] = useState<AssessmentTaskItemResponse | null>(null);
  const [isLoadingTask, setIsLoadingTask] = useState(true);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isExpired, setIsExpired] = useState(false);

  // Extract sessionId from URL if present
  useEffect(() => {
    const parts = window.location.pathname.split('/');
    const idIdx = parts.indexOf('assessment');
    if (idIdx !== -1 && parts[idIdx + 1] && !isNaN(Number(parts[idIdx + 1]))) {
      setSessionId(Number(parts[idIdx + 1]));
    }
  }, []);

  const totalTasks = 12;

  const loadTask = async (sessId: number, taskIdx: number) => {
    setIsLoadingTask(true);
    setTaskError(null);
    setSubmitError(null);
    try {
      const data = await api.get<any>(`/assessment/sessions/${sessId}/tasks/${taskIdx}`);
      const testCase = data.public_tests?.[0];
      setCurrentTask({
        id: `task-${data.task_index ?? taskIdx}`,
        sessionTaskId: data.task_index ?? taskIdx,
        index: data.task_index ?? taskIdx,
        title: data.title || `Изоморфное задание #${taskIdx}: (KITE 3PL)`,
        description: data.description || data.prompt || '',
        difficulty: (taskIdx <= 4 ? 'easy' : taskIdx <= 9 ? 'medium' : 'hard') as 'easy' | 'medium' | 'hard',
        language: 'python',
        starterCode: data.code_template || data.starter_code || '# Введите ваше решение здесь\n',
        sampleInput: testCase ? (typeof testCase.input === 'object' ? JSON.stringify(testCase.input) : String(testCase.input ?? testCase.input_data ?? '')) : '',
        sampleOutput: testCase ? (typeof testCase.expected_output === 'object' ? JSON.stringify(testCase.expected_output) : String(testCase.expected_output ?? '')) : '',
        timeLimitSec: data.time_limit_seconds || 180,
      });
    } catch (err: unknown) {
      setCurrentTask(null);
      setTaskError(
        err instanceof Error
          ? err.message
          : 'Не удалось загрузить задание с сервера. Проверьте соединение.'
      );
    } finally {
      setIsLoadingTask(false);
    }
  };

  useEffect(() => {
    loadTask(sessionId, currentTaskIndex);
  }, [sessionId, currentTaskIndex]);

  const handleSubmitAnswer = async (code: string) => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await api.post(`/assessment/sessions/${sessionId}/answer`, {
        task_index: currentTaskIndex,
        answer_payload: code,
        time_spent_seconds: 45,
      });

      if (currentTaskIndex < totalTasks) {
        setCurrentTaskIndex((prev) => prev + 1);
      } else {
        // Complete session
        await api.post(`/assessment/sessions/${sessionId}/submit`);
        window.location.href = `/candidate/assessment/${sessionId}/results`;
      }
    } catch (err: unknown) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : 'Не удалось отправить решение на сервер. Пожалуйста, повторите попытку.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTimeExpired = async () => {
    setIsExpired(true);
    try {
      await api.post(`/assessment/sessions/${sessionId}/submit`);
    } catch {
      // Best-effort submit
    }
    setTimeout(() => {
      window.location.href = `/candidate/assessment/${sessionId}/results`;
    }, 1800);
  };

  return (
    <CandidateLayout currentTab="onboarding">
      <div className="flex flex-col gap-6 relative">
        {isExpired && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-[#202129] border border-[#00F5D4] rounded-[16px] p-6 max-w-md text-center flex flex-col items-center gap-3 shadow-2xl">
              <CheckCircle size={36} className="text-[#00F5D4]" />
              <h3 className="font-mono text-lg font-bold text-white">Время на выполнение теста истекло</h3>
              <p className="text-xs text-[#9B9C9E]">
                Ваши решения зафиксированы и отправлены на оценку KITE IRT. Перенаправление к результатам...
              </p>
            </div>
          </div>
        )}
        {/* Top Assessment Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-[8px] bg-[#402FFF]/10 border border-[#402FFF]/30 flex items-center justify-center text-[#402FFF]">
              <Code size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-white">
                  Сессия KITE #{sessionId}
                </span>
                <Badge variant="fsp" size="sm">
                  Задание {currentTaskIndex} из {totalTasks}
                </Badge>
              </div>
              <p className="text-[11px] text-[#9B9C9E] mt-0.5">
                Изоморфный рандомизированный вариант (HMAC-SHA256 анти-лик защита)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 self-end sm:self-center">
            <TaskTimer
              totalSeconds={5400}
              onTimeExpired={handleTimeExpired}
            />

            {currentTaskIndex === totalTasks && (
              <Button
                variant="fsp_mint"
                size="sm"
                onClick={() => handleSubmitAnswer('')}
                isLoading={isSubmitting}
              >
                <span>Завершить сессию</span>
                <CheckCircle size={14} />
              </Button>
            )}
          </div>
        </div>

        {/* Task Navigation Matrix */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
          {Array.from({ length: totalTasks }, (_, i) => i + 1).map((idx) => {
            const isActive = idx === currentTaskIndex;
            const isCompleted = idx < currentTaskIndex;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => setCurrentTaskIndex(idx)}
                className={`w-9 h-9 rounded-[8px] font-mono text-xs font-bold flex items-center justify-center transition-all ${
                  isActive
                    ? 'bg-[#402FFF] text-white shadow-[0_0_12px_rgba(64,47,255,0.5)] border border-[#402FFF]'
                    : isCompleted
                    ? 'bg-[#00F5D4]/10 text-[#00F5D4] border border-[#00F5D4]/30'
                    : 'bg-[#202129] text-[#9B9C9E] border border-[#2D2E37] hover:text-white'
                }`}
              >
                {idx}
              </button>
            );
          })}
        </div>

        {submitError && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 text-red-400 rounded-[12px] text-xs font-mono flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="shrink-0" />
              <span>{submitError}</span>
            </div>
            <button
              type="button"
              onClick={() => setSubmitError(null)}
              className="text-red-400 hover:text-white text-xs font-bold px-2 py-1 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Main Task Runner / Error / Loading States */}
        {taskError ? (
          <div className="p-8 bg-[#202129] rounded-[16px] border border-red-500/30 text-center flex flex-col items-center gap-4">
            <AlertCircle size={32} className="text-red-400" />
            <div className="text-white font-mono text-base font-bold">
              Ошибка загрузки задания #{currentTaskIndex}
            </div>
            <div className="text-red-300 font-mono text-xs max-w-md">
              {taskError}
            </div>
            <Button
              variant="fsp_mint"
              size="sm"
              onClick={() => loadTask(sessionId, currentTaskIndex)}
            >
              <span>Повторить загрузку</span>
            </Button>
          </div>
        ) : isLoadingTask || !currentTask ? (
          <div className="p-12 bg-[#202129] rounded-[16px] border border-[#2D2E37] text-center flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-[#00F5D4] border-t-transparent rounded-full animate-spin" />
            <span className="font-mono text-xs text-[#9B9C9E]">
              Загрузка изоморфного задания KITE #{currentTaskIndex}...
            </span>
          </div>
        ) : (
          <IsomorphicTaskRunner
            key={currentTask.id}
            sessionId={sessionId}
            task={currentTask}
            onSubmitAnswer={handleSubmitAnswer}
            isSubmitting={isSubmitting}
          />
        )}

        {/* Bottom Pagination Control */}
        <div className="flex items-center justify-between p-4 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
          <Button
            variant="ghost"
            size="sm"
            disabled={currentTaskIndex === 1}
            onClick={() => setCurrentTaskIndex((prev) => Math.max(1, prev - 1))}
          >
            <ChevronLeft size={16} />
            <span>Предыдущее задание</span>
          </Button>

          <span className="font-mono text-xs text-[#9B9C9E]">
            {Math.round((currentTaskIndex / totalTasks) * 100)}% пройдено
          </span>

          <Button
            variant="secondary"
            size="sm"
            disabled={currentTaskIndex === totalTasks}
            onClick={() => setCurrentTaskIndex((prev) => Math.min(totalTasks, prev + 1))}
          >
            <span>Следующее задание</span>
            <ChevronRight size={16} />
          </Button>
        </div>
      </div>
    </CandidateLayout>
  );
};
export default AssessmentSessionPage;
