import React from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { NeedCreationWizard } from '../components/organisms/NeedCreationWizard';

export const CreateNeedPage: React.FC = () => {
  const handleComplete = (needId: number) => {
    window.location.href = `/employer/candidate-bank?needId=${needId}`;
  };

  const handleCancel = () => {
    window.location.href = '/employer/needs';
  };

  return (
    <EmployerLayout currentTab="needs">
      <div className="max-w-4xl mx-auto flex flex-col gap-6">
        <div>
          <h1 className="font-mono text-2xl font-bold text-white">
            Формирование потребности инженерной команды
          </h1>
          <p className="text-xs text-[#9B9C9E] mt-1">
            Мастер создания запроса: обязательная фиксация рублевой зарплатной вилки (152-ФЗ и регламент ФСП) и стека технологий.
          </p>
        </div>

        <div className="p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37]">
          <NeedCreationWizard
            onComplete={handleComplete}
            onCancel={handleCancel}
          />
        </div>
      </div>
    </EmployerLayout>
  );
};
export default CreateNeedPage;
