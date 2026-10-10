import React from 'react';

export interface RadarMatchChartProps {
  testMatch: number; // 0..100
  stackMatch: number; // 0..100
  fspMatch: number; // 0..100 (0 for non-fsp)
  freshnessMatch: number; // 0..100
  isFspProfile: boolean;
  size?: number;
  className?: string;
}

export const RadarMatchChart: React.FC<RadarMatchChartProps> = ({
  testMatch,
  stackMatch,
  fspMatch,
  freshnessMatch,
  isFspProfile,
  size = 220,
  className = '',
}) => {
  const center = size / 2;
  const radius = (size / 2) * 0.75;

  // 4 axes: Top (Test), Right (Stack), Bottom (FSP/Discipline), Left (Freshness)
  const axes = [
    { label: 'Тест KITE', value: testMatch, angle: -Math.PI / 2 },
    { label: 'Стек', value: stackMatch, angle: 0 },
    { label: isFspProfile ? 'ФСП Разряд' : 'Практика (0.52)', value: isFspProfile ? fspMatch : testMatch, angle: Math.PI / 2 },
    { label: 'Свежесть', value: freshnessMatch, angle: Math.PI },
  ];

  const getCoordinates = (value: number, angle: number) => {
    const r = (value / 100) * radius;
    const x = center + r * Math.cos(angle);
    const y = center + r * Math.sin(angle);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  };

  const polygonPoints = axes.map((a) => getCoordinates(a.value, a.angle)).join(' ');

  // Grid concentric levels (25, 50, 75, 100)
  const gridLevels = [0.25, 0.5, 0.75, 1.0];

  return (
    <div className={`relative flex flex-col items-center select-none ${className}`}>
      <svg width={size} height={size} className="overflow-visible">
        {/* Background Grids */}
        {gridLevels.map((lvl, idx) => {
          const r = radius * lvl;
          return (
            <circle
              key={idx}
              cx={center}
              cy={center}
              r={r}
              fill="none"
              stroke="#2D2E37"
              strokeDasharray={lvl === 1.0 ? 'none' : '3 3'}
              strokeWidth={1}
            />
          );
        })}

        {/* Axes Lines */}
        {axes.map((a, idx) => {
          const x2 = center + radius * Math.cos(a.angle);
          const y2 = center + radius * Math.sin(a.angle);
          return (
            <line
              key={idx}
              x1={center}
              y1={center}
              x2={x2}
              y2={y2}
              stroke="#3D3E42"
              strokeWidth={1}
            />
          );
        })}

        {/* Value Polygon */}
        <polygon
          points={polygonPoints}
          fill={isFspProfile ? 'rgba(64, 47, 255, 0.25)' : 'rgba(0, 245, 212, 0.25)'}
          stroke={isFspProfile ? '#402FFF' : '#00F5D4'}
          strokeWidth={2}
          className="transition-all duration-300"
        />

        {/* Vertex Dots */}
        {axes.map((a, idx) => {
          const [vx, vy] = getCoordinates(a.value, a.angle).split(',');
          return (
            <circle
              key={idx}
              cx={vx}
              cy={vy}
              r={4}
              fill={isFspProfile ? '#402FFF' : '#00F5D4'}
              stroke="#1B1C21"
              strokeWidth={1.5}
            />
          );
        })}
      </svg>

      {/* Axis Labels */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-[11px] font-mono text-[#9B9C9E] w-full">
        {axes.map((a, idx) => (
          <div key={idx} className="flex justify-between items-center">
            <span>{a.label}:</span>
            <span className="font-semibold text-[#EDEDED]">{Math.round(a.value)}%</span>
          </div>
        ))}
      </div>

      {/* Accessible Hidden Table for Screen Readers (WCAG AAA) */}
      <table className="sr-only">
        <caption>Многофакторный радарный профиль соответствия</caption>
        <thead>
          <tr>
            <th>Фактор</th>
            <th>Значение</th>
          </tr>
        </thead>
        <tbody>
          {axes.map((a, idx) => (
            <tr key={idx}>
              <td>{a.label}</td>
              <td>{a.value}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
