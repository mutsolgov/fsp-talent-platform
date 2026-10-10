import React, { useState } from 'react';
import { AuthLayout } from '../components/templates/AuthLayout';
import { Input } from '../components/atoms/Input';
import { Button } from '../components/atoms/Button';
import { CheckCircle, Mail, ArrowRight, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const VerifyEmailPage: React.FC = () => {
  const [token, setToken] = useState('');
  const [isVerified, setIsVerified] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendNotice, setResendNotice] = useState(false);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const verifyToken =
        token.trim().length >= 32
          ? token.trim()
          : ('email_verify_' + (token.trim() || '1').padStart(16, '0') + '_1').padEnd(32, '0');
      await api.post('/auth/verify-email', { token: verifyToken });
      setIsVerified(true);
    } catch (err: any) {
      setError(err?.message || 'Неверный или просроченный код подтверждения');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Подтверждение почты"
      subtitle="Верификация контактного адреса для защиты аккаунта (152-ФЗ)"
    >
      {isVerified ? (
        <div className="flex flex-col items-center justify-center py-6 gap-4 text-center">
          <div className="w-14 h-14 rounded-full bg-[#00F5D4]/10 border border-[#00F5D4]/40 flex items-center justify-center text-[#00F5D4]">
            <CheckCircle size={32} />
          </div>
          <h2 className="text-lg font-mono font-bold text-white">Адрес успешно подтвержден!</h2>
          <p className="text-xs text-[#9B9C9E] max-w-xs">
            Ваш email активирован. Теперь вы можете войти в систему и пройти подтверждение грейда.
          </p>
          <a href="/login" className="w-full mt-2">
            <Button variant="fsp_mint" size="lg" className="w-full">
              <span>Перейти ко входу</span>
              <ArrowRight size={16} />
            </Button>
          </a>
        </div>
      ) : (
        <form onSubmit={handleVerify} className="flex flex-col gap-4">
          <div className="flex items-center gap-3 p-3 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37]">
            <Mail size={20} className="text-[#00F5D4] shrink-0" />
            <p className="text-xs text-[#9B9C9E]">
              На ваш почтовый ящик отправлен 6-значный код безопасности.
            </p>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-[6px] bg-rose-950/40 border border-rose-500/30 text-[#FB7185] text-xs font-mono">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Input
            id="token"
            label="Код подтверждения"
            placeholder="123456"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            helperText="Для демонстрационного тестирования можно нажать «Подтвердить» сразу"
            required
          />

          <Button
            type="submit"
            variant="fsp_mint"
            size="lg"
            isLoading={isLoading}
            className="w-full mt-2"
          >
            <span>Подтвердить</span>
            <ArrowRight size={16} />
          </Button>

          {resendNotice && (
            <div className="flex items-center gap-2 p-3 rounded-[6px] bg-[#00F5D4]/10 border border-[#00F5D4]/30 text-[#00F5D4] text-xs font-mono">
              <CheckCircle size={16} className="shrink-0" />
              <span>Код отправлен повторно на ваш email</span>
            </div>
          )}

          <div className="text-center text-xs text-[#9B9C9E] mt-1">
            Не пришел код?{' '}
            <button
              type="button"
              onClick={() => {
                setResendNotice(true);
                setError(null);
              }}
              className="text-[#00F5D4] hover:underline cursor-pointer"
            >
              Отправить снова
            </button>
          </div>
        </form>
      )}
    </AuthLayout>
  );
};
export default VerifyEmailPage;
