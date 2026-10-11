import React from 'react';
import {
  CandidateProfilePage,
  mapCandidateProfileData,
} from '../pages/CandidateProfilePage';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;

describe('CandidateProfilePage (Production Mode — Zero Synthetic Defaults)', () => {
  describe('mapCandidateProfileData Function', () => {
    it('correctly maps uncalibrated candidate data without synthetic defaults', () => {
      const rawData = {
        id: 7,
        first_name: 'Федор',
        last_name: 'Федотов',
        grade: null,
        specialization: null,
        category_title: 'Профиль не откалиброван',
        skills: [],
        fsp_id: null,
        fsp_verified: false,
        theta: 0.0,
        kite_score_scaled: 0.0,
        expected_salary: null,
        city: null,
        work_format: null,
      };

      const mapped = mapCandidateProfileData(rawData);
      expect(mapped.verifiedGrade).toBe('Ожидает тестирования');
      expect(mapped.specialization).toBe('Специализация не выбрана');
      expect(mapped.sportRank).toBe('Без разряда');
      expect(mapped.isFspVerified).toBe(false);
      expect(mapped.skills).toEqual([]);
      expect(mapped.theta).toBe(0.0);
    });

    it('replaces string markers "Не определен" and "Не выбрана" with user-friendly fallbacks', () => {
      const rawData = {
        id: 8,
        first_name: 'Иван',
        last_name: 'Иванов',
        grade: 'Не определен',
        specialization: 'Не выбрана',
        fsp_id: null,
        skills: [],
        theta: 0.0,
      };

      const mapped = mapCandidateProfileData(rawData);
      expect(mapped.verifiedGrade).toBe('Ожидает тестирования');
      expect(mapped.specialization).toBe('Специализация не выбрана');
    });

    it('falls back to 1-й разряд when candidate has fsp_id but no rank recorded', () => {
      const rawData = {
        id: 10,
        first_name: 'Алексей',
        last_name: 'Кузнецов',
        fsp_id: 'FSP-77-01042',
        fsp_verified: true,
        sport_rank: null,
        fsp_badge: null,
      };

      const mapped = mapCandidateProfileData(rawData);
      expect(mapped.sportRank).toBe('1-й разряд');
      expect(mapped.isFspVerified).toBe(true);
    });
  });

  describe('Component Rendering for Uncalibrated Candidate', () => {
    it('renders honest status badges, empty skills banner, and calibration CTA', () => {
      const uncalibratedData = {
        id: 15,
        first_name: 'Тест',
        last_name: 'Соискатель',
        grade: 'Не определен',
        specialization: 'Не выбрана',
        fsp_id: null,
        fsp_verified: false,
        sport_rank: null,
        skills: [],
        theta: 0.0,
        freshness_score: 50.0,
        bio: '',
        is_published: true,
      };

      const html = renderToString(
        React.createElement(CandidateProfilePage, { initialData: uncalibratedData })
      );

      // 1. Честные статусы квалификации и разряда
      expect(html).toContain('Ожидает тестирования');
      expect(html).toContain('Специализация не выбрана');
      expect(html).toContain('Без разряда');

      // 2. Информационный баннер онбординга при пустом стеке
      expect(html).toContain(
        'Технологический стек пока не заполнен. Заполните анкету онбординга или загрузите резюме, чтобы добавить подтвержденные навыки'
      );
      expect(html).toContain('href="/candidate/onboarding"');

      // 3. Статус непройденного тестирования KITE и кнопка калибровки
      expect(html).toContain('Тестирование не пройдено');
      expect(html).toContain('Пройти калибровку');
      expect(html).toContain('href="/candidate/assessment"');
    });

    it('renders confirmed attributes for fully calibrated FSP candidate', () => {
      const calibratedData = {
        id: 42,
        first_name: 'Алексей',
        last_name: 'Кузнецов',
        specialization: 'Backend',
        grade: 'Senior',
        fsp_id: 'FSP-77-01042',
        fsp_verified: true,
        sport_rank: 'КМС',
        skills: ['Python', 'FastAPI', 'PostgreSQL'],
        theta: 89.5,
        freshness_score: 85.0,
        bio: 'Ведущий бэкенд разработчик',
        is_published: true,
      };

      const html = renderToString(
        React.createElement(CandidateProfilePage, { initialData: calibratedData })
      );

      expect(html).toContain('Backend • Senior');
      expect(html).toContain('КМС');
      expect(html).toContain('Python');
      expect(html).toContain('FastAPI');
      expect(html).toContain('PostgreSQL');
      expect(html).toContain('θ = 89.5');
      expect(html).not.toContain('Технологический стек пока не заполнен');
      expect(html).not.toContain('Тестирование не пройдено');
    });
  });
});
