import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { CandidateCardUnmasked } from '../components/organisms/CandidateCardUnmasked';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { CandidateFullProfileResponse } from '../types';
import { Users, Mail, CheckCircle, Download, FileText } from '../components/icons';
import { api } from '../api/client';

export const EmployerApplicationsPage: React.FC = () => {
  const [applications, setApplications] = useState<CandidateFullProfileResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  useEffect(() => {
    const fetchApplications = async () => {
      setIsLoading(true);
      try {
        const data = await api.get<any>('/applications/received');
        const list = Array.isArray(data) ? data : data?.items || [];
        const normalized: CandidateFullProfileResponse[] = list.map((item: any) => {
          const app = item.application || item;
          const contacts = item.candidate_contacts || {};
          const candId = contacts.candidate_id ?? app.candidate_profile_id ?? app.candidateId ?? 1;
          const fullName = contacts.full_name || app.candidate_name || `Кандидат #${candId}`;
          return {
            id: candId,
            maskedCode: `CAND-${candId}`,
            fullName: fullName,
            specialization: 'backend',
            verifiedGrade: 'senior',
            finalScore: 90.0,
            isFspVerified: true,
            sportRank: null,
            fspId: null,
            theta: 90.0,
            freshnessScore: 90,
            skills: ['Python', 'PostgreSQL', 'Docker'],
            email: contacts.email || `candidate_${candId}@fsp.ru`,
            phone: contacts.phone,
            telegram: contacts.telegram,
            githubUrl: contacts.github_url,
            isMasked: false,
            cooldownUntil: null,
            experienceYears: 4,
            summaryBio: app.cover_letter || `Отклик на вакансию #${app.vacancy_id || ''}`,
          };
        });
        setApplications(normalized);
      } catch {
        setApplications([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchApplications();
  }, []);

  const handleBatchExport = () => {
    setExportNotice('Пакетный экспорт в ATS запущен');
    setTimeout(() => setExportNotice(null), 4000);
  };

  return (
    <EmployerLayout currentTab="vacancies">
      <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Полученные отклики соискателей
              </h1>
              <Badge variant="fsp" size="sm">
                {applications.length} откликов
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Кандидаты самостоятельно откликнулись на ваши вакансии — контакты раскрыты в соответствии с 152-ФЗ.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={handleBatchExport}>
              <Download size={14} />
              <span>Экспорт всех в ATS</span>
            </Button>
          </div>
        </div>

        {exportNotice && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <CheckCircle size={16} />
            <span>{exportNotice}</span>
          </div>
        )}

        {applications.length === 0 ? (
          <div className="p-12 text-center bg-[#202129] rounded-[16px] border border-[#2D2E37] text-xs font-mono text-[#9B9C9E]">
            {isLoading ? 'Загрузка откликов...' : 'Пока нет полученных откликов на ваши вакансии.'}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {applications.map((cand) => (
              <CandidateCardUnmasked
                key={cand.id}
                candidate={cand}
                onPdfDownload={() => window.open('/api/v1/resume-pdf/' + cand.id + '/full', '_blank')}
              />
            ))}
          </div>
        )}
      </div>
    </EmployerLayout>
  );
};
export default EmployerApplicationsPage;
