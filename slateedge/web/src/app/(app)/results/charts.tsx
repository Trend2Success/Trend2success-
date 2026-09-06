'use client';

import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const TOOLTIP_STYLE = {
  background: '#171b21',
  border: '1px solid #2b323b',
  borderRadius: 8,
  fontSize: 12,
  color: '#f4f6f8',
};

export function BankrollTrendChart({ data }: { data: { date: string; cumulative: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#20252c" />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#8b97a6' }} />
        <YAxis tick={{ fontSize: 11, fill: '#8b97a6' }} tickFormatter={(v) => `$${v}`} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `$${v.toFixed(2)}`} />
        <Line type="monotone" dataKey="cumulative" stroke="#2dd4bf" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function RoiByContestTypeChart({ data }: { data: { type: string; roi: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#20252c" />
        <XAxis dataKey="type" tick={{ fontSize: 10, fill: '#8b97a6' }} />
        <YAxis tick={{ fontSize: 11, fill: '#8b97a6' }} tickFormatter={(v) => `${v}%`} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `${v.toFixed(1)}%`} />
        <Bar dataKey="roi" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.roi >= 0 ? '#2dd4bf' : '#f43f5e'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function EntriesVsResultsChart({ data }: { data: { date: string; entries: number; netCents: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#20252c" />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#8b97a6' }} />
        <YAxis tick={{ fontSize: 11, fill: '#8b97a6' }} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="entries" fill="#5eead4" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
