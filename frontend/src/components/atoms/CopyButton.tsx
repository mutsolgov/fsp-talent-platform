import React, { useState } from 'react';
import { Copy, Check } from '../icons';

export interface CopyButtonProps {
  textToCopy: string;
  label?: string;
  className?: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({
  textToCopy,
  label,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(textToCopy);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = textToCopy;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={label || 'Скопировать'}
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-[4px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#C8C9CA] hover:text-white border border-[#3D3E42] text-xs font-mono transition-colors cursor-pointer ${className}`}
    >
      {copied ? (
        <>
          <Check size={14} className="text-[#00F5D4]" />
          <span className="text-[#00F5D4]">Скопировано</span>
        </>
      ) : (
        <>
          <Copy size={14} />
          {label && <span>{label}</span>}
        </>
      )}
      <span aria-live="polite" className="sr-only">
        {copied ? 'Скопировано в буфер обмена' : ''}
      </span>
    </button>
  );
};
