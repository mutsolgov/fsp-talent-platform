import React from 'react';
import { SearchFilters, Specialization, Grade } from '../../types';
import { Search, Filter, RefreshCw } from '../icons';

export interface SearchFilterBarProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
  onReset: () => void;
  className?: string;
}

export const SearchFilterBar: React.FC<SearchFilterBarProps> = ({
  filters,
  onChange,
  onReset,
  className = '',
}) => {
  const specializations: Array<{ value: Specialization | 'all'; label: string }> = [
    { value: 'all', label: 'Все специализации' },
    { value: 'backend', label: 'Backend' },
    { value: 'frontend', label: 'Frontend' },
    { value: 'ml_data', label: 'ML / Data' },
    { value: 'devops', label: 'DevOps / SRE' },
    { value: 'qa', label: 'QA / Testing' },
    { value: 'infosec', label: 'InfoSec / CTF' },
  ];

  const grades: Array<{ value: Grade | 'all'; label: string }> = [
    { value: 'all', label: 'Все грейды' },
    { value: 'junior', label: 'Junior' },
    { value: 'middle', label: 'Middle' },
    { value: 'senior', label: 'Senior' },
    { value: 'lead', label: 'Lead' },
  ];

  return (
    <div
      role="search"
      className={`relative p-4 rounded-[12px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_20px_rgba(0,0,0,0.4)] overflow-hidden ${className}`}
    >
      {/* Decorative dot matrix map underlay (map1.png) */}
      <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-[url('/brand/map1.png')] bg-contain bg-no-repeat bg-right opacity-15 pointer-events-none" />

      <div className="relative z-10 flex flex-col gap-3.5">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3.5 top-3 text-[#9B9C9E]" />
            <input
              type="text"
              value={filters.searchQuery || ''}
              onChange={(e) => onChange({ ...filters, searchQuery: e.target.value })}
              placeholder="Поиск по навыкам, коду кандидата или стеку..."
              className="w-full pl-10 pr-4 py-2.5 rounded-[6px] bg-[#1B1C21] text-[#EDEDED] font-mono text-sm border border-[#3D3E42] focus:border-[#402FFF] outline-none"
            />
          </div>

          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#C8C9CA] text-xs font-mono transition-colors cursor-pointer border border-[#3D3E42]"
          >
            <RefreshCw size={14} />
            Сброс
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {/* Specialization Select */}
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-mono text-[#9B9C9E]">Специализация</span>
            <select
              value={filters.specialization || 'all'}
              onChange={(e) =>
                onChange({ ...filters, specialization: e.target.value as Specialization | 'all' })
              }
              className="w-full px-3 py-2 rounded-[6px] bg-[#1B1C21] text-[#EDEDED] font-mono text-xs border border-[#3D3E42] focus:border-[#402FFF] outline-none"
            >
              {specializations.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* Grade Select */}
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-mono text-[#9B9C9E]">Подтвержденный грейд</span>
            <select
              value={filters.grade || 'all'}
              onChange={(e) =>
                onChange({ ...filters, grade: e.target.value as Grade | 'all' })
              }
              className="w-full px-3 py-2 rounded-[6px] bg-[#1B1C21] text-[#EDEDED] font-mono text-xs border border-[#3D3E42] focus:border-[#402FFF] outline-none"
            >
              {grades.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </div>

          {/* FSP Toggle */}
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-mono text-[#9B9C9E]">Реестр ФСП</span>
            <label className="flex items-center gap-2 h-9 px-3 rounded-[6px] bg-[#1B1C21] border border-[#3D3E42] cursor-pointer">
              <input
                type="checkbox"
                checked={Boolean(filters.onlyFsp)}
                onChange={(e) => onChange({ ...filters, onlyFsp: e.target.checked })}
                className="accent-[#402FFF]"
              />
              <span className="text-xs font-mono text-[#EDEDED]">Только участники ФСП</span>
            </label>
          </div>

          {/* Region Filter */}
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-mono text-[#9B9C9E]">Регион РФ (89 субъектов)</span>
            <input
              type="text"
              value={filters.region || ''}
              onChange={(e) => onChange({ ...filters, region: e.target.value })}
              placeholder="Москва, СПб, Казань..."
              className="w-full px-3 py-2 rounded-[6px] bg-[#1B1C21] text-[#EDEDED] font-mono text-xs border border-[#3D3E42] focus:border-[#402FFF] outline-none"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
