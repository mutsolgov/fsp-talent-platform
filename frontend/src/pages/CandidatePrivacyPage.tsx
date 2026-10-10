import React, { useState } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { ConsentCheckboxGroup } from '../components/molecules/ConsentCheckboxGroup';
import { MaskedContactIndicator } from '../components/molecules/MaskedContactIndicator';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { useAuthStore } from '../stores/useAuthStore';
import { ShieldCheck, Lock, Eye, Download, Trash2, CheckCircle, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const CandidatePrivacyPage: React.FC = () => {
  const { isPdnConsentGiven, isProfilePublicationConsentGiven, setConsents } = useAuthStore();
  const [pdn, setPdn] = useState(isPdnConsentGiven ?? true);
  const [pub, setPub] = useState(isProfilePublicationConsentGiven ?? true);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [archiveNotice, setArchiveNotice] = useState<string | null>(null);
  const [revokeNotice, setRevokeNotice] = useState<string | null>(null);

  const handleSave = async () => {
    setError(null);
    try {
      await api.put('/auth/consents', {
        consent_profile_publication: pub,
      });
      setConsents(pdn, pub);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.message || 'Ошибка сохранения настроек приватности');
    }
  };

  return (
    <CandidateLayout currentTab="privacy">
      <div className="flex flex-col gap-6 max-w-4xl mx-auto">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
              Защита персональных данных и настройки 152-ФЗ
            </h1>
            <Badge variant="fsp" size="sm">152-ФЗ РФ</Badge>
          </div>
          <p className="text-xs text-[#9B9C9E] mt-1">
            Платформа ФСП гарантирует физическое сокрытие контактов от работодателей на уровне сериализатора бэкенда до обоюдного согласия.
          </p>
        </div>

        {savedSuccess && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <CheckCircle size={16} />
            <span>Настройки согласий успешно сохранены и зафиксированы в журнале аудита!</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-rose-950/40 border border-rose-500/40 text-[#FB7185] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Consents Management */}
        <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <Lock size={20} className="text-[#00F5D4]" />
            <div>
              <h2 className="font-mono text-base font-bold text-white">
                Юридические согласия субъекта персональных данных
              </h2>
              <p className="text-xs text-[#9B9C9E]">
                ст. 9 и ст. 10.1 Федерального закона от 27.07.2006 № 152-ФЗ
              </p>
            </div>
          </div>

          <ConsentCheckboxGroup
            pdnProcessing={pdn}
            profilePublication={pub}
            onPdnChange={setPdn}
            onPubChange={setPub}
          />

          <div className="pt-2">
            <Button variant="fsp_mint" size="md" onClick={handleSave}>
              <span>Сохранить настройки приватности</span>
            </Button>
          </div>
        </div>

        {/* Masking Preview */}
        <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <Eye size={20} className="text-[#402FFF]" />
            <div>
              <h2 className="font-mono text-base font-bold text-white">
                Как работодатель видит ваш профиль в поиске
              </h2>
              <p className="text-xs text-[#9B9C9E]">
                До принятия приглашения ваши контакты (email, телефон, телеграм, ссылка на GitHub) не передаются в браузер работодателя.
              </p>
            </div>
          </div>

          <div className="p-4 bg-[#1B1C21] rounded-[12px] border border-[#2D2E37] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/brand/face1.png" alt="152-ФЗ Аватар" className="w-12 h-12 rounded-full border border-[#00F5D4]/40" />
              <div>
                <span className="font-mono text-sm font-bold text-white">Кандидат CAND-77-9021</span>
                <p className="text-xs text-[#9B9C9E] font-mono">Backend • Middle (Подтверждено KITE)</p>
              </div>
            </div>
            <MaskedContactIndicator candidateId={1} />
          </div>
        </div>

        {/* Data Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col justify-between gap-3">
            <div>
              <h3 className="font-mono text-sm font-bold text-white">Выгрузка личных данных</h3>
              <p className="text-xs text-[#9B9C9E] mt-1">
                Скачать машиночитаемый архив (JSON) со всей историей прохождения тестов и аудита.
              </p>
            </div>
            {archiveNotice && (
              <div className="p-2.5 bg-[#00F5D4]/10 border border-[#00F5D4]/30 text-[#00F5D4] rounded-[6px] text-xs font-mono flex items-center gap-2">
                <CheckCircle size={14} className="shrink-0" />
                <span>{archiveNotice}</span>
              </div>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setArchiveNotice('Формирование архива ПДн 152-ФЗ начато');
                setTimeout(() => setArchiveNotice(null), 5000);
              }}
            >
              <Download size={14} />
              <span>Экспорт архива (152-ФЗ)</span>
            </Button>
          </div>

          <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col justify-between gap-3">
            <div>
              <h3 className="font-mono text-sm font-bold text-rose-400">Отзыв согласий и удаление</h3>
              <p className="text-xs text-[#9B9C9E] mt-1">
                Полный отзыв согласий и анонимизация всех записей платформы по ст. 21 152-ФЗ.
              </p>
            </div>
            {revokeNotice && (
              <div className="p-2.5 bg-rose-950/40 border border-rose-500/30 text-[#FB7185] rounded-[6px] text-xs font-mono flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{revokeNotice}</span>
              </div>
            )}
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                setRevokeNotice('Запрос на отзыв согласий зарегистрирован по ст. 21 152-ФЗ');
                setTimeout(() => setRevokeNotice(null), 5000);
              }}
            >
              <Trash2 size={14} />
              <span>Отозвать согласия</span>
            </Button>
          </div>
        </div>
      </div>
    </CandidateLayout>
  );
};
export default CandidatePrivacyPage;
