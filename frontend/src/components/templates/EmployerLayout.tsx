import React, { ReactNode } from 'react';
import { RoleSwitcherBar } from '../molecules/RoleSwitcherBar';
import { Briefcase, User, Pin, Mail, Building, Sliders } from '../icons';

export interface EmployerLayoutProps {
  children: ReactNode;
  currentTab?: string;
  className?: string;
}

export const EmployerLayout: React.FC<EmployerLayoutProps> = ({
  children,
  currentTab = 'candidate-bank',
  className = '',
}) => {
  const tabs = [
    { id: 'candidate-bank', label: 'Банк талантов', href: '/employer/candidate-bank', icon: <User size={16} /> },
    { id: 'needs', label: 'Потребности команд', href: '/employer/needs', icon: <Briefcase size={16} /> },
    { id: 'shortlists', label: 'Шортлисты', href: '/employer/shortlists', icon: <Pin size={16} /> },
    { id: 'invitations', label: 'Приглашения', href: '/employer/invitations', icon: <Mail size={16} /> },
    { id: 'vacancies', label: 'Вакансии', href: '/employer/vacancies', icon: <Building size={16} /> },
    { id: 'ats-settings', label: 'Интеграция ATS', href: '/employer/ats-settings', icon: <Sliders size={16} /> },
  ];

  return (
    <div className={`min-h-screen bg-[#1B1C21] text-[#EDEDED] flex flex-col ${className}`}>
      {/* Header */}
      <header className="border-b border-[#2D2E37] bg-[#202129] px-4 sm:px-8 py-3 sticky top-0 z-40">
        <div className="max-w-[1340px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <a href="/" className="flex items-center">
              <img src="/brand/logo_01.svg" alt="ФСП" className="h-8 w-auto" />
            </a>
            <span className="hidden md:inline text-xs font-mono text-[#402FFF] bg-[#402FFF]/10 px-2 py-0.5 rounded border border-[#402FFF]/30">
              Кабинет работодателя (Reverse Recruiting)
            </span>
          </div>

          <div className="flex items-center gap-3">
            <RoleSwitcherBar />
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="max-w-[1340px] mx-auto flex items-center gap-1 mt-3 overflow-x-auto scrollbar-none text-xs font-mono">
          {tabs.map((tab) => {
            const isActive = currentTab === tab.id;
            return (
              <a
                key={tab.id}
                href={tab.href}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-t-[6px] border-b-2 whitespace-nowrap transition-colors ${
                  isActive
                    ? 'border-[#402FFF] text-white bg-[#1B1C21] font-bold shadow-[0_-2px_10px_rgba(64,47,255,0.2)]'
                    : 'border-transparent text-[#9B9C9E] hover:text-[#EDEDED] hover:bg-[#2D2E37]'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </a>
            );
          })}
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="max-w-[1340px] w-full mx-auto p-4 sm:p-8 flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#2D2E37] bg-[#202129] py-4 text-center text-xs font-mono text-[#5F5F66]">
        Платформа ИТ-Талантов ФСП России • Модель реверс-рекрутинга (LHH) • 152-ФЗ защита
      </footer>
    </div>
  );
};
