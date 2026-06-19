'use client';

import { Card } from '@/components/ui/card';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

const COLORS = { emerald: '#10b981', blue: '#3b82f6', purple: '#8b5cf6', amber: '#f59e0b', red: '#ef4444', gray: '#6b7280' };

interface OverviewChartsProps {
  charts: {
    monthly_revenue?: { month: string; revenue?: number }[];
    user_distribution?: { name: string; value: number; color: string }[];
  } | null;
}

export default function OverviewCharts({ charts }: OverviewChartsProps) {
  if (!charts) return null;

  return (
    <div className="grid lg:grid-cols-3 gap-5">
      <Card className="lg:col-span-2">
        <h3 className="font-bold text-gray-900 mb-4 text-sm">Revenue Trend</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={charts.monthly_revenue || []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v} />
            <RechartsTooltip formatter={(v: any) => `KES ${Number(v).toLocaleString()}`} />
            <Bar dataKey="revenue" fill={COLORS.emerald} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
      <Card>
        <h3 className="font-bold text-gray-900 mb-3 text-sm">User Roles</h3>
        <div className="flex justify-center">
          <PieChart width={160} height={160}>
            <Pie data={charts.user_distribution || []} cx={75} cy={75} innerRadius={40} outerRadius={65} dataKey="value" paddingAngle={2}>
              {(charts.user_distribution || []).map((d: any, i: number) => (
                <Cell key={i} fill={d.color} />
              ))}
            </Pie>
            <RechartsTooltip />
          </PieChart>
        </div>
        <div className="space-y-1 mt-2">
          {(charts.user_distribution || []).map((d: any) => (
            <div key={d.name} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                <span className="text-gray-600">{d.name}</span>
              </div>
              <span className="font-medium">{d.value}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
