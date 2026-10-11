import React, { useState } from 'react';
import { Download, FileText, RefreshCw, AlertCircle } from '../icons';
import { api } from '../../api/client';

export interface PdfPreviewThumbnailProps {
  candidateId: number;
  mode?: 'auto' | 'anonymized' | 'full';
  className?: string;
}

export const PdfPreviewThumbnail: React.FC<PdfPreviewThumbnailProps> = ({
  candidateId,
  mode = 'auto',
  className = '',
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    if (isDownloading) return;
    setIsDownloading(true);
    setError(null);
    try {
      await api.downloadBlob(
        `/resume-pdf/export-fsp/${candidateId}?mode=${mode}`,
        `fsp_profile_${candidateId}.pdf`
      );
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Не удалось скачать PDF-профиль';
      setError(message);
      setTimeout(() => setError(null), 4000);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div
      className={`group relative rounded-[10px] overflow-hidden border border-[#3D3E42] hover:border-[#402FFF] transition-all bg-[#1E1F26] p-3 flex flex-col items-center gap-2.5 shadow-[0_4px_16px_rgba(0,0,0,0.5)] ${className}`}
    >
      <div className="relative w-full h-32 rounded-[6px] overflow-hidden bg-white/5 flex items-center justify-center border border-[#2D2E37]">
        <img
          src="/brand/example.png"
          alt="Стандартизированный PDF-профиль ФСП"
          className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
        />
        <div className="absolute inset-0 bg-[#1B1C21]/40 flex items-center justify-center group-hover:bg-[#1B1C21]/20 transition-all">
          <FileText size={28} className="text-[#00F5D4]" />
        </div>
      </div>

      <div className="flex flex-col text-center">
        <span className="text-xs font-mono font-medium text-[#EDEDED]">
          PDF-профиль ФСП (FR-CAND-03)
        </span>
        <span className="text-[10px] font-sans text-[#9B9C9E]">
          Формат А4 • JetBrains Mono • ReportLab
        </span>
      </div>

      {error && (
        <div
          role="alert"
          className="w-full p-2 bg-red-500/10 border border-red-500/40 text-red-400 rounded-[6px] text-[10px] font-mono flex items-center gap-1.5"
        >
          <AlertCircle size={12} className="shrink-0" />
          <span className="truncate">{error}</span>
        </div>
      )}

      <button
        type="button"
        onClick={handleDownload}
        disabled={isDownloading}
        aria-label="Скачать PDF ФСП"
        className={`w-full py-1.5 px-3 rounded-[6px] text-white text-xs font-mono font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
          isDownloading
            ? 'bg-[#402FFF]/60 cursor-not-allowed'
            : 'bg-[#402FFF] hover:bg-[#3525E0]'
        }`}
      >
        {isDownloading ? (
          <>
            <RefreshCw size={14} className="animate-spin text-white" />
            <span>Генерация...</span>
          </>
        ) : (
          <>
            <Download size={14} />
            <span>Скачать PDF</span>
          </>
        )}
      </button>
    </div>
  );
};
