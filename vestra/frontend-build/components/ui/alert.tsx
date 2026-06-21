'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { X, Info, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

type AlertVariant = 'info' | 'success' | 'warning' | 'error';

interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  description?: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  className?: string;
  children?: React.ReactNode;
  icon?: React.ReactNode;
}

// ─── Styles ─────────────────────────────────────────────────────────────────

const variantStyles: Record<AlertVariant, {
  container: string;
  icon: string;
  iconColor: string;
  title: string;
  description: string;
  close: string;
}> = {
  info: {
    container: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    icon: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    iconColor: 'text-blue-600',
    title: 'text-blue-900 dark:text-blue-200',
    description: 'text-blue-700 dark:text-blue-300',
    close: 'hover:bg-blue-100 dark:hover:bg-blue-900/30',
  },
  success: {
    container: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800',
    icon: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400',
    iconColor: 'text-emerald-600',
    title: 'text-emerald-900 dark:text-emerald-200',
    description: 'text-emerald-700 dark:text-emerald-300',
    close: 'hover:bg-emerald-100 dark:hover:bg-emerald-900/30',
  },
  warning: {
    container: 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800',
    icon: 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
    iconColor: 'text-amber-600',
    title: 'text-amber-900 dark:text-amber-200',
    description: 'text-amber-700 dark:text-amber-300',
    close: 'hover:bg-amber-100 dark:hover:bg-amber-900/30',
  },
  error: {
    container: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
    icon: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    iconColor: 'text-red-600',
    title: 'text-red-900 dark:text-red-200',
    description: 'text-red-700 dark:text-red-300',
    close: 'hover:bg-red-100 dark:hover:bg-red-900/30',
  },
};

const defaultIcons: Record<AlertVariant, React.ReactNode> = {
  info: <Info className="w-5 h-5" />,
  success: <CheckCircle className="w-5 h-5" />,
  warning: <AlertTriangle className="w-5 h-5" />,
  error: <AlertCircle className="w-5 h-5" />,
};

// ─── Alert ──────────────────────────────────────────────────────────────────

function Alert({
  variant = 'info',
  title,
  description,
  dismissible = false,
  onDismiss,
  className,
  children,
  icon,
}: AlertProps) {
  const [visible, setVisible] = React.useState(true);
  const [exiting, setExiting] = React.useState(false);

  function handleDismiss() {
    setExiting(true);
    setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, 200);
  }

  if (!visible) return null;

  const styles = variantStyles[variant];
  const IconElement = icon !== undefined ? icon : defaultIcons[variant];

  return (
    <div
      role="alert"
      className={cn(
        'rounded-2xl border shadow-sm transition-all duration-200',
        styles.container,
        exiting ? 'opacity-0 -translate-y-2 scale-[0.98]' : 'opacity-100 translate-y-0 scale-100',
        className
      )}
    >
      <div className="flex items-start gap-3 p-4">
        {/* Icon */}
        {IconElement && (
          <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0', styles.icon)}>
            {IconElement}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0 pt-0.5">
          {title && (
            <p className={cn('text-sm font-semibold', styles.title)}>
              {title}
            </p>
          )}
          {description && (
            <p className={cn('text-xs mt-0.5', styles.description)}>
              {description}
            </p>
          )}
          {children && (
            <div className={cn('mt-1 text-xs', styles.description)}>
              {children}
            </div>
          )}
        </div>

        {/* Close button */}
        {dismissible && (
          <button
            onClick={handleDismiss}
            className={cn('flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-colors', styles.close)}
            aria-label="Dismiss alert"
          >
            <X className="w-3.5 h-3.5 opacity-60" />
          </button>
        )}
      </div>
    </div>
  );
}

Alert.displayName = 'Alert';

// ─── Convenience variants ───────────────────────────────────────────────────

function AlertInfo(props: Omit<AlertProps, 'variant'>) {
  return <Alert variant="info" {...props} />;
}
AlertInfo.displayName = 'AlertInfo';

function AlertSuccess(props: Omit<AlertProps, 'variant'>) {
  return <Alert variant="success" {...props} />;
}
AlertSuccess.displayName = 'AlertSuccess';

function AlertWarning(props: Omit<AlertProps, 'variant'>) {
  return <Alert variant="warning" {...props} />;
}
AlertWarning.displayName = 'AlertWarning';

function AlertError(props: Omit<AlertProps, 'variant'>) {
  return <Alert variant="error" {...props} />;
}
AlertError.displayName = 'AlertError';

export { Alert, AlertInfo, AlertSuccess, AlertWarning, AlertError };
export type { AlertProps, AlertVariant };
