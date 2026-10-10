import React, { useState } from 'react';
import { AuthLayout } from '../components/templates/AuthLayout';
import { Input } from '../components/atoms/Input';
import { Button } from '../components/atoms/Button';
import { ConsentCheckboxGroup } from '../components/molecules/ConsentCheckboxGroup';
import { useAuthStore } from '../stores/useAuthStore';
import { ArrowRight, Building, User, ShieldCheck } from '../components/icons';
import { api } from '../api/client';

export const RegisterPage: React.FC = () => {
  const [role, setRole] = useState<'candidate' | 'employer'>('candidate');
  const [fullName, setFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [inn, setInn] = useState('7707083893');
  const [pdnConsent, setPdnConsent] = useState(true);
  const [pubConsent, setPubConsent] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { setAuthSession, setConsents } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !fullName) {
      setError('Заполните все обязательные поля');
      return;
    }

    if (role === 'employer' && (!inn || inn.length < 10)) {
      setError('Для регистрации работодателя укажите корректный ИНН (10 или 12 цифр)');
      return;
    }

    if (!pdnConsent) {
      setError('Согласие на обработку персональных данных (152-ФЗ) обязательно');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const nameParts = fullName.trim().split(/\s+/);
      const firstName = nameParts.length > 1 ? nameParts[0] : (nameParts[0] || 'Иван');
      const lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : 'Пользователь';

      const payload: Record<string, any> = {
        email,
        password,
        role,
        consent_pdn_processing: pdnConsent,
        consent_profile_publication: pubConsent,
        policy_version: 'v1.0-2026',
      };

      if (role === 'candidate') {
        payload.first_name = firstName;
        payload.last_name = lastName;
      } else {
        payload.company_name = companyName.trim() || fullName.trim() || 'ООО Цифровые Решения';
        payload.inn = inn.trim();
      }

      const data = await api.post<any>('/auth/register', payload);

      const accessToken = data.tokens?.access_token || data.access_token || 'demo-jwt-token';
      const refreshToken = data.tokens?.refresh_token || data.refresh_token || 'demo-refresh-token';

      setAuthSession(
        accessToken,
        refreshToken,
        role,
        data.user_id || 2,
        email
      );
      setConsents(pdnConsent, pubConsent);
      window.location.href = role === 'candidate' ? '/candidate/onboarding' : '/employer/needs/new';
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || 'Ошибка регистрации учетной записи');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Создание профиля"
      subtitle="Присоединяйтесь к экосистеме верифицированных талантов ФСП"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && (
          <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-[8px]">
            {error}
          </div>
        )}

        {/* Role Segmented Switcher */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-mono text-[#9B9C9E]">Тип аккаунта:</label>
          <div className="grid grid-cols-2 gap-2 p-1 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37]">
            <button
              type="button"
              onClick={() => setRole('candidate')}
              className={`flex items-center justify-center gap-2 py-2 rounded-[6px] text-xs font-mono transition-all ${
                role === 'candidate'
                  ? 'bg-[#402FFF] text-white font-bold shadow-[0_0_12px_rgba(64,47,255,0.4)]'
                  : 'text-[#9B9C9E] hover:text-white'
              }`}
            >
              <User size={14} />
              <span>ИТ-Специалист</span>
            </button>
            <button
              type="button"
              onClick={() => setRole('employer')}
              className={`flex items-center justify-center gap-2 py-2 rounded-[6px] text-xs font-mono transition-all ${
                role === 'employer'
                  ? 'bg-[#402FFF] text-white font-bold shadow-[0_0_12px_rgba(64,47,255,0.4)]'
                  : 'text-[#9B9C9E] hover:text-white'
              }`}
            >
              <Building size={14} />
              <span>Работодатель</span>
            </button>
          </div>
        </div>

        <Input
          id="fullName"
          label={role === 'candidate' ? 'ФИО соискателя' : 'ФИО представителя / HR'}
          placeholder="Иванов Иван Иванович"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />

        <Input
          id="email"
          type="email"
          label="Рабочий email"
          placeholder="user@organization.ru"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Input
          id="password"
          type="password"
          label="Пароль для доступа"
          placeholder="Минимум 8 символов"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {role === 'employer' && (
          <>
            <Input
              id="companyName"
              label="Наименование организации"
              placeholder="ООО Цифровые Решения"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
            />
            <Input
              id="inn"
              label="ИНН юридического лица"
              placeholder="7707083893"
              value={inn}
              onChange={(e) => setInn(e.target.value.replace(/\D/g, '').slice(0, 12))}
              helperText="10 цифр для организаций или 12 цифр для ИП (проверка по ФНС)"
              required
            />
          </>
        )}

        {/* 152-ФЗ Consents */}
        <div className="pt-2 border-t border-[#2D2E37]">
          <ConsentCheckboxGroup
            pdnProcessing={pdnConsent}
            profilePublication={pubConsent}
            onPdnChange={setPdnConsent}
            onPubChange={setPubConsent}
          />
        </div>

        <Button
          type="submit"
          variant="fsp_mint"
          size="lg"
          isLoading={isLoading}
          className="w-full mt-2"
        >
          <span>Зарегистрироваться</span>
          <ArrowRight size={16} />
        </Button>

        <div className="text-center text-xs text-[#9B9C9E] mt-2">
          Уже есть аккаунт?{' '}
          <a href="/login" className="text-[#00F5D4] font-medium hover:underline">
            Войти в систему
          </a>
        </div>
      </form>
    </AuthLayout>
  );
};
export default RegisterPage;
