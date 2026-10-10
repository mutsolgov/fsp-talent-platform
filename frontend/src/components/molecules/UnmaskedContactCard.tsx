import React from 'react';
import { Mail, Phone, ExternalLink, FileText, Unlock } from '../icons';
import { CopyButton } from '../atoms/CopyButton';

export interface UnmaskedContactCardProps {
  email: string;
  phone?: string;
  telegram?: string;
  githubUrl?: string;
  pdfUrl?: string;
  className?: string;
}

export const UnmaskedContactCard: React.FC<UnmaskedContactCardProps> = ({
  email,
  phone,
  telegram,
  githubUrl,
  pdfUrl,
  className = '',
}) => {
  return (
    <div
      aria-label="Контакты кандидата"
      className={`p-4 rounded-[10px] bg-[#1E1F26] border border-[#00F5D4]/40 shadow-[0_0_16px_rgba(0,245,212,0.15)] flex flex-col gap-3 ${className}`}
    >
      <div className="flex items-center justify-between border-b border-[#2D2E37] pb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[#00F5D4]/20 flex items-center justify-center text-[#00F5D4]">
            <Unlock size={14} />
          </div>
          <span className="text-xs font-mono font-bold text-[#00F5D4]">
            Контакты подтверждены и открыты
          </span>
        </div>
        <span className="text-[11px] font-mono text-[#9B9C9E]">152-ФЗ Согласие получено</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
        <div className="flex items-center justify-between p-2 rounded-[6px] bg-[#1B1C21] border border-[#2D2E37]">
          <div className="flex items-center gap-2 overflow-hidden">
            <Mail size={14} className="text-[#9B9C9E] shrink-0" />
            <a href={`mailto:${email}`} className="text-[#EDEDED] hover:text-[#402FFF] truncate">
              {email}
            </a>
          </div>
          <CopyButton textToCopy={email} />
        </div>

        {phone && (
          <div className="flex items-center justify-between p-2 rounded-[6px] bg-[#1B1C21] border border-[#2D2E37]">
            <div className="flex items-center gap-2 overflow-hidden">
              <Phone size={14} className="text-[#9B9C9E] shrink-0" />
              <a href={`tel:${phone}`} className="text-[#EDEDED] hover:text-[#402FFF] truncate">
                {phone}
              </a>
            </div>
            <CopyButton textToCopy={phone} />
          </div>
        )}

        {telegram && (
          <div className="flex items-center justify-between p-2 rounded-[6px] bg-[#1B1C21] border border-[#2D2E37]">
            <span className="text-[#9B9C9E]">Telegram:</span>
            <a
              href={`https://t.me/${telegram.replace('@', '')}`}
              target="_blank"
              rel="noreferrer"
              className="text-[#00F5D4] hover:underline flex items-center gap-1"
            >
              {telegram} <ExternalLink size={12} />
            </a>
          </div>
        )}

        {githubUrl && (
          <div className="flex items-center justify-between p-2 rounded-[6px] bg-[#1B1C21] border border-[#2D2E37]">
            <span className="text-[#9B9C9E]">GitHub:</span>
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className="text-[#00F5D4] hover:underline flex items-center gap-1 truncate max-w-[150px]"
            >
              {githubUrl.replace('https://github.com/', '')} <ExternalLink size={12} />
            </a>
          </div>
        )}
      </div>

      {pdfUrl && (
        <a
          href={pdfUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 mt-1 py-2 px-3 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED] text-xs font-mono font-medium transition-colors border border-[#3D3E42]"
        >
          <FileText size={14} className="text-[#402FFF]" />
          Скачать оригинальное резюме кандидата
        </a>
      )}
    </div>
  );
};
