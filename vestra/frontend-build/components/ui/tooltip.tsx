'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

// ─── Types ──────────────────────────────────────────────────────────────────

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content: React.ReactNode;
  position?: TooltipPosition;
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
  delay?: number;
  disabled?: boolean;
}

// ─── Tooltip ────────────────────────────────────────────────────────────────

function Tooltip({
  content,
  position = 'top',
  children,
  className,
  contentClassName,
  delay = 200,
  disabled = false,
}: TooltipProps) {
  const [visible, setVisible] = React.useState(false);
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  function show() {
    if (disabled) return;
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setVisible(true), delay);
  }

  function hide() {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  }

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const positionClasses: Record<TooltipPosition, string> = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2.5',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2.5',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2.5',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2.5',
  };

  const arrowClasses: Record<TooltipPosition, string> = {
    top: 'top-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent border-t-gray-900 dark:border-t-gray-700',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent border-b-gray-900 dark:border-b-gray-700',
    left: 'left-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-gray-900 dark:border-l-gray-700',
    right: 'right-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-gray-900 dark:border-r-gray-700',
  };

  const animationClasses: Record<TooltipPosition, string> = {
    top: 'animate-in fade-in slide-in-from-bottom-1 duration-150',
    bottom: 'animate-in fade-in slide-in-from-top-1 duration-150',
    left: 'animate-in fade-in slide-in-from-right-1 duration-150',
    right: 'animate-in fade-in slide-in-from-left-1 duration-150',
  };

  return (
    <div
      className={cn('relative inline-flex', className)}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}

      {visible && content && (
        <div
          role="tooltip"
          className={cn(
            'absolute z-[9999] pointer-events-none',
            positionClasses[position],
            animationClasses[position]
          )}
        >
          {/* Arrow */}
          <div
            className={cn(
              'absolute w-0 h-0 border-4',
              arrowClasses[position]
            )}
          />

          {/* Content */}
          <div
            className={cn(
              'rounded-lg bg-gray-900 dark:bg-gray-700 px-3 py-1.5 text-xs text-white shadow-lg whitespace-nowrap max-w-xs',
              contentClassName
            )}
          >
            {content}
          </div>
        </div>
      )}
    </div>
  );
}

Tooltip.displayName = 'Tooltip';

export { Tooltip };
export type { TooltipProps, TooltipPosition };
