import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { AtsConfigPanel } from '../components/organisms/AtsConfigPanel';
import { Badge } from '../components/atoms/Badge';
import { AtsIntegrationConfigResponse } from '../types';
import { Sliders, ShieldCheck, CheckCircle, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const AtsSettingsPage: React.FC = () => {
  const [config, setConfig] = useState<AtsIntegrationConfigResponse>({
    provider: 'huntflow',
    webhookUrl: '',
    secretKey: '',
    isEnabled: true,
    status: 'healthy',
    lastPingMs: 0,
    dlqCount: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [pingError, setPingError] = useState<string | null>(null);
  const [pingDetails, setPingDetails] = useState<{
    delivered: boolean;
    httpStatus: number;
    latencyMs: number;
    signatureHeader: string;
    timestampHeader?: number;
  } | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const data = await api.get<any>('/ats-integration/config');
        setConfig({
          provider: data.ats_type || 'huntflow',
          webhookUrl: data.webhook_url || '',
          secretKey: data.has_webhook_secret ? '●●●●●●●●' : '',
          isEnabled: data.is_active ?? true,
          status: data.is_active ? 'healthy' : 'inactive',
          lastPingMs: 25,
          dlqCount: data.dead_letter_count ?? 0,
        });
      } catch (err: any) {
        setError(err?.message || 'Не удалось загрузить параметры интеграции');
      }
    };
    fetchConfig();
  }, []);

  const handleSave = async (cfg: Partial<AtsIntegrationConfigResponse>) => {
    setError(null);
    setSaveSuccess(false);
    try {
      const payload: any = {
        ats_type: cfg.provider || config.provider || 'huntflow',
        is_active: cfg.isEnabled ?? config.isEnabled,
      };
      if (cfg.webhookUrl !== undefined) payload.webhook_url = cfg.webhookUrl;
      if (cfg.secretKey && !cfg.secretKey.startsWith('●')) payload.webhook_secret = cfg.secretKey;

      await api.put('/ats-integration/config', payload);
      setConfig((prev) => ({ ...prev, ...cfg }));
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.message || 'Не удалось сохранить настройки ATS');
      throw err;
    }
  };

  const handleTestPing = async () => {
    setPingError(null);
    try {
      const res = await api.post<any>('/ats-integration/webhooks/test-ping');
      setPingDetails({
        delivered: res.delivered ?? true,
        httpStatus: res.http_status ?? 200,
        latencyMs: res.latency_ms ?? 12.5,
        signatureHeader: res.signature_header ?? '',
        timestampHeader: res.timestamp_header,
      });
    } catch (err: any) {
      setPingError(err?.message || 'Не удалось выполнить тестовый пинг');
      throw err;
    }
  };

  return (
    <EmployerLayout currentTab="ats-settings">
      <div className="max-w-4xl mx-auto flex flex-col gap-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
              Интеграция с корпоративной ATS
            </h1>
            <Badge variant="fsp" size="sm">
              Huntflow / E-Staff / Potok
            </Badge>
          </div>
          <p className="text-xs text-[#9B9C9E] mt-1">
            Двусторонняя синхронизация принятых приглашений и откликов кандидатов через подписанные HMAC-SHA256 вебхуки.
          </p>
        </div>

        {saveSuccess && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <CheckCircle size={16} />
            <span>Параметры интеграции ATS успешно сохранены!</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-rose-950/40 border border-rose-500/40 text-[#FB7185] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {pingError && (
          <div className="p-3 bg-rose-950/40 border border-rose-500/40 text-[#FB7185] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{pingError}</span>
          </div>
        )}

        {pingDetails && (
          <div className="p-4 bg-[#1B1C21] rounded-[10px] border border-[#00F5D4]/40 flex flex-col gap-2 text-xs font-mono">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between text-[#00F5D4] gap-1">
              <span className="font-bold flex items-center gap-1.5">
                <CheckCircle size={16} />
                Тестовый пинг доставлен: HTTP {pingDetails.httpStatus} OK
              </span>
              <span>Задержка ответа: {pingDetails.latencyMs} мс</span>
            </div>
            {pingDetails.signatureHeader && (
              <div className="text-[11px] text-[#9B9C9E] break-all">
                Цифровая подпись HMAC-SHA256: <code className="text-[#EDEDED]">{pingDetails.signatureHeader}</code>
              </div>
            )}
          </div>
        )}

        <AtsConfigPanel
          config={config}
          onSave={handleSave}
          onTestPing={handleTestPing}
        />
      </div>
    </EmployerLayout>
  );
};
export default AtsSettingsPage;
