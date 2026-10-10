import React, { useState, useEffect } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { FspRankBadge } from '../components/molecules/FspRankBadge';
import { CooldownTimer } from '../components/molecules/CooldownTimer';
import { PdfPreviewThumbnail } from '../components/molecules/PdfPreviewThumbnail';
import { RadarMatchChart } from '../components/molecules/RadarMatchChart';
import { User, Mail, ShieldCheck, Trophy, Sparkles, FileText, Code, Check, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const CandidateProfilePage: React.FC = () => {
  const [candidate, setCandidate] = useState<{
    id: number;
    fullName: string;
    specialization: string;
    verifiedGrade: string;
    fspId: string | null;
    sportRank: any;
    isFspVerified: boolean;
    theta: number;
    freshnessScore: number;
    cooldownUntil: string | null;
    skills: string[];
    maskedCode: string;
    bio: string;
    is_published: boolean;
  } | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [bioText, setBioText] = useState('');
  const [isSavingBio, setIsSavingBio] = useState(false);
  const [bioError, setBioError] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [isTogglingPublish, setIsTogglingPublish] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  const fetchProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<any>('/candidate-profile/me');
      if (data) {
        const fullName =
          data.first_name && data.last_name
            ? `${data.first_name} ${data.last_name}`
            : data.first_name || data.last_name || data.fullName || 'Кандидат ФСП';
        const skills = Array.isArray(data.skills)
          ? data.skills.map((s: any) => (typeof s === 'string' ? s : s.skill_name || s.name || ''))
          : [];
        const thetaScore = Number(data.kite_score_scaled ?? data.theta ?? 0);
        const bio = data.bio || data.about || '';
        setBioText(bio);

        setCandidate({
          id: data.id || 1,
          fullName,
          skills,
          verifiedGrade: data.grade || data.verified_grade || 'Middle',
          specialization: data.specialization || 'Backend',
          fspId: data.fsp_id || null,
          sportRank: data.fsp_badge || '1Р',
          isFspVerified: Boolean(data.fsp_id || data.fsp_verified || data.is_fsp_verified),
          theta: thetaScore,
          freshnessScore: Number(data.freshness_score ?? 50),
          cooldownUntil: data.cooldown_until || null,
          maskedCode: data.maskedCode || `CAND-77-${String(data.id || 1).padStart(4, '0')}`,
          bio,
          is_published: Boolean(data.is_published),
        });
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Не удалось загрузить профиль соискателя с сервера.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSaveBio = async () => {
    setIsSavingBio(true);
    setBioError(null);
    try {
      await api.put('/candidate-profile/me', { bio: bioText });
      setCandidate((prev) => (prev ? { ...prev, bio: bioText } : null));
      setIsEditing(false);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: unknown) {
      setBioError(err instanceof Error ? err.message : 'Ошибка сохранения биографии');
    } finally {
      setIsSavingBio(false);
    }
  };

  const handleTogglePublish = async () => {
    if (!candidate) return;
    setIsTogglingPublish(true);
    setPublishError(null);
    const newStatus = !candidate.is_published;
    try {
      await api.put('/candidate-profile/privacy', { is_published: newStatus });
      setCandidate((prev) => (prev ? { ...prev, is_published: newStatus } : null));
    } catch (err: unknown) {
      setPublishError(
        err instanceof Error ? err.message : 'Не удалось обновить статус видимости'
      );
    } finally {
      setIsTogglingPublish(false);
    }
  };

  return (
    <CandidateLayout currentTab="profile">
      <div className="flex flex-col gap-8 max-w-5xl mx-auto">
        {error ? (
          <div className="p-8 bg-[#202129] rounded-[16px] border border-red-500/30 text-center flex flex-col items-center gap-4">
            <AlertCircle size={32} className="text-red-400" />
            <h2 className="text-white font-mono text-base font-bold">
              Не удалось загрузить профиль соискателя
            </h2>
            <p className="text-red-300 font-mono text-xs max-w-md">
              {error}
            </p>
            <Button variant="fsp_mint" size="sm" onClick={fetchProfile}>
              <span>Повторить попытку</span>
            </Button>
          </div>
        ) : isLoading || !candidate ? (
          <div className="p-12 bg-[#202129] rounded-[16px] border border-[#2D2E37] text-center flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-[#00F5D4] border-t-transparent rounded-full animate-spin" />
            <span className="font-mono text-xs text-[#9B9C9E]">
              Загрузка верифицированного профиля ФСП...
            </span>
          </div>
        ) : (
          <>
            {/* Profile Hero Header */}
            <div className="p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-[#402FFF]/10 border-2 border-[#402FFF] flex items-center justify-center text-[#402FFF]">
                  <User size={32} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                      {candidate.fullName}
                    </h1>
                    <Badge variant="fsp" size="md">
                      {candidate.specialization} • {candidate.verifiedGrade}
                    </Badge>
                  </div>
                  <p className="text-xs text-[#9B9C9E] mt-1 font-mono">
                    Идентификатор 152-ФЗ: <span className="text-[#00F5D4]">{candidate.maskedCode}</span> • Реверс-рекрутинг активен
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex items-center gap-2">
                  <Badge variant={candidate.is_published ? 'fsp' : 'default'} size="sm">
                    {candidate.is_published ? 'Опубликован' : 'Скрыт'}
                  </Badge>
                  <Button
                    variant={candidate.is_published ? 'secondary' : 'fsp_mint'}
                    size="sm"
                    isLoading={isTogglingPublish}
                    onClick={handleTogglePublish}
                  >
                    <span>{candidate.is_published ? 'Скрыть из поиска' : 'Опубликовать'}</span>
                  </Button>
                </div>

                <FspRankBadge
                  rank={candidate.sportRank}
                  isFspVerified={candidate.isFspVerified}
                  contestCount={6}
                />
              </div>
            </div>

            {publishError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-[8px] text-xs font-mono flex items-center justify-between">
                <span>{publishError}</span>
                <button type="button" onClick={() => setPublishError(null)} className="cursor-pointer">✕</button>
              </div>
            )}

            {/* Status Highlights Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Freshness Score */}
              <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col justify-between">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-[#9B9C9E]">Актуальность профиля:</span>
                  <span className="text-xs font-mono font-bold text-[#00F5D4]">{candidate.freshnessScore}%</span>
                </div>
                <div className="w-full bg-[#1B1C21] h-2 rounded-full overflow-hidden mb-3">
                  <div
                    className="bg-gradient-to-r from-[#00F5D4] to-[#402FFF] h-full rounded-full"
                    style={{ width: `${candidate.freshnessScore}%` }}
                  />
                </div>
                <a href="/candidate/challenges" className="text-xs font-mono text-[#00F5D4] hover:underline flex items-center gap-1">
                  <span>Решить челлендж (+18%)</span>
                  <Sparkles size={12} />
                </a>
              </div>

              {/* KITE Theta */}
              <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col justify-between">
                <span className="text-xs font-mono text-[#9B9C9E]">Балл KITE IRT:</span>
                <div className="font-mono text-2xl font-bold text-white my-1">
                  θ = {candidate.theta} <span className="text-xs text-[#00F5D4]">/ 100</span>
                </div>
                <span className="text-[11px] text-[#9B9C9E]">
                  Верифицировано независимой психометрикой
                </span>
              </div>

              {/* Cooldown Timer */}
              <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
                <CooldownTimer
                  cooldownUntil={candidate.cooldownUntil}
                  candidateId={candidate.id}
                />
              </div>
            </div>

            {/* Bio / About Section */}
            <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText size={18} className="text-[#00F5D4]" />
                  <h2 className="font-mono text-sm font-bold text-white">Инженерный профиль и опыт</h2>
                </div>
                {!isEditing ? (
                  <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                    <span>Редактировать bio</span>
                  </Button>
                ) : (
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => { setIsEditing(false); setBioText(candidate.bio); }}>
                      <span>Отмена</span>
                    </Button>
                    <Button variant="fsp_mint" size="sm" isLoading={isSavingBio} onClick={handleSaveBio}>
                      <span>Сохранить</span>
                    </Button>
                  </div>
                )}
              </div>

              {bioError && (
                <div className="text-xs text-red-400 font-mono">{bioError}</div>
              )}
              {savedSuccess && (
                <div className="text-xs text-[#00F5D4] font-mono flex items-center gap-1">
                  <Check size={14} />
                  <span>Информация успешно сохранена на сервере!</span>
                </div>
              )}

              {isEditing ? (
                <textarea
                  value={bioText}
                  onChange={(e) => setBioText(e.target.value)}
                  rows={4}
                  placeholder="Расскажите о своем инженерном опыте, проектах и специализации..."
                  className="w-full bg-[#1B1C21] border border-[#3D3E42] rounded-[8px] p-3 text-xs font-mono text-white focus:outline-none focus:border-[#402FFF]"
                />
              ) : (
                <p className="text-xs text-[#C8C9CA] leading-relaxed whitespace-pre-line font-sans">
                  {candidate.bio || 'Инженерное описание пока не заполнено. Нажмите «Редактировать bio», чтобы рассказать о себе.'}
                </p>
              )}
            </div>

            {/* Competencies & PDF Export Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Skills and Stack */}
              <div className="lg:col-span-2 p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-mono text-sm font-bold text-white">Подтвержденный технологический стек</h2>
                  <span className="text-xs text-[#9B9C9E] font-mono">{candidate.skills.length} навыков</span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {candidate.skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1.5 rounded-[8px] text-xs font-mono bg-[#1B1C21] border border-[#2D2E37] text-white flex items-center gap-1.5"
                    >
                      <Check size={12} className="text-[#00F5D4]" />
                      <span>{skill}</span>
                    </span>
                  ))}
                </div>

                <div className="pt-4 border-t border-[#2D2E37]">
                  <h3 className="font-mono text-xs font-bold text-white mb-2">Многофакторное позиционирование:</h3>
                  <div className="flex justify-center py-2">
                    <RadarMatchChart
                      testMatch={candidate.theta}
                      stackMatch={90}
                      fspMatch={candidate.isFspVerified ? 80 : 0}
                      freshnessMatch={candidate.freshnessScore}
                      isFspProfile={candidate.isFspVerified}
                      size={220}
                    />
                  </div>
                </div>
              </div>

              {/* Standardized PDF Profile (FR-CAND-03) */}
              <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <FileText size={18} className="text-[#402FFF]" />
                    <h3 className="font-mono text-sm font-bold text-white">Стандартизированный PDF ФСП</h3>
                  </div>
                  <p className="text-xs text-[#9B9C9E] leading-relaxed mb-4">
                    Сгенерированный ReportLab эталонный профиль по макету брендбука с синим акцентом #402FFF и шрифтом JetBrains Mono. Контакты маскируются до обоюдного согласия.
                  </p>

                  <PdfPreviewThumbnail candidateId={candidate.id} mode="auto" />
                </div>

                <div className="pt-2">
                  <a href="/candidate/invitations">
                    <Button variant="secondary" size="sm" className="w-full">
                      <span>Входящие приглашения</span>
                    </Button>
                  </a>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </CandidateLayout>
  );
};
export default CandidateProfilePage;
