import React from 'react';
import { RadarMatchChart } from '../components/molecules/RadarMatchChart';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;

describe('RadarMatchChart 4-Axis SVG Radar & Accessibility Table', () => {
  describe('FSP Profile Radar (Brandbook Violet #402FFF)', () => {
    const props = {
      testMatch: 85,
      stackMatch: 92,
      fspMatch: 80,
      freshnessMatch: 75,
      isFspProfile: true,
      size: 240,
    };

    it('renders SVG element with requested dimensions and concentric grid circles', () => {
      const html = renderToString(React.createElement(RadarMatchChart, props));

      expect(html).toContain('<svg');
      expect(html).toContain('width="240"');
      expect(html).toContain('height="240"');
      // 4 concentric level circles
      expect(html).toContain('stroke-dasharray="3 3"');
    });

    it('renders polygon and vertex circles in official FSP violet theme (#402FFF)', () => {
      const html = renderToString(React.createElement(RadarMatchChart, props));

      expect(html).toContain('<polygon');
      expect(html).toContain('stroke="#402FFF"');
      expect(html).toContain('fill="rgba(64, 47, 255, 0.25)"');
    });

    it('renders official FSP discipline label for the 3rd axis', () => {
      const html = renderToString(React.createElement(RadarMatchChart, props));

      expect(html).toContain('Тест KITE');
      expect(html).toContain('Стек');
      expect(html).toContain('ФСП Разряд');
      expect(html).toContain('Свежесть');

      // Rounded percentage values
      expect(html).toContain('85');
      expect(html).toContain('92');
      expect(html).toContain('80');
      expect(html).toContain('75');
    });
  });

  describe('Non-FSP General Track Radar (Mint Accent #00F5D4)', () => {
    const nonFspProps = {
      testMatch: 88,
      stackMatch: 90,
      fspMatch: 0,
      freshnessMatch: 82,
      isFspProfile: false,
      size: 220,
    };

    it('renders redistributed weight label "Практика (0.52)" without penalty', () => {
      const html = renderToString(React.createElement(RadarMatchChart, nonFspProps));

      expect(html).toContain('Практика (0.52)');
      expect(html).not.toContain('ФСП Разряд');
    });

    it('renders polygon in official mint accent theme (#00F5D4)', () => {
      const html = renderToString(React.createElement(RadarMatchChart, nonFspProps));

      expect(html).toContain('stroke="#00F5D4"');
      expect(html).toContain('fill="rgba(0, 245, 212, 0.25)"');
    });
  });

  describe('WCAG AAA Screen Reader Accessibility Table', () => {
    it('renders hidden accessible table with caption, headers and exact factor rows', () => {
      const props = {
        testMatch: 95,
        stackMatch: 88,
        fspMatch: 70,
        freshnessMatch: 60,
        isFspProfile: true,
      };

      const html = renderToString(React.createElement(RadarMatchChart, props));

      expect(html).toContain('<table class="sr-only">');
      expect(html).toContain('<caption>Многофакторный радарный профиль соответствия</caption>');
      expect(html).toContain('<th>Фактор</th>');
      expect(html).toContain('<th>Значение</th>');

      // All 4 table rows populated
      expect(html).toContain('<td>Тест KITE</td>');
      expect(html).toContain('<td>Стек</td>');
      expect(html).toContain('<td>ФСП Разряд</td>');
      expect(html).toContain('<td>Свежесть</td>');
      expect(html).toContain('95<!-- -->%');
      expect(html).toContain('88<!-- -->%');
      expect(html).toContain('70<!-- -->%');
      expect(html).toContain('60<!-- -->%');
    });
  });
});
