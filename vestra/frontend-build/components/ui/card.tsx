import * as React from 'react';
import { cn } from '@/lib/utils';

// ─── Card ─────────────────────────────────────────────────────────────────

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function Card({ className, hover = false, padding = 'md', children, ...props }: CardProps) {
  const paddings = { none: '', sm: 'p-4', md: 'p-6', lg: 'p-8' };
  return (
    <div
      className={cn(
        'bg-white rounded-2xl border border-gray-100 shadow-sm',
        hover && 'hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 hover-card cursor-pointer',
        paddings[padding],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn('text-lg font-semibold text-gray-900', className)} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn(className)} {...props}>
      {children}
    </div>
  );
}

// ─── Badge ────────────────────────────────────────────────────────────────

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = 'default', children, ...props }: BadgeProps) {
  const variants: Record<BadgeVariant, string> = {
    default: 'bg-gray-100 text-gray-700 border-gray-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    danger: 'bg-red-50 text-red-700 border-red-200',
    info: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  color?: string;
  trend?: { value: number; label: string; positive?: boolean };
}

export function StatCard({ label, value, subtext, icon, color = 'emerald', trend }: StatCardProps) {
  const colors: Record<string, string> = {
    emerald: 'bg-emerald-50 text-emerald-600',
    blue: 'bg-blue-50 text-blue-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  };

  const isPositive = trend ? (trend.positive !== undefined ? trend.positive : trend.value >= 0) : true;

  return (
    <Card className="flex-1 min-w-0 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wider truncate">{label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1.5 tracking-tight">{value}</p>
          {subtext && <p className="text-xs text-gray-400 mt-1">{subtext}</p>}
          {trend && (
            <p className={cn('text-xs font-semibold mt-1.5 flex items-center gap-1 animate-fade-in', isPositive ? 'text-emerald-600' : 'text-red-500')}>
              <span className="text-sm">{isPositive ? '↑' : '↓'}</span>
              {Math.abs(trend.value)}{typeof trend.value === 'number' && !trend.label?.includes('%') ? '%' : ''} {trend.label}
            </p>
          )}
        </div>
        {icon && (
          <div className={cn('p-3 rounded-xl flex-shrink-0 shadow-sm', colors[color])}>
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────

interface ProgressProps {
  value: number;
  max?: number;
  className?: string;
  color?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function Progress({ value, max = 100, className, color, showLabel = false, size = 'md' }: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const barColor = color || (pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500');
  const heights = { sm: 'h-1.5', md: 'h-2.5', lg: 'h-4' };

  return (
    <div className={cn('w-full', className)}>
      <div className={cn('w-full bg-gray-100 rounded-full overflow-hidden', heights[size])}>
        <div
          className={cn('rounded-full transition-all duration-700', barColor, heights[size])}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-gray-500 mt-1 text-right">{Math.round(pct)}%</p>
      )}
    </div>
  );
}

// ─── Loading Spinner ──────────────────────────────────────────────────────

export function Spinner({ className, size = 'md' }: { className?: string; size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' };
  return (
    <div className={cn('animate-spin rounded-full border-2 border-gray-200 border-t-emerald-600', sizes[size], className)} />
  );
}

export function LoadingScreen({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-emerald-600 rounded-xl flex items-center justify-center">
          <span className="text-white font-bold text-sm">V</span>
        </div>
        <span className="font-bold text-xl text-gray-900">Vestra</span>
      </div>
      <Spinner />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}
