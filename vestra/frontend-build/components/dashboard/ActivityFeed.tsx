'use client';

import { cn } from '@/lib/utils';
import { getRoleTheme, normalizeRole } from '@/lib/roleThemes';
import { useAuthStore } from '@/store/authStore';
import { Card, Badge } from '@/components/ui/card';
import { formatRelativeTime } from '@/lib/utils';
import { Activity, Clock } from 'lucide-react';

export interface ActivityItem {
  id: string | number;
  title: string;
  description?: string;
  timestamp: string;
  type?: 'success' | 'warning' | 'info' | 'danger';
  icon?: React.ReactNode;
  action?: { label: string; href: string };
}

interface ActivityFeedProps {
  items: ActivityItem[];
  title?: string;
  emptyMessage?: string;
  className?: string;
  maxItems?: number;
}

export default function ActivityFeed({
  items,
  title = 'Recent Activity',
  emptyMessage = 'No recent activity',
  className,
  maxItems = 5,
}: ActivityFeedProps) {
  const { user } = useAuthStore();
  const role = normalizeRole(user?.role);
  const theme = getRoleTheme(role);

  const typeStyles: Record<string, { dot: string; bg: string }> = {
    success: { dot: 'bg-emerald-500', bg: 'bg-emerald-50' },
    warning: { dot: 'bg-amber-500', bg: 'bg-amber-50' },
    info: { dot: 'bg-blue-500', bg: 'bg-blue-50' },
    danger: { dot: 'bg-red-500', bg: 'bg-red-50' },
  };

  return (
    <Card className={cn('overflow-hidden', className)} padding="none">
      <div className="px-5 pt-4 pb-3 flex items-center justify-between">
        <h3 className="font-bold text-gray-900 flex items-center gap-2 text-sm">
          <Activity className={cn('w-4 h-4', theme.primaryText)} />
          {title}
        </h3>
        <Clock className="w-4 h-4 text-gray-300" />
      </div>
      <div className="divide-y divide-gray-50">
        {items.length === 0 ? (
          <div className="text-center py-10">
            <Activity className="w-8 h-8 text-gray-200 mx-auto mb-2" />
            <p className="text-xs text-gray-400 font-medium">{emptyMessage}</p>
          </div>
        ) : (
          items.slice(0, maxItems).map((item) => {
            const style = item.type ? typeStyles[item.type] : typeStyles.info;
            return (
              <div
                key={item.id}
                className="flex items-start gap-3 px-5 py-3 hover:bg-gray-50/50 transition-colors"
              >
                <div className="relative flex-shrink-0 mt-0.5">
                  <div className={cn('w-2 h-2 rounded-full', style.dot)} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
                  {item.description && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{item.description}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">{formatRelativeTime(item.timestamp)}</p>
                </div>
                {item.action && (
                  <a
                    href={item.action.href}
                    className={cn('text-xs font-medium hover:underline flex-shrink-0', theme.primaryText)}
                  >
                    {item.action.label}
                  </a>
                )}
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
