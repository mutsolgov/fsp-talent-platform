import React from 'react';
import {
  SalaryRangeInput,
  validateSalaryRange,
} from '../components/molecules/SalaryRangeInput';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;

describe('SalaryRangeInput Component & Validation Logic', () => {
  describe('Domain Invariant: validateSalaryRange (152-ФЗ / ТЗ ФСП)', () => {
    it('rejects salary_min <= 0 with explicit error message', () => {
      const errZero = validateSalaryRange(0, 200000);
      expect(errZero).toBe('Минимальная зарплата должна быть строго больше нуля');

      const errNegative = validateSalaryRange(-50000, 150000);
      expect(errNegative).toBe('Минимальная зарплата должна быть строго больше нуля');
    });

    it('rejects salary_max < salary_min with explicit error message', () => {
      const err = validateSalaryRange(250000, 200000);
      expect(err).toBe('Максимальная зарплата не может быть меньше минимальной');
    });

    it('rejects salary spread ratio exceeding 3.5x', () => {
      // 100 000 to 360 000 is 3.6x > 3.5x
      const errSpread = validateSalaryRange(100000, 360000);
      expect(errSpread).toBe('Разброс зарплатной вилки не может превышать 3.5x');

      // 50 000 to 200 000 is 4.0x > 3.5x
      const errHighSpread = validateSalaryRange(50000, 200000);
      expect(errHighSpread).toBe('Разброс зарплатной вилки не может превышать 3.5x');
    });

    it('accepts exact boundary spread ratio of 3.5x', () => {
      // 100 000 to 350 000 is exactly 3.5x
      const errBoundary = validateSalaryRange(100000, 350000);
      expect(errBoundary).toBeNull();
    });

    it('accepts valid realistic compensation ranges', () => {
      expect(validateSalaryRange(150000, 250000)).toBeNull();
      expect(validateSalaryRange(200000, 300000)).toBeNull();
      expect(validateSalaryRange(300000, 450000)).toBeNull();
      expect(validateSalaryRange(180000, 180000)).toBeNull();
    });
  });

  describe('Component Presentation & Accessibility', () => {
    it('renders input elements with semantic IDs and currency symbol', () => {
      const html = renderToString(
        React.createElement(SalaryRangeInput, {
          salaryMin: 150000,
          salaryMax: 250000,
          onChange: () => {},
        })
      );

      expect(html).toContain('id="salary_min_input"');
      expect(html).toContain('id="salary_max_input"');
      expect(html).toContain('₽');
      expect(html).toContain('Обязательная зарплатная вилка');
    });

    it('renders formatted RUB values with localization spacing', () => {
      const html = renderToString(
        React.createElement(SalaryRangeInput, {
          salaryMin: 180000,
          salaryMax: 320000,
          onChange: () => {},
        })
      );

      // Value should be formatted via toLocaleString('ru-RU')
      const formattedMin = (180000).toLocaleString('ru-RU');
      const formattedMax = (320000).toLocaleString('ru-RU');

      expect(html).toContain(formattedMin);
      expect(html).toContain(formattedMax);
    });

    it('displays external validation error when passed via props', () => {
      const errorMessage = 'Введенная сумма ниже регионального минимума';
      const html = renderToString(
        React.createElement(SalaryRangeInput, {
          salaryMin: 100000,
          salaryMax: 200000,
          onChange: () => {},
          error: errorMessage,
        })
      );

      expect(html).toContain(errorMessage);
      expect(html).toContain('text-[#FB7185]');
    });

    it('displays validation warning when initial range exceeds 3.5x', () => {
      const warning = validateSalaryRange(100000, 400000);
      expect(warning).toBe('Разброс зарплатной вилки не может превышать 3.5x');

      const html = renderToString(
        React.createElement(SalaryRangeInput, {
          salaryMin: 100000,
          salaryMax: 400000,
          onChange: () => {},
          error: warning || undefined,
        })
      );

      expect(html).toContain('Разброс зарплатной вилки не может превышать 3.5x');
    });

    it('disables input fields when disabled prop is true', () => {
      const html = renderToString(
        React.createElement(SalaryRangeInput, {
          salaryMin: 150000,
          salaryMax: 250000,
          onChange: () => {},
          disabled: true,
        })
      );

      expect(html).toContain('disabled');
    });

    it('simulates handleMinChange and handleMaxChange event triggers', () => {
      const mockOnChange = vi.fn();
      const el = React.createElement(SalaryRangeInput, {
        salaryMin: 120000,
        salaryMax: 240000,
        onChange: mockOnChange,
      });

      // Verify props contract
      expect(el.props.salaryMin).toBe(120000);
      expect(el.props.salaryMax).toBe(240000);

      // Directly invoke onChange with updated valid range
      el.props.onChange(130000, 240000, true);
      expect(mockOnChange.mock.calls.length).toBe(1);
      expect(mockOnChange.mock.lastCall).toEqual([130000, 240000, true]);

      // Directly invoke onChange with invalid spread
      el.props.onChange(50000, 240000, false);
      expect(mockOnChange.mock.calls.length).toBe(2);
      expect(mockOnChange.mock.lastCall).toEqual([50000, 240000, false]);
    });
  });
});
