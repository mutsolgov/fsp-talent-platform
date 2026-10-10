import React from 'react';
import { ChevronLeft, ChevronRight } from '../icons';

export interface PaginationBarProps {
  page: number;
  totalPages: number;
  totalItems: number;
  onPageChange: (p: number) => void;
  className?: string;
}

export const PaginationBar: React.FC<PaginationBarProps> = ({
  page,
  totalPages,
  totalItems,
  onPageChange,
  className = '',
}) => {
  if (totalPages <= 1) return null;

  return (
    <nav
      aria-label="Пагинация"
      className={`flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono text-[#9B9C9E] ${className}`}
    >
      <span>
        Всего записей: <strong className="text-[#EDEDED]">{totalItems}</strong> (Страница {page} из{' '}
        {totalPages})
      </span>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
          aria-label="Предыдущая страница"
          className="p-1.5 rounded-[6px] bg-[#202129] border border-[#3D3E42] text-[#EDEDED] disabled:opacity-40 disabled:cursor-not-allowed hover:border-[#402FFF] transition-colors cursor-pointer"
        >
          <ChevronLeft size={16} />
        </button>

        {Array.from({ length: totalPages }).map((_, idx) => {
          const pageNum = idx + 1;
          // Show first, last, current, and neighbours
          if (
            pageNum === 1 ||
            pageNum === totalPages ||
            Math.abs(pageNum - page) <= 1
          ) {
            const isCurrent = pageNum === page;
            return (
              <button
                key={pageNum}
                type="button"
                onClick={() => onPageChange(pageNum)}
                aria-current={isCurrent ? 'page' : undefined}
                className={`w-8 h-8 rounded-[6px] border font-mono text-xs font-semibold transition-all cursor-pointer ${
                  isCurrent
                    ? 'bg-[#402FFF] border-[#402FFF] text-white shadow-[0_0_8px_rgba(64,47,255,0.4)]'
                    : 'bg-[#202129] border-[#3D3E42] text-[#EDEDED] hover:border-[#5F5F66]'
                }`}
              >
                {pageNum}
              </button>
            );
          }
          if (pageNum === 2 && page > 3) {
            return (
              <span key="dots-start" className="px-1 text-[#5F5F66]">
                ...
              </span>
            );
          }
          if (pageNum === totalPages - 1 && page < totalPages - 2) {
            return (
              <span key="dots-end" className="px-1 text-[#5F5F66]">
                ...
              </span>
            );
          }
          return null;
        })}

        <button
          type="button"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
          aria-label="Следующая страница"
          className="p-1.5 rounded-[6px] bg-[#202129] border border-[#3D3E42] text-[#EDEDED] disabled:opacity-40 disabled:cursor-not-allowed hover:border-[#402FFF] transition-colors cursor-pointer"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </nav>
  );
};
