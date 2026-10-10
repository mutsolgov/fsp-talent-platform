import React, { useEffect, useState } from 'react';
import { AuthLayout } from '../components/templates/AuthLayout';
import { Spinner } from '../components/atoms/Spinner';
import { useAuthStore } from '../stores/useAuthStore';
import { CheckCircle, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const OidcCallbackPage: React.FC = () => {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Авторизация через Keycloak ФСП ID...');
  const { setAuthSession } = useAuthStore();

  useEffect(() => {
    const processCallback = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        if (!code) {
          setStatus('error');
          setMessage('Код авторизации не получен от провайдера Keycloak ФСП ID (параметр code отсутствует)');
          return;
        }
        const redirectUri = window.location.origin + window.location.pathname;
        const codeVerifier = 'fsp_pkce_verifier_long_enough_random_128';

        // Exchange OIDC code via API client
        const data = await api.post<any>('/fsp-integration/connect', {
          code,
          redirect_uri: redirectUri,
          code_verifier: codeVerifier,
        });

        if (data.access_token) {
          setAuthSession(data.access_token, data.refresh_token || '', data.role || 'candidate', data.user_id || 1, data.email || 'athlete@fsp-russia.ru');
        }
        setStatus('success');
        setMessage(`ФСП ID ${data.fsp_id || ''} успешно верифицирован! Перенаправление в профиль...`);
        setTimeout(() => {
          window.location.href = '/candidate/profile';
        }, 1200);
      } catch (err: any) {
        setStatus('error');
        setMessage(err?.message || 'Ошибка верификации через Keycloak ФСП ID');
      }
    };

    processCallback();
  }, [setAuthSession]);

  return (
    <AuthLayout
      title="Авторизация ФСП ID"
      subtitle="Проверка учетной записи в Едином реестре спортивного программирования"
    >
      <div className="flex flex-col items-center justify-center py-8 gap-4 text-center">
        {status === 'loading' && (
          <>
            <Spinner size="lg" color="#00F5D4" label="Загрузка" />
            <p className="text-sm font-mono text-[#00F5D4] animate-pulse">{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-12 h-12 rounded-full bg-[#00F5D4]/10 border border-[#00F5D4]/40 flex items-center justify-center text-[#00F5D4]">
              <CheckCircle size={28} />
            </div>
            <p className="text-sm font-mono text-white">{message}</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <AlertCircle size={28} />
            </div>
            <p className="text-sm font-mono text-rose-400">{message}</p>
            <a
              href="/login"
              className="mt-4 px-4 py-2 bg-[#2D2E37] text-white rounded-[6px] text-xs font-mono"
            >
              Вернуться на страницу входа
            </a>
          </>
        )}
      </div>
    </AuthLayout>
  );
};
export default OidcCallbackPage;
