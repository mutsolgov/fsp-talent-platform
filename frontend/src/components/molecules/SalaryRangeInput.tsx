import React, { useState, useEffect } from 'react';
import { RubCurrencySymbol } from '../atoms/RubCurrencySymbol';

export interface SalaryRangeInputProps {
  salaryMin: number;
  salaryMax: number;
  onChange: (min: number, max: number, isValid: boolean) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
}

export function validateSalaryRange(min: number, max: number): string | null {
  if (min <= 0) {
    return 'Минимальная зарплата должна быть строго больше нуля';
  }
  if (max < min) {
    return 'Максимальная зарплата не может быть меньше минимальной';
  }
  if (min > 0 && max / min > 3.5) {
    return 'Разброс зарплатной вилки не может превышать 3.5x';
  }
  return null;
}

export const SalaryRangeInput: React.FC<SalaryRangeInputProps> = ({
  salaryMin,
  salaryMax,
  onChange,
  error: externalError,
  disabled = false,
  className = '',
}) => {
  const [minVal, setMinVal] = useState<number>(salaryMin);
  const [maxVal, setMaxVal] = useState<number>(salaryMax);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setMinVal(salaryMin);
    setMaxVal(salaryMax);
    const err = validateSalaryRange(salaryMin, salaryMax);
    setLocalError(err);
  }, [salaryMin, salaryMax]);

  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value) || 0;
    setMinVal(val);
    const err = validateSalaryRange(val, maxVal);
    setLocalError(err);
    onChange(val, maxVal, err === null);
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value) || 0;
    setMaxVal(val);
    const err = validateSalaryRange(minVal, val);
    setLocalError(err);
    onChange(minVal, val, err === null);
  };

  const displayError = externalError || localError;

  return (
    <div className={`flex flex-col gap-2 w-full ${className}`}>
      <div className="flex justify-between items-center text-xs font-mono text-[#C8C9CA]">
        <span>Обязательная зарплатная вилка (152-ФЗ / ТЗ ФСП)</span>
        <span className="text-[#00F5D4] flex items-center gap-1 font-semibold">
          {minVal.toLocaleString('ru-RU')} — {maxVal.toLocaleString('ru-RU')}{' '}
          <RubCurrencySymbol />
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="relative">
          <label htmlFor="salary_min_input" className="sr-only">
            Минимальная зарплата (от)
          </label>
          <span className="absolute left-3 top-2.5 text-xs font-mono text-[#9B9C9E]">от</span>
          <input
            id="salary_min_input"
            type="number"
            value={minVal || ''}
            onChange={handleMinChange}
            disabled={disabled}
            placeholder="150000"
            className="w-full pl-9 pr-8 py-2.5 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-sm border border-[#3D3E42] focus:border-[#402FFF] outline-none"
          />
          <span className="absolute right-3 top-2.5 text-sm font-mono text-[#9B9C9E]">
            <RubCurrencySymbol />
          </span>
        </div>

        <div className="relative">
          <label htmlFor="salary_max_input" className="sr-only">
            Максимальная зарплата (до)
          </label>
          <span className="absolute left-3 top-2.5 text-xs font-mono text-[#9B9C9E]">до</span>
          <input
            id="salary_max_input"
            type="number"
            value={maxVal || ''}
            onChange={handleMaxChange}
            disabled={disabled}
            placeholder="250000"
            className="w-full pl-9 pr-8 py-2.5 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-sm border border-[#3D3E42] focus:border-[#402FFF] outline-none"
          />
          <span className="absolute right-3 top-2.5 text-sm font-mono text-[#9B9C9E]">
            <RubCurrencySymbol />
          </span>
        </div>
      </div>

      {displayError && (
        <span className="text-xs font-mono text-[#FB7185] mt-0.5 tracking-tight">
          {displayError}
        </span>
      )}
    </div>
  );
};
