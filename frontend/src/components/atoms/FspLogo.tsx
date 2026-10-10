import React from 'react';

export type FspLogoVariant =
  | 'logo_01'
  | 'logo_02'
  | 'logo_03'
  | 'logo_04'
  | 'logo_01w'
  | 'logo_02w'
  | 'logo_03w'
  | 'logo_04w'
  | 'logo_05w'
  | 'logo_big'
  | 'logo_head'
  | 'logo_foot'
  | 'logo_mark'
  | 'horizontal'
  | 'mark'
  | 'compact'
  | 'full'
  | 'wide';

export interface FspLogoProps {
  variant?: FspLogoVariant;
  theme?: 'dark' | 'light';
  className?: string;
  alt?: string;
  width?: number | string;
  height?: number | string;
  onClick?: () => void;
}

const resolveLogoSrc = (variant: FspLogoVariant, theme: 'dark' | 'light'): string => {
  // If exact logo filename specified
  const exactLogos = [
    'logo_01',
    'logo_02',
    'logo_03',
    'logo_04',
    'logo_01w',
    'logo_02w',
    'logo_03w',
    'logo_04w',
    'logo_05w',
    'logo_big',
    'logo_head',
    'logo_foot',
    'logo_mark',
  ];
  if (exactLogos.includes(variant)) {
    return `/brand/${variant}.svg`;
  }

  // Semantic role-based resolution based on theme
  if (theme === 'light') {
    switch (variant) {
      case 'wide':
        return '/brand/logo_01w.svg';
      case 'horizontal':
        return '/brand/logo_02w.svg';
      case 'mark':
        return '/brand/logo_03w.svg';
      case 'compact':
        return '/brand/logo_04w.svg';
      case 'full':
        return '/brand/logo_05w.svg';
      default:
        return '/brand/logo_01w.svg';
    }
  }

  // Dark theme default
  switch (variant) {
    case 'wide':
      return '/brand/logo_big.svg';
    case 'horizontal':
      return '/brand/logo_01.svg';
    case 'mark':
      return '/brand/logo_02.svg';
    case 'compact':
      return '/brand/logo_03.svg';
    case 'full':
      return '/brand/logo_04.svg';
    default:
      return '/brand/logo_01.svg';
  }
};

export const FspLogo: React.FC<FspLogoProps> = ({
  variant = 'horizontal',
  theme = 'dark',
  className = '',
  alt = 'ФСП — Федерация спортивного программирования',
  width,
  height,
  onClick,
}) => {
  const src = resolveLogoSrc(variant, theme);

  return (
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      onClick={onClick}
      className={`inline-block select-none object-contain ${className}`}
      loading="eager"
    />
  );
};
