'use client';

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { PlayerSimStats, LineupSimStats } from '@/lib/optimizer/types';

const TOOLTIP_STYLE = {
  background: '#171b21',
  border: '1px solid #2b323b',
  borderRadius: 8,
  fontSize: 12,
  color: '#f4f6f8',
};

export function PlayerSimChart({ stats, names }: { stats: PlayerSimStats[]; names: Record<string, string> }) {
  const data = stats
    .slice()
    .sort((a, b) => b.mean - a.mean)
    .slice(0, 15)
    .map((s) => ({
      name: names[s.player_id] ?? s.player_id,
      Median: Number(s.median.toFixed(1)),
      Mean: Number(s.mean.toFixed(1)),
      'P90': Number(s.p90.toFixed(1)),
    }));

  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#20252c" />
        <XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} height={80} tick={{ fontSize: 10, fill: '#8b97a6' }} />
        <YAxis tick={{ fontSize: 11, fill: '#8b97a6' }} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="Median" fill="#2dd4bf" radius={[3, 3, 0, 0]} />
        <Bar dataKey="P90" fill="#f59e0b" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LineupSimChart({ stats }: { stats: LineupSimStats[] }) {
  const data = stats.map((s, i) => ({
    name: `Lineup ${i + 1}`,
    Median: Number(s.median.toFixed(1)),
    P90: Number(s.p90.toFixed(1)),
    'Dup. risk (x100)': Number((s.duplication_risk_proxy * 100).toFixed(0)),
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#20252c" />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#8b97a6' }} />
        <YAxis tick={{ fontSize: 11, fill: '#8b97a6' }} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="Median" fill="#2dd4bf" radius={[3, 3, 0, 0]} />
        <Bar dataKey="P90" fill="#f59e0b" radius={[3, 3, 0, 0]} />
        <Bar dataKey="Dup. risk (x100)" fill="#f43f5e" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
