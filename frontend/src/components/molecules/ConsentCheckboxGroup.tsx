import React from 'react';
import { Checkbox } from '../atoms/Checkbox';

export interface ConsentCheckboxGroupProps {
  pdnProcessing: boolean;
  profilePublication: boolean;
  onPdnChange: (v: boolean) => void;
  onPubChange: (v: boolean) => void;
  error?: string;
  className?: string;
}

export const ConsentCheckboxGroup: React.FC<ConsentCheckboxGroupProps> = ({
  pdnProcessing,
  profilePublication,
  onPdnChange,
  onPubChange,
  error,
  className = '',
}) => {
  return (
    <div className={`flex flex-col gap-3 p-3.5 rounded-[8px] bg-[#1E1F26] border border-[#3D3E42] ${className}`}>
      <span className="text-xs font-mono font-medium text-[#C8C9CA] tracking-wide">
        Согласия на обработку персональных данных (152-ФЗ РФ)
      </span>

      <Checkbox
        id="consent_pdn_processing"
        checked={pdnProcessing}
        onChange={onPdnChange}
        required
        label={
          <span>
            Я даю согласие на обработку моих персональных данных в соответствии со{' '}
            <strong className="text-[#00F5D4]">ст. 9 Федерального закона № 152-ФЗ</strong> и{' '}
            <a href="#privacy-policy" className="text-[#402FFF] underline hover:text-[#00F5D4]">
              Политикой конфиденциальности платформы ФСП
            </a>
          </span>
        }
      />

      <Checkbox
        id="consent_profile_publication"
        checked={profilePublication}
        onChange={onPubChange}
        required
        label={
          <span>
            Я даю согласие на распространение персональных данных и размещение верифицированного профиля в витрине платформы согласно{' '}
            <strong className="text-[#00F5D4]">ст. 10.1 Федерального закона № 152-ФЗ</strong> (контакты скрыты до подтверждения)
          </span>
        }
      />

      {error && <span className="text-xs font-mono text-[#FB7185] mt-1">{error}</span>}
    </div>
  );
};
