import React, { useState } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { ResumeUploader, ResumeParsedResponse } from '../components/organisms/ResumeUploader';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Select } from '../components/atoms/Select';
import { SalaryRangeInput } from '../components/molecules/SalaryRangeInput';
import { FspCircuitConnector } from '../components/atoms/FspCircuitConnector';
import { ArrowRight, CheckCircle, ShieldCheck, Trophy, Sparkles, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const CandidateOnboardingPage: React.FC = () => {
  const [step, setStep] = useState<number>(1);
  const [parsedData, setParsedData] = useState<ResumeParsedResponse | null>(null);
  const [specialization, setSpecialization] = useState('backend');
  const [claimedGrade, setClaimedGrade] = useState('middle');
  const [city, setCity] = useState<string>('');
  const [fspId, setFspId] = useState('');
  const [hasFsp, setHasFsp] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [salaryMin, setSalaryMin] = useState<number>(150000);
  const [salaryMax, setSalaryMax] = useState<number>(250000);
  const [isSalaryValid, setIsSalaryValid] = useState<boolean>(true);
  const [consentPdn, setConsentPdn] = useState<boolean>(true);
  const [consentPublish, setConsentPublish] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const specializations = [
    { value: 'backend', label: 'Backend разработка (Python, Go, Java, C++)' },
    { value: 'frontend', label: 'Frontend разработка (React, TypeScript, Vue)' },
    { value: 'ml_data', label: 'Machine Learning & Data Science (PyTorch, Pandas)' },
    { value: 'devops', label: 'DevOps & SRE (Kubernetes, Terraform, CI/CD)' },
    { value: 'qa', label: 'Quality Assurance & Test Automation (Python, Pytest)' },
    { value: 'infosec', label: 'Информационная безопасность (AppSec, DevSecOps)' },
  ];

  const grades = [
    { value: 'junior', label: 'Junior (Базовые алгоритмы, структуры данных, чистый код)' },
    { value: 'middle', label: 'Middle (Сложные алгоритмы, оптимизация, изоморфные тесты)' },
    { value: 'senior', label: 'Senior (HighLoad, паттерны, распределенные системы)' },
    { value: 'lead', label: 'Lead (Архитектура, системный дизайн, техническое лидерство)' },
  ];

  const specIdMap: Record<string, number> = {
    backend: 1,
    frontend: 2,
    ml_data: 3,
    devops: 4,
    qa: 5,
    infosec: 6,
  };

  const gradeIdMap: Record<string, number> = {
    junior: 1,
    middle: 2,
    senior: 3,
    lead: 4,
  };

  const handleResumeParsed = (data: ResumeParsedResponse) => {
    setParsedData(data);
    if (data.specialization && specIdMap[data.specialization]) {
      setSpecialization(data.specialization);
    }
    if (data.grade && gradeIdMap[data.grade]) {
      setClaimedGrade(data.grade);
    }
    if (data.salaryMin) {
      setSalaryMin(data.salaryMin);
    }
    if (data.salaryMax) {
      setSalaryMax(data.salaryMax);
    }
    if (data.city) {
      setCity(data.city);
    }
    setStep(2);
  };

  const handleStartAssessment = async () => {
    setIsStarting(true);
    setErrorMessage(null);
    try {
      const specId = specIdMap[specialization] || 1;
      const gradeId = gradeIdMap[claimedGrade] || 2;
      const skillsToSubmit =
        parsedData?.skills && parsedData.skills.length > 0
          ? parsedData.skills
          : [specialization === 'frontend' ? 'TypeScript' : 'Python', 'Algorithms'];

      const resolvedCity = (city || parsedData?.city || '').trim() || 'Москва';

      const surveyPayload = {
        specialization_id: specId,
        claimed_grade_id: gradeId,
        skills: skillsToSubmit,
        salary_min: Number(salaryMin) || 150000,
        salary_max: Number(salaryMax) || 250000,
        expected_salary: Number(salaryMin) || 150000,
        consent_personal_data: consentPdn,
        consent_profile_publish: consentPublish,
        city: resolvedCity,
        work_format: 'any',
        relocation_ready: false,
      };

      // 1. Сохранение результатов онбординг-опроса по 152-ФЗ
      await api.post('/candidate-profile/onboarding-survey', surveyPayload);

      // 2. Старт сессии адаптивного тестирования KITE
      const sessionData = await api.post<{ session_id: number; id?: number }>('/assessment/sessions/start', {
        specialization_id: specId,
        claimed_grade_id: gradeId,
      });

      const sessId = sessionData.session_id || sessionData.id;
      if (!sessId) {
        throw new Error('Идентификатор сессии не получен от сервера');
      }
      window.location.href = `/candidate/assessment/${sessId}`;
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Не удалось завершить онбординг или запустить сессию тестирования. Проверьте соединение с сервером.'
      );
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <CandidateLayout currentTab="onboarding">
      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {/* Header & Stepper */}
        <div className="flex flex-col gap-4 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <Badge variant="fsp" size="md">
              ВЕРИФИКАЦИОННЫЙ ОНБОРДИНГ KITE
            </Badge>
            <Badge variant="default" size="sm">
              Этап {step} из 3
            </Badge>
          </div>
          <h1 className="font-mono text-2xl sm:text-3xl font-bold text-white">
            Присвоение верифицированной категории таланта
          </h1>
          <p className="font-sans text-xs sm:text-sm text-[#9B9C9E] max-w-2xl leading-relaxed">
            В соответствии со стандартами ФСП и моделью реверс-рекрутинга, категория не зависит от самописных строк резюме. Ваш грейд подтверждается через адаптивную психометрическую оценку KITE IRT 3PL.
          </p>
        </div>

        {/* Stepper Indicator */}
        <div className="flex items-center justify-between p-4 bg-[#202129] rounded-[12px] border border-[#2D2E37] text-xs font-mono">
          <div className={`flex items-center gap-2 ${step >= 1 ? 'text-[#00F5D4] font-bold' : 'text-[#5F5F66]'}`}>
            <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-[11px]">1</span>
            <span>Загрузка резюме</span>
          </div>
          <FspCircuitConnector orientation="horizontal" variant="accent" className="flex-1 mx-4 max-w-[80px]" />
          <div className={`flex items-center gap-2 ${step >= 2 ? 'text-[#00F5D4] font-bold' : 'text-[#5F5F66]'}`}>
            <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-[11px]">2</span>
            <span>Выбор трека и грейда</span>
          </div>
          <FspCircuitConnector orientation="horizontal" variant="accent" className="flex-1 mx-4 max-w-[80px]" />
          <div className={`flex items-center gap-2 ${step >= 3 ? 'text-[#00F5D4] font-bold' : 'text-[#5F5F66]'}`}>
            <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-[11px]">3</span>
            <span>KITE Тестирование</span>
          </div>
        </div>

        {/* Step 1: Resume Upload */}
        {step === 1 && (
          <div className="flex flex-col gap-6 p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37]">
            <div>
              <h2 className="font-mono text-lg font-bold text-white">Шаг 1: Парсинг PDF-резюме (PyMuPDF)</h2>
              <p className="text-xs text-[#9B9C9E] mt-1">
                Загрузите резюме для автоматического заполнения стека и опыта. Контактные данные будут зашифрованы по 152-ФЗ.
              </p>
            </div>

            <ResumeUploader onParsed={handleResumeParsed} />

            <div className="flex justify-between items-center pt-4 border-t border-[#2D2E37]">
              <span className="text-xs text-[#5F5F66]">
                Нет файла под рукой?
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStep(2)}
              >
                <span>Пропустить и настроить вручную</span>
                <ArrowRight size={14} />
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Track & Grade Selection */}
        {step === 2 && (
          <div className="flex flex-col gap-6 p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37]">
            <div>
              <h2 className="font-mono text-lg font-bold text-white">Шаг 2: Специализация и целевой грейд</h2>
              <p className="text-xs text-[#9B9C9E] mt-1">
                Выберите направление и уровень сложности калибровочного тестирования KITE.
              </p>
            </div>

            {parsedData && (
              <div className="p-4 rounded-[8px] bg-[#1B1C21] border border-[#00F5D4]/30 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-mono text-[#00F5D4]">
                  <CheckCircle size={16} />
                  <span>Резюме успешно распознано PyMuPDF:</span>
                </div>
                <div className="text-xs text-white">
                  <strong>{parsedData.fullName || 'Кандидат'}</strong> • Опыт: {parsedData.experienceYears || 0}+ лет
                  {parsedData.city && <span> • Город: <strong className="text-[#00F5D4]">{parsedData.city}</strong></span>}
                </div>
                <div className="flex flex-wrap gap-2 text-[11px] font-mono text-[#9B9C9E] mt-1">
                  {parsedData.specialization && (
                    <button
                      type="button"
                      onClick={() => setSpecialization(parsedData.specialization!)}
                      className={`px-2 py-0.5 rounded cursor-pointer transition-all border ${
                        specialization === parsedData.specialization
                          ? 'bg-[#402FFF]/20 border-[#402FFF] text-white font-bold'
                          : 'bg-[#2D2E37] border-transparent text-[#00F5D4] hover:border-[#00F5D4]/40'
                      }`}
                      title="Нажмите, чтобы применить трек из резюме"
                    >
                      Авто-трек: {specializations.find(s => s.value === parsedData.specialization)?.label.split(' ')[0] || parsedData.specialization}
                    </button>
                  )}
                  {parsedData.grade && (
                    <button
                      type="button"
                      onClick={() => setClaimedGrade(parsedData.grade!)}
                      className={`px-2 py-0.5 rounded cursor-pointer transition-all border ${
                        claimedGrade === parsedData.grade
                          ? 'bg-[#00F5D4]/20 border-[#00F5D4] text-[#00F5D4] font-bold'
                          : 'bg-[#2D2E37] border-transparent text-[#00F5D4] hover:border-[#00F5D4]/40'
                      }`}
                      title="Нажмите, чтобы применить грейд из резюме"
                    >
                      Грейд: {parsedData.grade.toUpperCase()}
                    </button>
                  )}
                  {parsedData.salaryMin && parsedData.salaryMax && (
                    <button
                      type="button"
                      onClick={() => {
                        setSalaryMin(parsedData.salaryMin!);
                        setSalaryMax(parsedData.salaryMax!);
                      }}
                      className="px-2 py-0.5 rounded cursor-pointer bg-[#2D2E37] text-[#FFD700] hover:border-[#FFD700]/40 border border-transparent transition-all"
                      title="Нажмите, чтобы применить зарплатную вилку из резюме"
                    >
                      Вилка: {parsedData.salaryMin.toLocaleString('ru-RU')} — {parsedData.salaryMax.toLocaleString('ru-RU')} ₽
                    </button>
                  )}
                  {parsedData.city && (
                    <button
                      type="button"
                      onClick={() => setCity(parsedData.city!)}
                      className="px-2 py-0.5 rounded cursor-pointer bg-[#2D2E37] text-[#00F5D4] hover:border-[#00F5D4]/40 border border-transparent transition-all"
                      title="Нажмите, чтобы применить город из резюме"
                    >
                      Город: {parsedData.city}
                    </button>
                  )}
                </div>
                {parsedData.skills && parsedData.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {parsedData.skills.map((s, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#2D2E37] text-[#C8C9CA]">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="flex flex-col gap-5">
              {/* Specialization Selection with Interactive Chips */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-mono font-bold text-white flex items-center justify-between">
                  <span>Специализация (инженерный трек)</span>
                  <span className="text-[11px] text-[#00F5D4] font-normal">Интерактивный выбор</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {specializations.map((spec) => (
                    <button
                      key={spec.value}
                      type="button"
                      onClick={() => setSpecialization(spec.value)}
                      className={`px-3 py-1.5 rounded-[8px] text-xs font-mono transition-all cursor-pointer border ${
                        specialization === spec.value
                          ? 'bg-[#402FFF]/25 border-[#402FFF] text-white font-bold shadow-[0_0_12px_rgba(64,47,255,0.4)]'
                          : 'bg-[#1E1F26] border-[#2D2E37] text-[#9B9C9E] hover:border-[#402FFF]/50 hover:text-white'
                      }`}
                    >
                      {spec.label.split(' (')[0]}
                    </button>
                  ))}
                </div>
                <Select
                  id="specialization"
                  label=""
                  options={specializations}
                  value={specialization}
                  onChange={(e) => setSpecialization(e.target.value)}
                />
              </div>

              {/* Target Grade Selection with Interactive Chips */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-mono font-bold text-white flex items-center justify-between">
                  <span>Заявляемый целевой грейд</span>
                  <span className="text-[11px] text-[#00F5D4] font-normal">Уровень сложности KITE</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {grades.map((gr) => (
                    <button
                      key={gr.value}
                      type="button"
                      onClick={() => setClaimedGrade(gr.value)}
                      className={`px-3 py-1.5 rounded-[8px] text-xs font-mono transition-all cursor-pointer border ${
                        claimedGrade === gr.value
                          ? 'bg-[#00F5D4]/15 border-[#00F5D4] text-[#00F5D4] font-bold shadow-[0_0_12px_rgba(0,245,212,0.3)]'
                          : 'bg-[#1E1F26] border-[#2D2E37] text-[#9B9C9E] hover:border-[#00F5D4]/50 hover:text-white'
                      }`}
                    >
                      {gr.label.split(' (')[0]}
                    </button>
                  ))}
                </div>
                <Select
                  id="claimedGrade"
                  label=""
                  options={grades}
                  value={claimedGrade}
                  onChange={(e) => setClaimedGrade(e.target.value)}
                />
              </div>
            </div>

            {/* City & Location Input with Interactive Quick Chips */}
            <div className="p-4 rounded-[12px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2.5">
              <label htmlFor="candidateCity" className="text-xs font-mono font-bold text-white flex items-center justify-between">
                <span>Город проживания / локация</span>
                <span className="text-[11px] text-[#9B9C9E] font-normal">152-ФЗ локализация</span>
              </label>
              <input
                id="candidateCity"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Например: Москва, Санкт-Петербург, Новосибирск..."
                className="w-full bg-[#202129] border border-[#3D3E42] rounded-[8px] px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#402FFF]"
              />
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] font-mono text-[#9B9C9E]">Быстрый выбор:</span>
                {['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань', 'Удаленно'].map((quickCity) => (
                  <button
                    key={quickCity}
                    type="button"
                    onClick={() => setCity(quickCity)}
                    className={`px-2.5 py-1 rounded-[6px] text-[11px] font-mono border transition-all cursor-pointer ${
                      city === quickCity
                        ? 'bg-[#00F5D4]/15 border-[#00F5D4] text-[#00F5D4] font-bold'
                        : 'bg-[#202129] border-[#3D3E42] text-[#9B9C9E] hover:text-white hover:border-[#402FFF]'
                    }`}
                  >
                    {quickCity}
                  </button>
                ))}
              </div>
              <span className="text-[11px] font-sans text-[#9B9C9E]">
                {parsedData?.city ? `Автоопределен из резюме: ${parsedData.city}. Вы можете скорректировать значение при необходимости.` : 'Укажите город или выберите «Удаленно» для распределенной работы.'}
              </span>
            </div>

            {/* Salary Expectations (Mandatory for reverse-recruiting via SalaryRangeInput) */}
            <div className="p-4 rounded-[12px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-3">
              <SalaryRangeInput
                salaryMin={salaryMin}
                salaryMax={salaryMax}
                onChange={(min, max, valid) => {
                  setSalaryMin(min);
                  setSalaryMax(max);
                  setIsSalaryValid(valid);
                }}
              />
            </div>

            {/* 152-FZ Consents */}
            <div className="p-4 rounded-[12px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2.5">
              <span className="text-xs font-mono font-bold text-white">
                Согласия на обработку данных (152-ФЗ)
              </span>
              <label className="flex items-center gap-2 text-xs font-sans text-[#C8C9CA] cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentPdn}
                  onChange={(e) => setConsentPdn(e.target.checked)}
                  className="rounded bg-[#2D2E37] border-[#3D3E42] text-[#402FFF]"
                />
                <span>Согласие на обработку персональных данных (152-ФЗ)</span>
              </label>
              <label className="flex items-center gap-2 text-xs font-sans text-[#C8C9CA] cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentPublish}
                  onChange={(e) => setConsentPublish(e.target.checked)}
                  className="rounded bg-[#2D2E37] border-[#3D3E42] text-[#402FFF]"
                />
                <span>Согласие на публикацию верифицированного профиля в Банке талантов</span>
              </label>
              {!consentPdn && (
                <div className="p-2.5 rounded-[8px] bg-rose-950/40 border border-rose-500/40 text-[#FB7185] text-xs font-sans flex items-center gap-2 mt-1">
                  <AlertCircle size={16} className="shrink-0" />
                  <span>Согласие на обработку персональных данных (152-ФЗ) является обязательным для участия в платформе и прохождения тестирования</span>
                </div>
              )}
            </div>

            {/* FSP ID Integration Block */}
            <div className="p-4 rounded-[12px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Trophy size={18} className="text-[#FFD700]" />
                  <span className="text-xs font-mono font-bold text-white">
                    Интеграция с реестром ФСП России
                  </span>
                </div>
                <label className="flex items-center gap-2 text-xs font-mono cursor-pointer text-[#00F5D4]">
                  <input
                    type="checkbox"
                    checked={hasFsp}
                    onChange={(e) => setHasFsp(e.target.checked)}
                    className="rounded bg-[#2D2E37] border-[#3D3E42] text-[#402FFF]"
                  />
                  <span>Есть спортивный профиль ФСП</span>
                </label>
              </div>

              {hasFsp ? (
                <div className="flex flex-col sm:flex-row gap-3 items-center">
                  <input
                    type="text"
                    value={fspId}
                    onChange={(e) => setFspId(e.target.value)}
                    placeholder="Введите FSP-ID (например: FSP-RU-2024-9912)"
                    className="flex-1 w-full bg-[#202129] border border-[#3D3E42] rounded-[8px] px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#402FFF]"
                  />
                  <a href="/auth/callback">
                    <Button variant="secondary" size="sm">
                      <span>Привязать через Keycloak OIDC</span>
                    </Button>
                  </a>
                </div>
              ) : (
                <div className="text-[11px] font-sans text-[#9B9C9E] leading-relaxed">
                  <strong>Общий трек (без истории ФСП):</strong> При отсутствии спортивных разрядов алгоритм ранжирования автоматически перераспределяет веса (<code className="text-[#00F5D4]">w = 0.52 / 0.30 / 0.00 / 0.18</code>) в пользу тестирования KITE и коммерческого стека. Никаких штрафов или занижения скоринга.
                </div>
              )}
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-[#2D2E37]">
              <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
                <span>Назад</span>
              </Button>
              <Button
                variant="fsp_mint"
                size="lg"
                disabled={!consentPdn || !isSalaryValid}
                onClick={() => setStep(3)}
              >
                <span>Продолжить к проверке правил</span>
                <ArrowRight size={16} />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Rules & Launch KITE */}
        {step === 3 && (
          <div className="flex flex-col gap-6 p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37]">
            <div className="flex items-center gap-3">
              <Sparkles size={24} className="text-[#00F5D4]" />
              <div>
                <h2 className="font-mono text-lg font-bold text-white">Шаг 3: Калибровка KITE IRT 3PL</h2>
                <p className="text-xs text-[#9B9C9E]">
                  Правила непринудительного тестирования и гарантия защиты от даунгрейда
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2">
                <span className="text-xs font-mono text-[#00F5D4] font-bold">12 Изоморфных Задач</span>
                <p className="text-[11px] text-[#9B9C9E] leading-relaxed">
                  Генерация уникального варианта через HMAC-SHA256. Тест защищен от утечек и шпаргалок. Время: 90 минут.
                </p>
              </div>

              <div className="p-4 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2">
                <span className="text-xs font-mono text-[#402FFF] font-bold">Непринудительный грейдинг</span>
                <p className="text-[11px] text-[#9B9C9E] leading-relaxed">
                  При балле θ &lt; 70 вы не теряете статус: система мгновенно предлагает тест на грейд ниже без 90-дневного кулдауна.
                </p>
              </div>

              <div className="p-4 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2">
                <span className="text-xs font-mono text-[#FFD700] font-bold">Risk-Free Boost (θ ≥ 88)</span>
                <p className="text-[11px] text-[#9B9C9E] leading-relaxed">
                  Уверенная сдача открывает возможность бесплатного буст-теста на следующий грейд без риска отката.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-[8px] bg-[#402FFF]/10 border border-[#402FFF]/30 text-xs text-[#C8C9CA] leading-relaxed flex items-center gap-3">
              <ShieldCheck size={20} className="text-[#00F5D4] shrink-0" />
              <span>
                Выбранная конфигурация: <strong className="text-white uppercase">{specialization}</strong> • Целевой грейд: <strong className="text-white uppercase">{claimedGrade}</strong>.
              </span>
            </div>

            {errorMessage && (
              <div className="p-4 rounded-[8px] bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono flex items-center gap-2">
                <AlertCircle size={16} className="shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-[#2D2E37]">
              <Button variant="ghost" size="sm" onClick={() => setStep(2)}>
                <span>Назад</span>
              </Button>
              <Button
                variant="fsp_mint"
                size="lg"
                isLoading={isStarting}
                onClick={handleStartAssessment}
              >
                <span>Начать тестирование KITE</span>
                <ArrowRight size={16} />
              </Button>
            </div>
          </div>
        )}
      </div>
    </CandidateLayout>
  );
};
export default CandidateOnboardingPage;
