'use client';

import { useMemo } from 'react';
import zxcvbn from 'zxcvbn';
import { cn } from '@/lib/utils';

interface Props {
  password: string;
  className?: string;
}

const STRENGTH_LABELS = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'] as const;

const STRENGTH_COLORS = [
  'bg-red-500',    // 0 — Weak
  'bg-orange-500', // 1 — Fair
  'bg-yellow-500',  // 2 — Good
  'bg-green-500',   // 3 — Strong
  'bg-green-600',   // 4 — Very Strong
] as const;

const STRENGTH_TEXT_COLORS = [
  'text-red-600',
  'text-orange-600',
  'text-yellow-700',
  'text-green-600',
  'text-green-700',
] as const;

export default function PasswordStrengthMeter({ password, className }: Props) {
  const result = useMemo(() => {
    if (!password) return null;
    return zxcvbn(password);
  }, [password]);

  if (!result) return null;

  const score = result.score;
  const label = STRENGTH_LABELS[score];
  const barColor = STRENGTH_COLORS[score];
  const textColor = STRENGTH_TEXT_COLORS[score];
  const pct = ((score + 1) / STRENGTH_LABELS.length) * 100;

  return (
    <div className={cn('mt-1.5 space-y-1', className)}>
      {/* Bar */}
      <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-300', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {/* Label */}
      <p className={cn('text-xs font-medium', textColor)}>{label}</p>
    </div>
  );
}
