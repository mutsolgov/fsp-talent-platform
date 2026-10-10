import React, { useRef } from 'react';

export interface CodeEditorMiniProps {
  code: string;
  language: string;
  onChange: (code: string) => void;
  readOnly?: boolean;
  className?: string;
}

export const CodeEditorMini: React.FC<CodeEditorMiniProps> = ({
  code,
  language,
  onChange,
  readOnly = false,
  className = '',
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lines = (code || '').split('\n');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.currentTarget;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const newCode = code.substring(0, start) + '    ' + code.substring(end);
      onChange(newCode);
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 4;
        }
      }, 0);
    }
  };

  return (
    <div
      className={`relative rounded-[8px] bg-[#16171D] border border-[#3D3E42] overflow-hidden flex flex-col font-mono text-xs ${className}`}
    >
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1B1C21] border-b border-[#2D2E37] text-[11px] text-[#9B9C9E]">
        <span className="uppercase font-semibold tracking-wider text-[#00F5D4]">{language}</span>
        <span>{lines.length} строк • JetBrains Mono</span>
      </div>

      <div className="relative flex flex-1 overflow-auto max-h-[450px]">
        {/* Line numbers gutter */}
        <div className="py-3 pl-3 pr-2 select-none text-right text-[#5F5F66] bg-[#16171D] border-r border-[#2D2E37]">
          {lines.map((_, idx) => (
            <div key={idx} className="leading-5 h-5 text-[11px]">
              {idx + 1}
            </div>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={code}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          readOnly={readOnly}
          spellCheck={false}
          className="w-full h-full p-3 bg-transparent text-[#EDEDED] font-mono leading-5 outline-none resize-none whitespace-pre tab-4"
          placeholder="// Напишите решение здесь..."
        />
      </div>
    </div>
  );
};
