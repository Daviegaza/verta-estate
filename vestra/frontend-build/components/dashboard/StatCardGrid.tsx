'use client';

import { cn } from '@/lib/utils';
import { getRoleTheme, normalizeRole } from '@/lib/roleThemes';
import { useAuthStore } from '@/store/authStore';
import { Card } from '@/components/ui/card';

export interface StatItem {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  subtext?: string;
  trend?: {
    value: string | number;
    label?: string;
    positive?: boolean;
  };
  onClick?: () => void;
}

interface StatCardGridProps {
  stats: StatItem[];
  columns?: 2 | 3 | 4;
  className?: string;
}

export default function StatCardGrid({ stats, columns = 4, className }: StatCardGridProps) {
  const { user } = useAuthStore();
  const role = normalizeRole(user?.role);
  const theme = getRoleTheme(role);

  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={cn('grid gap-4 mb-8', gridCols[columns], className)}>
      {stats.map((stat, i) => (
        <Card
          key={stat.label + i}
          padding="md"
          className={cn(
            'hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group',
            stat.onClick && 'cursor-pointer'
          )}
          onClick={stat.onClick}
        >
          <div className="flex items-start justify-between mb-2">
            <div className={cn('p-2.5 rounded-xl shadow-sm', theme.statIconBg)}>
              <span className={theme.statIconColor}>{stat.icon}</span>
            </div>
            {stat.trend && (
              <span className={cn(
                'inline-flex items-center gap-0.5 text-xs font-semibold px-2 py-0.5 rounded-full',
                stat.trend.positive !== false
                  ? 'bg-emerald-50 text-emerald-600'
                  : 'bg-red-50 text-red-600'
              )}>
                {stat.trend.positive !== false ? '↑' : '↓'} {stat.trend.value}
                {stat.trend.label && <span className="font-normal opacity-70">{stat.trend.label}</span>}
              </span>
            )}
          </div>
          <p className="text-2xl lg:text-3xl font-bold text-gray-900 mb-0.5 tracking-tight">
            {stat.value}
          </p>
          <p className="text-xs text-gray-500 font-medium">{stat.label}</p>
          {stat.subtext && (
            <p className="text-xs text-gray-400 mt-1">{stat.subtext}</p>
          )}
        </Card>
      ))}
    </div>
  );
}
