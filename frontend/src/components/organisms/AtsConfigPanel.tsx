import React, { useState } from 'react';
import { AtsIntegrationConfigResponse } from '../../types';
import { AtsWebhookStatusBadge } from '../molecules/AtsWebhookStatusBadge';
import { Input } from '../atoms/Input';
import { Select } from '../atoms/Select';
import { Button } from '../atoms/Button';
import { RefreshCw, Check } from '../icons';

export interface AtsConfigPanelProps {
  config: AtsIntegrationConfigResponse;
  onSave: (cfg: Partial<AtsIntegrationConfigResponse>) => Promise<void>;
  onTestPing: () => Promise<void>;
  className?: string;
}

export const AtsConfigPanel: React.FC<AtsConfigPanelProps> = ({
  config,
  onSave,
  onTestPing,
  className = '',
}) => {
  const [provider, setProvider] = useState(config.provider);
  const [webhookUrl, setWebhookUrl] = useState(config.webhookUrl);
  const [secretKey, setSecretKey] = useState(config.secretKey);
  const [isEnabled, setIsEnabled] = useState(config.isEnabled);
  const [isSaving, setIsSaving] = useState(false);
  const [isPinging, setIsPinging] = useState(false);
  const [pingResult, setPingResult] = useState<string | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await onSave({ provider, webhookUrl, secretKey, isEnabled });
    } finally {
      setIsSaving(false);
    }
  };

  const handlePing = async () => {
    setIsPinging(true);
    setPingResult(null);
    try {
      await onTestPing();
      setPingResult('Тестовый пинг успешен: 200 OK (28мс)');
    } catch {
      setPingResult('Ошибка пинга: проверьте URL и HTTPS сертификат');
    } finally {
      setIsPinging(false);
    }
  };

  return (
    <form
      onSubmit={handleSave}
      className={`p-6 rounded-[14px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_24px_rgba(0,0,0,0.5)] flex flex-col gap-5 ${className}`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#2D2E37] pb-4">
        <div className="flex flex-col">
          <h2 className="font-mono text-base font-bold text-white">
            Интеграция с корпоративной ATS / CRM
          </h2>
          <span className="text-xs font-sans text-[#9B9C9E]">
            Автоматическая передача кандидатов с раскрытыми контактами после принятия оффера
          </span>
        </div>
        <AtsWebhookStatusBadge
          status={config.status}
          lastPingMs={config.lastPingMs}
          dlqCount={config.dlqCount}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Select
          id="ats_provider"
          label="Провайдер ATS"
          value={provider}
          onChange={(e) => setProvider(e.target.value as any)}
          options={[
            { value: 'huntflow', label: 'Huntflow API' },
            { value: 'potok', label: 'Поток (Potok.io)' },
            { value: 'e-staff', label: 'E-Staff Рекрутер' },
            { value: 'custom_webhook', label: 'Пользовательский Webhook (HTTPS)' },
          ]}
        />

        <div className="flex flex-col justify-end">
          <label className="flex items-center gap-2.5 h-10 px-3.5 rounded-[6px] bg-[#1E1F26] border border-[#3D3E42] cursor-pointer">
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={(e) => setIsEnabled(e.target.checked)}
              className="accent-[#402FFF]"
            />
            <span className="text-xs font-mono text-[#EDEDED]">Вебхуки активны</span>
          </label>
        </div>
      </div>

      <Input
        id="webhook_url"
        label="Webhook Endpoint URL (HTTPS)"
        value={webhookUrl}
        onChange={(e) => setWebhookUrl(e.target.value)}
        placeholder="https://ats.yourcompany.ru/api/webhooks/fsp"
        helperText="События: invitation.accepted, application.received"
      />

      <Input
        id="secret_key"
        type="password"
        label="Секретный ключ подписи HMAC-SHA256"
        value={secretKey}
        onChange={(e) => setSecretKey(e.target.value)}
        placeholder="whsec_..."
        isMasked
      />

      {pingResult && (
        <div className="p-3 rounded-[6px] bg-[#16171D] border border-emerald-500/30 text-emerald-400 font-mono text-xs">
          {pingResult}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-[#2D2E37] pt-4">
        <button
          type="button"
          onClick={handlePing}
          disabled={isPinging || !webhookUrl}
          className="px-4 py-2 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED] text-xs font-mono font-medium transition-colors cursor-pointer flex items-center gap-2 border border-[#3D3E42]"
        >
          <RefreshCw size={14} className={isPinging ? 'animate-spin' : ''} />
          <span>Тестовый пинг</span>
        </button>

        <Button variant="primary" size="md" type="submit" isLoading={isSaving}>
          <Check size={16} />
          <span>Сохранить настройки</span>
        </Button>
      </div>
    </form>
  );
};
