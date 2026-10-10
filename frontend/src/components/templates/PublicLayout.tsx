import React, { ReactNode } from 'react';
import { RoleSwitcherBar } from '../molecules/RoleSwitcherBar';
import { ArrowRight, ShieldCheck } from '../icons';

export interface PublicLayoutProps {
  children: ReactNode;
  className?: string;
}

export const PublicLayout: React.FC<PublicLayoutProps> = ({ children, className = '' }) => {
  return (
    <div className={`min-h-screen bg-[#1B1C21] text-[#EDEDED] flex flex-col justify-between ${className}`}>
      {/* Floating Header per docs/05 §1.1 */}
      <header className="sticky top-4 z-40 max-w-[1340px] w-[95%] mx-auto mt-4 px-6 py-3.5 rounded-[12px] bg-white/95 text-[#1B1C21] backdrop-blur-md border border-[#E2E4E8] shadow-[0_8px_30px_rgba(0,0,0,0.12)] flex items-center justify-between transition-all">
        <a href="/" className="flex items-center gap-2">
          {/* Light Mode Master Logo (logo_01w.svg) with #C8C9CA top node and #1B1C21 text */}
          <img
            src="/brand/logo_01w.svg"
            alt="ФСП Россия"
            className="h-8 w-auto"
          />
        </a>

        <nav className="hidden md:flex items-center gap-6 font-mono text-xs font-medium text-[#1B1C21]">
          <a href="/vacancies" className="hover:text-[#402FFF] transition-colors">
            Вакансии
          </a>
          <a href="/categories" className="hover:text-[#402FFF] transition-colors">
            24 Категории
          </a>
          <a href="/demo/dashboard" className="text-[#402FFF] font-bold flex items-center gap-1 hover:underline">
            <ShieldCheck size={14} />
            Демо Жюри
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <a
            href="/login"
            className="hidden sm:inline font-mono text-xs font-semibold text-[#1B1C21] hover:text-[#402FFF] px-2 py-1"
          >
            Войти
          </a>
          <a
            href="/register"
            className="inline-flex items-center gap-1 px-4 py-2 rounded-[6px] bg-[#402FFF] text-white font-mono text-xs font-bold hover:bg-[#3525E0] transition-colors shadow-[0_0_12px_rgba(64,47,255,0.4)]"
          >
            <span>Регистрация</span>
            <ArrowRight size={14} />
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1340px] w-full mx-auto px-4 sm:px-8 py-8 flex-1">
        {children}
      </main>

      {/* Footer per doc 05 §1.1 with logo_foot.svg */}
      <footer className="border-t border-[#2D2E37] bg-[#202129] py-10 mt-12 text-xs font-mono text-[#9B9C9E]">
        <div className="max-w-[1340px] mx-auto px-4 sm:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex flex-col items-center md:items-start gap-2">
            <img src="/brand/logo_foot.svg" alt="ФСП" className="h-7 w-auto opacity-90" />
            <span className="text-[11px] text-[#5F5F66]">
              Официальная цифровая платформа Федерации спортивного программирования России
            </span>
          </div>

          <div className="flex flex-wrap justify-center items-center gap-6 text-[11px]">
            <a href="/vacancies" className="hover:text-white">Вакансии</a>
            <a href="/categories" className="hover:text-white">Категории</a>
            <a href="/candidate/onboarding" className="hover:text-white">Соискателям</a>
            <a href="/employer/candidate-bank" className="hover:text-white">Работодателям</a>
            <a href="/demo/dashboard" className="text-[#00F5D4] hover:underline">Режим Жюри</a>
          </div>

          <div className="text-[11px] text-[#5F5F66] text-center md:text-right">
            152-ФЗ РФ Согласие и защита данных • 2026
          </div>
        </div>
      </footer>
    </div>
  );
};
