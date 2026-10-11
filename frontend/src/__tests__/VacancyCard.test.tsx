import React from 'react';
import { VacancyCard } from '../components/organisms/VacancyCard';
import { VacancySummary } from '../types';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;

describe('VacancyCard Organism & Applied Status Layout', () => {
  const mockVacancy: VacancySummary = {
    id: 10,
    title: 'Senior Python Engineer',
    companyName: 'ФСП Технологии',
    inn: '7701234567',
    specialization: 'backend',
    grade: 'senior',
    salaryMinRub: 250000,
    salaryMaxRub: 350000,
    location: 'Москва (Гибрид)',
    isTrustEmployer: true,
    tags: ['Python', 'FastAPI', 'PostgreSQL'],
    createdAt: '2026-10-01',
  };

  it('renders standard apply button and grade badge when isApplied is false', () => {
    const html = renderToString(
      React.createElement(VacancyCard, {
        vacancy: mockVacancy,
        onApplyClick: () => {},
        isApplied: false,
      })
    );

    expect(html).toContain('SENIOR');
    expect(html).toContain('Откликнуться');
    expect(html).not.toContain('Отклик отправлен');
  });

  it('renders isApplied badge alongside grade badge in flex container without overlap', () => {
    const html = renderToString(
      React.createElement(VacancyCard, {
        vacancy: mockVacancy,
        onApplyClick: () => {},
        isApplied: true,
      })
    );

    expect(html).toContain('SENIOR');
    expect(html).toContain('Отклик отправлен');
    // Apply button is replaced by status indicator
    expect(html).not.toContain('Откликнуться');
    // Elements are positioned cleanly in flex layout, not absolute top-4 right-4
    expect(html).not.toContain('absolute top-4 right-4');
  });
});
