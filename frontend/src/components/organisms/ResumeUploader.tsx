import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from '../icons';
import { Spinner } from '../atoms/Spinner';
import { api } from '../../api/client';

export interface ResumeParsedResponse {
  fullName?: string;
  email?: string;
  phone?: string;
  skills?: string[];
  experienceYears?: number;
  extractedTextSnippet?: string;
}

export interface ResumeUploaderProps {
  onParsed: (data: ResumeParsedResponse) => void;
  className?: string;
}

export const ResumeUploader: React.FC<ResumeUploaderProps> = ({ onParsed, className = '' }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    if (file.type !== 'application/pdf') {
      setError('Поддерживаются только файлы резюме в формате PDF (PyMuPDF parser)');
      return;
    }

    setError(null);
    setFileName(file.name);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const data = await api.post<any>('/resume-pdf/upload', formData);
      const fullName =
        [data.detected_first_name, data.detected_last_name].filter(Boolean).join(' ') ||
        data.fullName ||
        '';
      const email = data.detected_email || data.email || '';
      const phone = data.detected_phone || data.phone;
      const skills = data.extracted_skills || data.detected_skills || data.skills || [];
      const experienceYears = data.total_experience_months
        ? Math.round(data.total_experience_months / 12)
        : data.experienceYears || 0;

      onParsed({
        fullName,
        email,
        phone,
        skills,
        experienceYears,
      });
    } catch (err: any) {
      setError(err?.message || 'Ошибка парсинга PDF');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`flex flex-col gap-3 w-full ${className}`}>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
        className={`relative p-8 rounded-[12px] border-2 border-dashed transition-all flex flex-col items-center justify-center gap-3 text-center cursor-pointer select-none ${
          isDragging
            ? 'border-[#402FFF] bg-[#402FFF]/10'
            : 'border-[#3D3E42] bg-[#1E1F26] hover:border-[#402FFF]/50'
        }`}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
          className="absolute inset-0 opacity-0 cursor-pointer"
        />

        <div className="w-12 h-12 rounded-full bg-[#402FFF]/15 border border-[#402FFF]/30 flex items-center justify-center text-[#402FFF]">
          {isLoading ? <Spinner size="md" /> : <Upload size={24} />}
        </div>

        <div className="flex flex-col gap-1">
          <span className="font-mono text-sm font-bold text-white">
            {fileName || 'Перетащите PDF-резюме сюда'}
          </span>
          <span className="text-xs font-sans text-[#9B9C9E]">
            или нажмите для выбора файла на устройстве (до 15 МБ)
          </span>
        </div>

        <span className="text-[11px] font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-2 py-0.5 rounded border border-[#00F5D4]/20">
          Автоматический парсинг стека и опыта через PyMuPDF
        </span>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-[6px] bg-rose-950/40 border border-rose-500/30 text-[#FB7185] text-xs font-mono">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
