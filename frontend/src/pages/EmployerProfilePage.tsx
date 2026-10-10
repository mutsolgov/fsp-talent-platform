import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Input } from '../components/atoms/Input';
import { Spinner } from '../components/atoms/Spinner';
import { Building, ShieldCheck, CheckCircle, AlertCircle } from '../components/icons';
import { api } from '../api/client';

interface EmployerProfileApiResponse {
  id: number;
  user_id: number;
  company_name: string;
  inn: string;
  domain: string;
  is_inn_verified: boolean;
  trust_score: number;
  invite_daily_limit: number;
  invites_sent_today: number;
  last_invite_reset_at: string;
  logo_url: string | null;
  description: string | null;
  city: string;
  website: string | null;
  active_needs_count: number;
  ats_connected: boolean;
  created_at: string;
  updated_at: string;
}

interface EmployerProfileState {
  companyName: string;
  inn: string;
  city: string;
  description: string;
  website: string;
  domain: string;
  trustScore: number;
  isVerifiedInn: boolean;
  activeNeedsCount: number;
  sentInvitationsQuota: number;
  usedInvitationsCount: number;
  atsConnected: boolean;
}

export const EmployerProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<EmployerProfileState>({
    companyName: '',
    inn: '',
    city: 'Москва',
    description: '',
    website: '',
    domain: '',
    trustScore: 50,
    isVerifiedInn: false,
    activeNeedsCount: 0,
    sentInvitationsQuota: 20,
    usedInvitationsCount: 0,
    atsConnected: false,
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  const fetchProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<EmployerProfileApiResponse>('/employer-profiles/me');
      setProfile({
        companyName: data.company_name,
        inn: data.inn,
        city: data.city || 'Москва',
        description: data.description || '',
        website: data.website || '',
        domain: data.domain || '',
        trustScore: data.trust_score,
        isVerifiedInn: data.is_inn_verified,
        activeNeedsCount: data.active_needs_count,
        sentInvitationsQuota: data.invite_daily_limit,
        usedInvitationsCount: data.invites_sent_today,
        atsConnected: data.ats_connected,
      });
    } catch (err: any) {
      setError(err?.data?.message || err?.message || 'Не удалось загрузить данные профиля работодателя');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      const updated = await api.put<EmployerProfileApiResponse>('/employer-profiles/me', {
        company_name: profile.companyName,
        inn: profile.inn,
        city: profile.city,
        description: profile.description,
        website: profile.website,
      });
      setProfile({
        companyName: updated.company_name,
        inn: updated.inn,
        city: updated.city || 'Москва',
        description: updated.description || '',
        website: updated.website || '',
        domain: updated.domain || '',
        trustScore: updated.trust_score,
        isVerifiedInn: updated.is_inn_verified,
        activeNeedsCount: updated.active_needs_count,
        sentInvitationsQuota: updated.invite_daily_limit,
        usedInvitationsCount: updated.invites_sent_today,
        atsConnected: updated.ats_connected,
      });
      setIsEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.data?.message || err?.message || 'Ошибка при сохранении профиля компании');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <EmployerLayout currentTab="needs">
      <div className="flex flex-col gap-8 max-w-4xl mx-auto">
        {/* Error notification banner */}
        {error && (
          <div className="p-4 rounded-[12px] bg-rose-950/40 border border-rose-500/30 text-[#FB7185] text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={18} className="shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={fetchProfile}
              className="px-3 py-1 bg-rose-900/50 hover:bg-rose-800 text-white rounded-[6px] transition-colors cursor-pointer"
            >
              Повторить
            </button>
          </div>
        )}

        {/* Success notification banner */}
        {saveSuccess && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <CheckCircle size={16} />
            <span>Данные компании успешно обновлены</span>
          </div>
        )}

        {/* Loading State */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Spinner size="lg" color="#402FFF" />
            <span className="text-xs font-mono text-[#9B9C9E]">Загрузка профиля компании...</span>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-[12px] bg-[#402FFF]/10 border-2 border-[#402FFF] flex items-center justify-center text-[#402FFF]">
                  <Building size={32} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                      {profile.companyName || 'ООО Компания'}
                    </h1>
                    <Badge variant="fsp" size="md">
                      Trust Score {profile.trustScore}%
                    </Badge>
                  </div>
                  <p className="text-xs text-[#9B9C9E] mt-1 font-mono">
                    ИНН: <span className="text-white">{profile.inn}</span> • Статус аккредитации:{' '}
                    {profile.isVerifiedInn ? 'Проверен ФНС' : 'Ожидает проверки'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 bg-[#00F5D4]/10 border border-[#00F5D4]/30 text-[#00F5D4] text-xs font-mono px-3 py-1.5 rounded-full">
                <ShieldCheck size={16} />
                <span>Верифицированный работодатель</span>
              </div>
            </div>

            {/* Quotas and Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col justify-between">
                <span className="text-xs font-mono text-[#9B9C9E]">Активные потребности команд:</span>
                <div className="font-mono text-2xl font-bold text-white my-1">
                  {profile.activeNeedsCount}
                </div>
                <a href="/employer/needs" className="text-xs font-mono text-[#00F5D4] hover:underline">
                  Управление потребностями →
                </a>
              </div>

              <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col justify-between">
                <span className="text-xs font-mono text-[#9B9C9E]">Лимит прямых приглашений:</span>
                <div className="font-mono text-2xl font-bold text-white my-1">
                  {profile.usedInvitationsCount} / {profile.sentInvitationsQuota}
                </div>
                <span className="text-[11px] text-[#9B9C9E]">
                  Защита от спама (Антифрод ФСП)
                </span>
              </div>

              <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col justify-between">
                <span className="text-xs font-mono text-[#9B9C9E]">Интеграция с ATS:</span>
                <div className="font-mono text-base font-bold text-[#00F5D4] my-1 flex items-center gap-2">
                  <CheckCircle size={18} />
                  <span>{profile.atsConnected ? 'Активно' : 'Не подключено'}</span>
                </div>
                <a href="/employer/ats-settings" className="text-xs font-mono text-[#00F5D4] hover:underline">
                  Настройки вебхуков →
                </a>
              </div>
            </div>

            {/* Legal Profile Details */}
            <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="font-mono text-base font-bold text-white">Реквизиты юридического лица</h2>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setIsEditing(!isEditing);
                    setError(null);
                  }}
                >
                  <span>{isEditing ? 'Отмена' : 'Редактировать'}</span>
                </Button>
              </div>

              {isEditing ? (
                <form onSubmit={handleSave} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    id="companyName"
                    label="Наименование организации"
                    value={profile.companyName}
                    onChange={(e) => setProfile({ ...profile, companyName: e.target.value })}
                    required
                  />
                  <Input
                    id="inn"
                    label="ИНН (10 или 12 знаков)"
                    value={profile.inn}
                    onChange={(e) => setProfile({ ...profile, inn: e.target.value })}
                    required
                  />
                  <Input
                    id="city"
                    label="Город"
                    value={profile.city}
                    onChange={(e) => setProfile({ ...profile, city: e.target.value })}
                    required
                  />
                  <Input
                    id="website"
                    label="Корпоративный сайт"
                    value={profile.website}
                    onChange={(e) => setProfile({ ...profile, website: e.target.value })}
                    placeholder="https://company.ru"
                  />
                  <div className="md:col-span-2 flex flex-col gap-1.5">
                    <label htmlFor="description" className="text-xs font-mono font-medium text-[#C8C9CA] tracking-wide">
                      О компании
                    </label>
                    <textarea
                      id="description"
                      rows={3}
                      value={profile.description}
                      onChange={(e) => setProfile({ ...profile, description: e.target.value })}
                      placeholder="Краткое описание деятельности компании..."
                      className="w-full px-3.5 py-2.5 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-sm border border-[#3D3E42] focus:border-[#402FFF] focus:ring-1 focus:ring-[#402FFF] outline-none transition-colors"
                    />
                  </div>
                  <div className="md:col-span-2 flex gap-3">
                    <Button type="submit" variant="fsp_mint" size="md" disabled={isSaving}>
                      <span>{isSaving ? 'Сохранение...' : 'Сохранить изменения'}</span>
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      size="md"
                      onClick={() => {
                        setIsEditing(false);
                        setError(null);
                      }}
                      disabled={isSaving}
                    >
                      <span>Отмена</span>
                    </Button>
                  </div>
                </form>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                  <div className="p-3 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37]">
                    <span className="text-[#9B9C9E] block mb-1">Юридическое лицо:</span>
                    <span className="text-white font-bold">{profile.companyName || '—'}</span>
                  </div>
                  <div className="p-3 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37]">
                    <span className="text-[#9B9C9E] block mb-1">ИНН:</span>
                    <span className="text-white font-bold">{profile.inn || '—'}</span>
                  </div>
                  <div className="p-3 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37]">
                    <span className="text-[#9B9C9E] block mb-1">Город:</span>
                    <span className="text-white">{profile.city || '—'}</span>
                  </div>
                  <div className="p-3 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37]">
                    <span className="text-[#9B9C9E] block mb-1">Корпоративный сайт:</span>
                    <span className="text-white">
                      {profile.website ? (
                        <a
                          href={profile.website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[#00F5D4] hover:underline"
                        >
                          {profile.website}
                        </a>
                      ) : (
                        '—'
                      )}
                    </span>
                  </div>
                  <div className="p-3 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37] md:col-span-2">
                    <span className="text-[#9B9C9E] block mb-1">О компании:</span>
                    <span className="text-white">{profile.description || 'Описание не заполнено'}</span>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </EmployerLayout>
  );
};

export default EmployerProfilePage;
