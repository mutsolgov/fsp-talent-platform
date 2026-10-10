import React from 'react';
import { AdminLayout } from '../components/templates/AdminLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { BenchmarkMetricTile } from '../components/molecules/BenchmarkMetricTile';
import { BarChart, Users, Trophy, ShieldCheck, Mail } from '../components/icons';

export const AdminAnalyticsPage: React.FC = () => {
  return (
    <AdminLayout>
      <div className="flex flex-col gap-6 max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Аналитика и показатели экосистемы ФСП
              </h1>
              <Badge variant="fsp" size="sm">
                ЛЦТ 2026
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Сводные метрики валидации, динамика реверс-рекрутинга и распределение кандидатов по категориям.
            </p>
          </div>

          <a href="/demo/benchmark-runner">
            <Button variant="fsp_mint" size="sm">
              <span>Запустить Golden Benchmark 60×15</span>
            </Button>
          </a>
        </div>

        {/* Tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
            <span className="text-xs font-mono text-[#9B9C9E]">Верифицировано талантов:</span>
            <div className="font-mono text-3xl font-bold text-white mt-1">1,248</div>
            <span className="text-[11px] font-mono text-[#00F5D4]">+124 за неделю</span>
          </div>

          <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
            <span className="text-xs font-mono text-[#9B9C9E]">Аккредитовано компаний:</span>
            <div className="font-mono text-3xl font-bold text-white mt-1">184</div>
            <span className="text-[11px] font-mono text-[#00F5D4]">100% ИНН проверены</span>
          </div>

          <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
            <span className="text-xs font-mono text-[#9B9C9E]">Конверсия инвайтов в оффер:</span>
            <div className="font-mono text-3xl font-bold text-[#00F5D4] mt-1">42.8%</div>
            <span className="text-[11px] font-mono text-[#C8C9CA]">В 3 раза выше классических резюме</span>
          </div>

          <div className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
            <span className="text-xs font-mono text-[#9B9C9E]">Защита от утечек (KITE Leak):</span>
            <div className="font-mono text-3xl font-bold text-[#00F5D4] mt-1">97.1%</div>
            <span className="text-[11px] font-mono text-[#C8C9CA]">HMAC-SHA256 изоморфизм</span>
          </div>
        </div>

        {/* Distribution Table */}
        <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4">
          <h2 className="font-mono text-base font-bold text-white">
            Распределение специалистов по дисциплинам и категориям
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
            <div className="p-4 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2">
              <span className="text-[#00F5D4] font-bold">Backend разработка (420 чел.)</span>
              <div className="text-[11px] text-[#9B9C9E]">
                Junior: 42 • Middle: 128 • Senior: 95 • Lead: 34
              </div>
            </div>

            <div className="p-4 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2">
              <span className="text-[#402FFF] font-bold">Frontend разработка (380 чел.)</span>
              <div className="text-[11px] text-[#9B9C9E]">
                Junior: 51 • Middle: 140 • Senior: 82 • Lead: 29
              </div>
            </div>

            <div className="p-4 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col gap-2">
              <span className="text-[#FFD700] font-bold">Machine Learning & Data (248 чел.)</span>
              <div className="text-[11px] text-[#9B9C9E]">
                Junior: 28 • Middle: 74 • Senior: 61 • Lead: 19
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};
export default AdminAnalyticsPage;
