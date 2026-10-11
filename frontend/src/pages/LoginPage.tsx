import React, { useState } from 'react';
import { AuthLayout } from '../components/templates/AuthLayout';
import { Input } from '../components/atoms/Input';
import { Button } from '../components/atoms/Button';
import { FspLogo } from '../components/atoms/FspLogo';
import { useAuthStore } from '../stores/useAuthStore';
import { ArrowRight, ShieldCheck } from '../components/icons';
import { api } from '../api/client';

function generateRandomString(length: number = 64): string {
  const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const array = new Uint8Array(length);
  window.crypto.getRandomValues(array);
  return Array.from(array, (dec) => charset[dec % charset.length]).join('');
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await window.crypto.subtle.digest('SHA-256', data);
  const base64 = btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return base64;
}

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFspLoading, setIsFspLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { setAuthSession } = useAuthStore();

  const handleFspLogin = async () => {
    setIsFspLoading(true);
    setError(null);
    try {
      const codeVerifier = generateRandomString(64);
      const codeChallenge = await generateCodeChallenge(codeVerifier);
      const oidcState = generateRandomString(32);
      sessionStorage.setItem('fsp_pkce_verifier', codeVerifier);
      sessionStorage.setItem('fsp_oidc_state', oidcState);

      const redirectUri = `${window.location.origin}/auth/callback`;
      const keycloakAuthUrl = `/auth/realms/fsp-realm/protocol/openid-connect/auth?client_id=fsp-frontend&redirect_uri=${encodeURIComponent(
        redirectUri
      )}&response_type=code&scope=openid+email+profile&code_challenge=${codeChallenge}&code_challenge_method=S256&state=${encodeURIComponent(oidcState)}`;

      window.location.href = keycloakAuthUrl;
    } catch (err: any) {
      setError('Не удалось инициализировать защищенную OIDC сессию ФСП ID');
      setIsFspLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Заполните все обязательные поля');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.post<{
        access_token: string;
        refresh_token: string;
        role: 'candidate' | 'employer' | 'admin';
        user_id: number;
        email: string;
      }>('/auth/login', { email, password });

      const role = data.role || (email.includes('employer') ? 'employer' : 'candidate');
      setAuthSession(
        data.access_token,
        data.refresh_token,
        role,
        data.user_id,
        data.email || email
      );
      window.location.href =
        role === 'employer'
          ? '/employer/candidate-bank'
          : role === 'admin'
          ? '/admin/audit-logs'
          : '/candidate/profile';
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || 'Неверный логин или пароль');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Вход в систему"
      subtitle="Единая платформа ИТ-талантов и работодателей ФСП России"
    >
      <div className="flex flex-col gap-4">
        {error && (
          <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-[8px]">
            {error}
          </div>
        )}

        {/* Corporate Keycloak OIDC Authentication */}
        <div className="flex flex-col gap-3">
          <button
            type="button"
            onClick={handleFspLogin}
            disabled={isFspLoading}
            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-[8px] bg-gradient-to-r from-[#402FFF] to-[#2A1FAF] hover:from-[#4E3DFF] hover:to-[#3828CC] text-white font-medium shadow-lg shadow-[#402FFF]/20 border border-[#402FFF]/40 transition-all cursor-pointer group disabled:opacity-50"
          >
            <div className="w-6 h-6 flex items-center justify-center bg-white/10 rounded-full p-1 group-hover:scale-105 transition-transform">
              <FspLogo variant="mark" width={18} height={18} theme="dark" />
            </div>
            <span className="text-sm font-semibold tracking-wide">
              {isFspLoading ? 'Перенаправление в Keycloak...' : 'Войти через ФСП ID'}
            </span>
            <ShieldCheck size={18} className="text-[#00F5D4] ml-auto" />
          </button>

          <div className="relative flex items-center justify-center py-2">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#2D2E37]"></div>
            </div>
            <span className="relative px-3 bg-[#202129] text-[11px] font-mono text-[#9B9C9E] uppercase tracking-wider">
              или через учетные данные
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            id="email"
            type="email"
            label="Электронная почта"
            placeholder="developer@example.ru"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <Input
            id="password"
            type="password"
            label="Пароль"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <div className="flex items-center justify-between text-xs text-[#9B9C9E]">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" defaultChecked className="rounded bg-[#2D2E37] border-[#3D3E42] text-[#402FFF]" />
              <span>Запомнить сессию</span>
            </label>
            <a href="/verify-email" className="text-[#00F5D4] hover:underline">
              Забыли пароль?
            </a>
          </div>

          <Button
            type="submit"
            variant="fsp_mint"
            size="lg"
            isLoading={isLoading}
            className="w-full mt-2"
          >
            <span>Войти</span>
            <ArrowRight size={16} />
          </Button>
        </form>

        <div className="text-center text-xs text-[#9B9C9E] mt-2">
          Нет учетной записи?{' '}
          <a href="/register" className="text-[#00F5D4] font-medium hover:underline">
            Зарегистрироваться
          </a>
        </div>
      </div>
    </AuthLayout>
  );
};

export default LoginPage;
