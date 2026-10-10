import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { ShortlistManager } from '../components/organisms/ShortlistManager';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Spinner } from '../components/atoms/Spinner';
import { Input } from '../components/atoms/Input';
import { SavedShortlistDetailResponse, CandidateAnonymizedSummary, Specialization, Grade, SportRank } from '../types';
import { Pin, Users, Plus, AlertCircle, CheckCircle, RefreshCw, X } from '../components/icons';
import { api } from '../api/client';

export interface ShortlistSummaryItem {
  id: number;
  title: string;
  needId?: number;
  candidatesCount: number;
  pinnedCount: number;
  updatedAt: string;
}

const mapBackendShortlistDetail = (data: any): SavedShortlistDetailResponse => {
  const items = Array.isArray(data.items) ? data.items : [];
  const candidates: CandidateAnonymizedSummary[] = items.map((item: any) => {
    const card = item.candidate_card || {};
    return {
      id: item.candidate_profile_id ?? card.id ?? 1,
      maskedCode: card.masked_full_name || `CAND-${item.candidate_profile_id ?? card.id ?? 1}`,
      specialization: (card.specialization as Specialization) || 'backend',
      verifiedGrade: (card.grade as Grade) || 'middle',
      finalScore: item.match_score ?? card.test_score ?? 80.0,
      initialScore: (item.match_score ?? 80.0) - (item.delta_score ?? 0.0),
      deltaScore: item.delta_score ?? 0.0,
      isPinned: Boolean(item.is_pinned),
      fspId: card.fsp_id || null,
      sportRank: (card.sport_rank as SportRank) || (card.fsp_verified ? '1Р' : null),
      isFspVerified: Boolean(card.fsp_verified),
      theta: card.test_score ?? 75.0,
      freshnessScore: card.freshness_score ?? 90,
      skills: card.skills || [],
      matchedSkills: item.explainability?.matched_skills || card.explainability?.matched_skills || card.skills?.slice(0, 3) || [],
      missingSkills: item.explainability?.missing_skills || card.explainability?.missing_skills || [],
      weights: item.explainability?.weights || card.explainability?.weights || {
        isFspProfile: Boolean(card.fsp_verified),
        wTest: card.fsp_verified ? 0.35 : 0.52,
        wStack: card.fsp_verified ? 0.25 : 0.30,
        wFsp: card.fsp_verified ? 0.25 : 0.00,
        wFreshness: card.fsp_verified ? 0.15 : 0.18,
      },
      factors: {
        testScore: card.test_score ?? 75.0,
        stackMatchPct: item.explainability?.stack_match_pct ?? 90.0,
        fspScore: card.fsp_verified ? 85.0 : 0.0,
        freshnessScore: card.freshness_score ?? 90.0,
      },
      fspAchievements: card.fsp_achievements || (card.fsp_verified ? [{
        title: 'Верифицированный участник соревнований ФСП',
        year: 2025,
        rank: card.sport_rank || '1Р',
        medal: 'participant',
      }] : []),
    };
  });

  const pinnedIds = items
    .filter((i: any) => i.is_pinned)
    .map((i: any) => i.candidate_profile_id ?? i.candidate_card?.id);

  return {
    id: data.id,
    needId: data.need_id ?? 0,
    title: data.title || `Шортлист #${data.id}`,
    candidates,
    pinnedIds,
    filterCriteria: data.filter_criteria_json || {},
  };
};

export const ShortlistsPage: React.FC = () => {
  const [shortlists, setShortlists] = useState<ShortlistSummaryItem[]>([]);
  const [selectedShortlistId, setSelectedShortlistId] = useState<number | null>(null);
  const [activeDetail, setActiveDetail] = useState<SavedShortlistDetailResponse | null>(null);
  const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Create shortlist dialog state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>('');
  const [isCreating, setIsCreating] = useState<boolean>(false);

  const loadShortlistsList = async () => {
    setIsLoadingList(true);
    try {
      const data = await api.get<any[]>('/candidate-bank/shortlists');
      const list = Array.isArray(data) ? data : [];
      const summaries: ShortlistSummaryItem[] = list.map((s: any) => ({
        id: s.id,
        title: s.title || `Шортлист #${s.id}`,
        needId: s.need_id,
        candidatesCount: s.candidates_count ?? s.items?.length ?? 0,
        pinnedCount: s.pinned_count ?? 0,
        updatedAt: s.created_at ? new Date(s.created_at).toLocaleDateString('ru-RU') : 'Недавно',
      }));
      setShortlists(summaries);

      if (summaries.length > 0) {
        const nextId = selectedShortlistId && summaries.some((s) => s.id === selectedShortlistId)
          ? selectedShortlistId
          : summaries[0].id;
        setSelectedShortlistId(nextId);
        loadShortlistDetail(nextId);
      } else {
        setSelectedShortlistId(null);
        setActiveDetail(null);
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err?.message || 'Не удалось загрузить список шортлистов',
      });
      setShortlists([]);
      setActiveDetail(null);
    } finally {
      setIsLoadingList(false);
    }
  };

  const loadShortlistDetail = async (id: number) => {
    setIsLoadingDetail(true);
    try {
      const data = await api.get<any>(`/candidate-bank/shortlists/${id}`);
      setActiveDetail(mapBackendShortlistDetail(data));
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err?.message || 'Не удалось загрузить данные шортлиста',
      });
      setActiveDetail(null);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  useEffect(() => {
    loadShortlistsList();
  }, []);

  const handleSelectShortlist = (id: number) => {
    setSelectedShortlistId(id);
    loadShortlistDetail(id);
  };

  const handlePinToggle = async (candidateId: number) => {
    if (!selectedShortlistId || !activeDetail) return;
    const isCurrentlyPinned = activeDetail.pinnedIds.includes(candidateId);
    try {
      await api.post(`/candidate-bank/shortlists/${selectedShortlistId}/pin/${candidateId}`, {
        is_pinned: !isCurrentlyPinned,
        candidate_profile_id: candidateId,
      });
      setNotification({
        type: 'success',
        text: !isCurrentlyPinned ? 'Кандидат закреплен в верхнем ярусе шортлиста' : 'Кандидат откреплен',
      });
      await loadShortlistDetail(selectedShortlistId);
      await loadShortlistsList();
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err?.message || 'Не удалось изменить фиксацию кандидата',
      });
    }
  };

  const handleRefine = async (criteria: Record<string, unknown>) => {
    if (!selectedShortlistId) return;
    try {
      const res = await api.post<any>(`/candidate-bank/shortlists/${selectedShortlistId}/refine`, {
        new_filter_criteria_json: criteria,
      });
      setActiveDetail(mapBackendShortlistDetail(res));
      setNotification({
        type: 'success',
        text: 'Запрос уточнен! Закрепленные кандидаты сохранены, дельты баллов ΔS пересчитаны.',
      });
      await loadShortlistsList();
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err?.message || 'Не удалось уточнить шортлист',
      });
    }
  };

  const handleDelete = async () => {
    if (!selectedShortlistId) return;
    try {
      await api.delete(`/candidate-bank/shortlists/${selectedShortlistId}`);
      setNotification({
        type: 'success',
        text: 'Шортлист успешно удален.',
      });
      const remaining = shortlists.filter((s) => s.id !== selectedShortlistId);
      setShortlists(remaining);
      if (remaining.length > 0) {
        setSelectedShortlistId(remaining[0].id);
        loadShortlistDetail(remaining[0].id);
      } else {
        setSelectedShortlistId(null);
        setActiveDetail(null);
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err?.message || 'Не удалось удалить шортлист',
      });
    }
  };

  const handleCreateShortlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setIsCreating(true);
    try {
      const created = await api.post<any>('/candidate-bank/shortlists', {
        title: newTitle.trim(),
        filter_criteria_json: {},
        candidate_ids: [],
      });
      setNotification({
        type: 'success',
        text: `Шортлист «${newTitle.trim()}» успешно создан!`,
      });
      setNewTitle('');
      setIsCreateModalOpen(false);
      await loadShortlistsList();
      if (created?.id) {
        setSelectedShortlistId(created.id);
        await loadShortlistDetail(created.id);
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err?.message || 'Не удалось создать шортлист',
      });
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <EmployerLayout currentTab="shortlists">
      <div className="flex flex-col gap-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Сохраненные подборки и шортлисты
              </h1>
              <Badge variant="fsp" size="sm">
                Stateful Matching
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Фильтрация без потери ранее полученной подборки: закрепленные кандидаты (Pin) сохраняются при любых изменениях запроса.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="fsp_mint" size="sm" onClick={() => setIsCreateModalOpen(true)}>
              <Plus size={16} />
              <span>Создать шортлист</span>
            </Button>
          </div>
        </div>

        {/* Notification Banner */}
        {notification && (
          <div
            className={`p-4 rounded-[12px] border text-xs font-mono flex items-center justify-between gap-3 animate-in fade-in ${
              notification.type === 'success'
                ? 'bg-[#00F5D4]/10 border-[#00F5D4]/40 text-[#00F5D4]'
                : 'bg-rose-950/40 border-rose-500/40 text-[#FB7185]'
            }`}
          >
            <div className="flex items-center gap-2">
              {notification.type === 'success' ? (
                <CheckCircle size={18} className="shrink-0" />
              ) : (
                <AlertCircle size={18} className="shrink-0" />
              )}
              <span>{notification.text}</span>
            </div>
            <button
              type="button"
              onClick={() => setNotification(null)}
              className="text-[#9B9C9E] hover:text-white cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Shortlists List / Selector */}
        {isLoadingList ? (
          <div className="flex items-center justify-center py-12 gap-3">
            <Spinner size="md" color="#402FFF" />
            <span className="text-xs font-mono text-[#9B9C9E]">Загрузка шортлистов...</span>
          </div>
        ) : shortlists.length === 0 ? (
          <div className="text-center py-16 bg-[#202129] border border-[#2D2E37] rounded-[14px] p-8 flex flex-col items-center gap-3">
            <Users size={40} className="text-[#5F5F66]" />
            <h3 className="font-mono text-base font-bold text-white">Нет сохраненных шортлистов</h3>
            <p className="text-xs text-[#9B9C9E] max-w-md">
              Сохраняйте перспективных кандидатов в шортлисты для сравнительного анализа и командного рекрутинга.
            </p>
            <Button variant="fsp_mint" size="sm" onClick={() => setIsCreateModalOpen(true)} className="mt-2">
              <Plus size={16} />
              <span>Создать первый шортлист</span>
            </Button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {shortlists.map((sl) => (
                <button
                  key={sl.id}
                  type="button"
                  onClick={() => handleSelectShortlist(sl.id)}
                  className={`p-4 rounded-[12px] text-left border transition-all flex flex-col justify-between gap-2 cursor-pointer ${
                    selectedShortlistId === sl.id
                      ? 'bg-[#202129] border-[#402FFF] shadow-[0_0_15px_rgba(64,47,255,0.3)]'
                      : 'bg-[#1B1C21] border-[#2D2E37] hover:border-[#3D3E42]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-white line-clamp-1">{sl.title}</span>
                    <span className="text-[11px] font-mono text-[#00F5D4] flex items-center gap-1">
                      <Pin size={12} />
                      <span>{sl.pinnedCount}</span>
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-[#9B9C9E]">
                    <span>{sl.candidatesCount} специалистов</span>
                    <span>{sl.updatedAt}</span>
                  </div>
                </button>
              ))}
            </div>

            {/* Pin Management Action Bar */}
            {activeDetail && activeDetail.candidates.length > 0 && (
              <div className="p-4 rounded-[12px] bg-[#1E1F26] border border-[#2D2E37] flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Pin size={16} className="text-[#00F5D4]" />
                    <span className="text-xs font-mono font-bold text-white">
                      Управление фиксацией в верхнем ярусе (Pin):
                    </span>
                  </div>
                  <span className="text-xs font-mono text-[#9B9C9E]">
                    Закреплено: {activeDetail.pinnedIds.length} из {activeDetail.candidates.length}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {activeDetail.candidates.map((c) => {
                    const isPinned = activeDetail.pinnedIds.includes(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => handlePinToggle(c.id)}
                        className={`px-2.5 py-1 rounded-[6px] text-xs font-mono border transition-all flex items-center gap-1.5 cursor-pointer ${
                          isPinned
                            ? 'bg-[#00F5D4]/15 border-[#00F5D4]/60 text-[#00F5D4]'
                            : 'bg-[#202129] border-[#3D3E42] text-[#9B9C9E] hover:text-white hover:border-[#5F5F66]'
                        }`}
                      >
                        <Pin size={12} className={isPinned ? 'fill-current' : ''} />
                        <span>{c.maskedCode}</span>
                        <span className="text-[10px] opacity-75">
                          ({isPinned ? 'В топе' : 'Закрепить'})
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Active Shortlist Detail */}
            {isLoadingDetail ? (
              <div className="flex items-center justify-center py-16 gap-3">
                <Spinner size="lg" color="#402FFF" />
                <span className="text-xs font-mono text-[#9B9C9E]">Загрузка деталей шортлиста...</span>
              </div>
            ) : activeDetail ? (
              <ShortlistManager
                key={activeDetail.id}
                shortlist={activeDetail}
                onRefine={handleRefine}
                onDelete={handleDelete}
              />
            ) : null}
          </>
        )}

        {/* Create Shortlist Modal */}
        {isCreateModalOpen && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in"
          >
            <div className="w-full max-w-md rounded-[14px] bg-[#1B1C21] border border-[#3D3E42] shadow-2xl p-6 flex flex-col gap-4">
              <div className="flex items-center justify-between border-b border-[#2D2E37] pb-3">
                <h3 className="font-mono text-base font-bold text-white">Новый шортлист талантов</h3>
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="p-1 rounded text-[#9B9C9E] hover:text-white cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleCreateShortlist} className="flex flex-col gap-4">
                <Input
                  id="shortlist_title_input"
                  label="Название подборки"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Например: HighLoad Backend Core Team"
                  required
                />

                <div className="flex items-center justify-end gap-2 pt-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                  >
                    Отмена
                  </Button>
                  <Button
                    variant="fsp_mint"
                    size="sm"
                    type="submit"
                    disabled={!newTitle.trim() || isCreating}
                    isLoading={isCreating}
                  >
                    Создать
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </EmployerLayout>
  );
};
export default ShortlistsPage;
