import React, { useState } from 'react';
import { AuthLayout } from '../components/templates/AuthLayout';
import { Input } from '../components/atoms/Input';
import { Button } from '../components/atoms/Button';
import { useAuthStore } from '../stores/useAuthStore';
import { ArrowRight, Lock, Mail, ShieldCheck } from '../components/icons';
import { api } from '../api/client';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { setAuthSession } = useAuthStore();

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

  const handleQuickDemoLogin = async (role: 'candidate' | 'employer' | 'admin') => {
    const demoEmail = `${role}@fsp-demo.ru`;
    try {
      const demoRole = role === 'candidate' ? 'candidate_with_fsp' : role;
      const data = await api.post<any>('/demo/switch-role', { role: demoRole });
      setAuthSession(data.access_token, data.access_token, data.role, data.user_id, data.email);
    } catch {
      setAuthSession(`mock-jwt-${role}`, `mock-refresh-${role}`, role, 1, demoEmail);
    }
    if (role === 'candidate') window.location.href = '/candidate/profile';
    else if (role === 'employer') window.location.href = '/employer/candidate-bank';
    else window.location.href = '/demo/dashboard';
  };

  return (
    <AuthLayout
      title="Вход в систему"
      subtitle="Единая платформа ИТ-талантов и работодателей ФСП России"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && (
          <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-[8px]">
            {error}
          </div>
        )}

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

        <div className="flex flex-col gap-2 pt-2 border-t border-[#2D2E37]">
          <span className="text-[11px] font-mono text-[#9B9C9E] text-center">
            Быстрый вход для жюри (1 клик):
          </span>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => handleQuickDemoLogin('candidate')}
              className="px-2 py-1.5 rounded-[6px] text-xs font-mono bg-[#2D2E37] hover:bg-[#3D3E42] text-[#00F5D4] border border-[#00F5D4]/20"
            >
              Кандидат
            </button>
            <button
              type="button"
              onClick={() => handleQuickDemoLogin('employer')}
              className="px-2 py-1.5 rounded-[6px] text-xs font-mono bg-[#2D2E37] hover:bg-[#3D3E42] text-[#402FFF] border border-[#402FFF]/20"
            >
              Работодатель
            </button>
            <button
              type="button"
              onClick={() => handleQuickDemoLogin('admin')}
              className="px-2 py-1.5 rounded-[6px] text-xs font-mono bg-[#2D2E37] hover:bg-[#3D3E42] text-[#FFD700] border border-[#FFD700]/20"
            >
              Жюри/Admin
            </button>
          </div>
        </div>

        <div className="text-center text-xs text-[#9B9C9E] mt-2">
          Нет учетной записи?{' '}
          <a href="/register" className="text-[#00F5D4] font-medium hover:underline">
            Зарегистрироваться
          </a>
        </div>
      </form>
    </AuthLayout>
  );
};
export default LoginPage;
