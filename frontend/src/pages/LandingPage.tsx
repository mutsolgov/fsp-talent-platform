import React from 'react';
import { PublicLayout } from '../components/templates/PublicLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { ArrowRight, ShieldCheck, Zap, Trophy, Cpu } from '../components/icons';

export const LandingPage: React.FC = () => {
  const disciplines = [
    { id: 'algoritm', name: 'Алгоритмическое программирование', icon: '/brand/icon_algoritm.svg' },
    { id: 'product', name: 'Продуктовое (хакатоны)', icon: '/brand/icon_product.svg' },
    { id: 'security', name: 'Информационная безопасность (CTF)', icon: '/brand/icon_security.svg' },
    { id: 'robot', name: 'Программирование робототехники', icon: '/brand/icon_robot.svg' },
    { id: 'drone', name: 'Алгоритмы БАС (Дроны)', icon: '/brand/icon_drone.svg' },
  ];

  const specializations = ['Backend', 'Frontend', 'ML / Data', 'DevOps / SRE', 'QA Engineering', 'InfoSec'];
  const grades = ['Junior', 'Middle', 'Senior', 'Lead'];

  return (
    <PublicLayout>
      <div className="flex flex-col gap-16">
        {/* Hero Section with Master Logo */}
        <section className="relative flex flex-col items-center text-center py-12 px-4 gap-6 overflow-hidden">
          {/* Subtle Ambient Glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-[#402FFF]/20 rounded-full blur-[100px] pointer-events-none" />

          <Badge variant="fsp" size="md">
            СПЕЦТРЕК ФСП • ЛЦТ 2026
          </Badge>

          <img
            src="/brand/logo_big.svg"
            alt="Федерация спортивного программирования"
            className="w-full max-w-2xl h-auto drop-shadow-[0_0_24px_rgba(64,47,255,0.3)]"
          />

          <h1 className="font-mono text-3xl sm:text-5xl font-bold text-white max-w-3xl leading-tight">
            Цифровая платформа ИТ-талантов с верифицированным профилем достижений
          </h1>

          <p className="font-sans text-sm sm:text-base text-[#C8C9CA] max-w-2xl leading-relaxed">
            Объективная категоризация талантов без самописных резюме. Психометрическая оценка{' '}
            <strong className="text-[#00F5D4]">KITE IRT 3PL</strong>, официальный реестр ФСП России и реверс-рекрутинг с обязательными рублевыми вилками.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4 mt-2">
            <a href="/candidate/onboarding">
              <Button variant="fsp_mint" size="lg">
                <span>Пройти верификацию KITE</span>
                <ArrowRight size={16} />
              </Button>
            </a>
            <a href="/employer/candidate-bank">
              <Button variant="secondary" size="lg">
                <span>Банк проверенных талантов</span>
              </Button>
            </a>
          </div>
        </section>

        {/* 5 FSP Disciplines */}
        <section className="flex flex-col gap-6">
          <div className="flex flex-col text-center">
            <h2 className="font-mono text-xl sm:text-2xl font-bold text-white">
              5 спортивных дисциплин ФСП России
            </h2>
            <span className="text-xs font-sans text-[#9B9C9E] mt-1">
              Официальные разряды ЕВСК, подтвержденные протоколами чемпионатов и кубков
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {disciplines.map((d) => (
              <div
                key={d.id}
                className="p-5 rounded-[12px] bg-[#202129] border border-[#3D3E42] hover:border-[#402FFF] transition-all flex flex-col items-center text-center gap-3 shadow-[0_4px_16px_rgba(0,0,0,0.4)] group"
              >
                <div className="w-14 h-14 rounded-full bg-[#1B1C21] border border-[#2D2E37] flex items-center justify-center p-2 group-hover:scale-105 transition-transform shadow-[0_0_16px_rgba(64,47,255,0.2)]">
                  <img src={d.icon} alt={d.name} className="w-9 h-9 object-contain" />
                </div>
                <span className="font-mono text-xs font-semibold text-[#EDEDED] leading-snug">
                  {d.name}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* 24 Categories Matrix */}
        <section className="flex flex-col gap-6 p-6 sm:p-8 rounded-[16px] bg-[#202129] border border-[#3D3E42]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#2D2E37] pb-4">
            <div className="flex flex-col">
              <h2 className="font-mono text-xl font-bold text-white flex items-center gap-2">
                <ShieldCheck size={20} className="text-[#00F5D4]" />
                Матрица 24 категорий квалификации
              </h2>
              <span className="text-xs font-sans text-[#9B9C9E] mt-0.5">
                Категория = Специализация + Подтвержденный грейд (LHH модель реверс-рекрутинга)
              </span>
            </div>
            <a href="/categories" className="text-xs font-mono text-[#402FFF] hover:underline flex items-center gap-1">
              <span>Смотреть все 24</span>
              <ArrowRight size={12} />
            </a>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {specializations.map((spec) => (
              <div key={spec} className="flex flex-col gap-2 p-3.5 rounded-[8px] bg-[#1B1C21] border border-[#2D2E37]">
                <span className="font-mono text-xs font-bold text-white">{spec}</span>
                <div className="flex flex-col gap-1 text-[11px] font-mono text-[#9B9C9E]">
                  {grades.map((g) => (
                    <span key={g} className="hover:text-[#00F5D4] cursor-pointer">
                      • {g}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 152-FZ & Zero Non-FSP Penalty Features */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-[12px] bg-[#202129] border border-[#3D3E42] flex flex-col gap-3">
            <div className="w-10 h-10 rounded-[8px] bg-[#00F5D4]/15 border border-[#00F5D4]/30 flex items-center justify-center text-[#00F5D4]">
              <Cpu size={20} />
            </div>
            <h3 className="font-mono text-base font-bold text-white">Паритет без стигматизации</h3>
            <p className="text-xs font-sans text-[#9B9C9E] leading-relaxed">
              Инженеры без истории в реестре ФСП не штрафуются: алгоритм автоматически перераспределяет веса (0.52 / 0.30 / 0.18), обеспечивая равный доступ к топу выдачи.
            </p>
          </div>

          <div className="p-6 rounded-[12px] bg-[#202129] border border-[#3D3E42] flex flex-col gap-3">
            <div className="w-10 h-10 rounded-[8px] bg-[#402FFF]/15 border border-[#402FFF]/30 flex items-center justify-center text-[#402FFF]">
              <ShieldCheck size={20} />
            </div>
            <h3 className="font-mono text-base font-bold text-white">152-ФЗ Приватность контактов</h3>
            <p className="text-xs font-sans text-[#9B9C9E] leading-relaxed">
              Контакты соискателя физически маскируются на уровне API до тех пор, пока соискатель лично не примет прямое предложение работодателя с указанной зарплатной вилкой.
            </p>
          </div>

          <div className="p-6 rounded-[12px] bg-[#202129] border border-[#3D3E42] flex flex-col gap-3">
            <div className="w-10 h-10 rounded-[8px] bg-[#EC1D35]/15 border border-[#EC1D35]/30 flex items-center justify-center text-[#EC1D35]">
              <Zap size={20} />
            </div>
            <h3 className="font-mono text-base font-bold text-white">Обязательные вилки в рублях</h3>
            <p className="text-xs font-sans text-[#9B9C9E] leading-relaxed">
              Каждое предложение и вакансия обязаны содержать прозрачную рублевую вилку (от–до) с ограничением разброса не более 3.5x.
            </p>
          </div>
        </section>
      </div>
    </PublicLayout>
  );
};

export default LandingPage;
