import React from 'react';

export interface RubCurrencySymbolProps {
  className?: string;
}

export const RubCurrencySymbol: React.FC<RubCurrencySymbolProps> = ({ className = '' }) => {
  return (
    <span
      aria-label="российских рублей"
      className={`font-mono font-medium inline-block select-none ${className}`}
    >
      ₽
    </span>
  );
};
