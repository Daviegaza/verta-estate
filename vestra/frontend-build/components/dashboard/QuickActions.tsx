'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { getRoleTheme, normalizeRole } from '@/lib/roleThemes';
import { useAuthStore } from '@/store/authStore';
import { ArrowRight, Zap } from 'lucide-react';
import { Card } from '@/components/ui/card';

export interface QuickAction {
  label: string;
  desc: string;
  icon: React.ReactNode;
  href: string;
  color?: string;
  iconBg?: string;
}

interface QuickActionsProps {
  actions: QuickAction[];
  title?: string;
  className?: string;
}

export default function QuickActions({ actions, title = 'Quick Actions', className }: QuickActionsProps) {
  const { user } = useAuthStore();
  const role = normalizeRole(user?.role);
  const theme = getRoleTheme(role);

  return (
    <Card className={cn('overflow-hidden', className)} padding="none">
      <div className={cn('bg-gradient-to-r from-opacity-50 to-transparent -mx-0 px-6 pt-5 pb-3 border-b', theme.statIconBg, theme.borderColor)}>
        <h3 className="font-bold text-gray-900 flex items-center gap-2">
          <Zap className={cn('w-4 h-4', theme.primaryText)} />
          {title}
        </h3>
      </div>
      <div className="p-3 space-y-1">
        {actions.map((action) => (
          <Link key={action.label + action.href} href={action.href}>
            <div
              className={cn(
                'flex items-center gap-3 px-3 py-3 rounded-xl transition-all cursor-pointer group border',
                action.color || `${theme.statIconBg} ${theme.borderColor} hover:bg-gray-50`
              )}
            >
              <div className={cn(
                'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-all',
                action.iconBg || theme.primary
              )}>
                <span className="text-white">{action.icon}</span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-gray-900 group-hover:text-gray-700 transition-colors">
                  {action.label}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{action.desc}</p>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-600 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
            </div>
          </Link>
        ))}
      </div>
    </Card>
  );
}
