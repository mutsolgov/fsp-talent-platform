import React from 'react';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: string;
  label?: string;
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  color = 'currentColor',
  label = 'Загрузка данных',
  className = '',
}) => {
  const sizePx = size === 'sm' ? 16 : size === 'md' ? 24 : 36;

  return (
    <div
      role="progressbar"
      aria-label={label}
      className={`inline-flex items-center justify-center animate-spin ${className}`}
      style={{ width: sizePx, height: sizePx }}
    >
      <svg
        className="w-full h-full"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke={color}
          strokeWidth="3"
        />
        <path
          className="opacity-90"
          fill={color}
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </div>
  );
};
