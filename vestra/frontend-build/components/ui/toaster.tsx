'use client';

import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
}

interface ToastContextValue {
  toast: (opts: Omit<Toast, 'id'>) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  warning: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((opts: Omit<Toast, 'id'>) => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    setToasts(prev => [...prev, { ...opts, id }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = (id: string) => setToasts(prev => prev.filter(t => t.id !== id));

  const value: ToastContextValue = {
    toast: addToast,
    success: (title, description) => addToast({ type: 'success', title, description }),
    error: (title, description) => addToast({ type: 'error', title, description }),
    info: (title, description) => addToast({ type: 'info', title, description }),
    warning: (title, description) => addToast({ type: 'warning', title, description }),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Toast Container — bottom-right, stacks upward */}
      <div
        className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-2.5 w-full max-w-sm pointer-events-none"
        aria-live="polite"
      >
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Trigger entrance animation
    requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300); // Wait for exit animation
    }, 4700);
    return () => clearTimeout(timer);
  }, [onClose]);

  const icons = {
    success: <CheckCircle className="w-5 h-5" />,
    error: <AlertCircle className="w-5 h-5" />,
    info: <Info className="w-5 h-5" />,
    warning: <AlertTriangle className="w-5 h-5" />,
  };

  const styles = {
    success: {
      bg: 'bg-emerald-50 border-emerald-200',
      iconBg: 'bg-emerald-100 text-emerald-600',
      title: 'text-emerald-900',
      desc: 'text-emerald-700',
      bar: 'bg-emerald-400',
    },
    error: {
      bg: 'bg-red-50 border-red-200',
      iconBg: 'bg-red-100 text-red-600',
      title: 'text-red-900',
      desc: 'text-red-700',
      bar: 'bg-red-400',
    },
    info: {
      bg: 'bg-blue-50 border-blue-200',
      iconBg: 'bg-blue-100 text-blue-600',
      title: 'text-blue-900',
      desc: 'text-blue-700',
      bar: 'bg-blue-400',
    },
    warning: {
      bg: 'bg-amber-50 border-amber-200',
      iconBg: 'bg-amber-100 text-amber-600',
      title: 'text-amber-900',
      desc: 'text-amber-700',
      bar: 'bg-amber-400',
    },
  };

  const s = styles[toast.type];

  return (
    <div
      className={cn(
        'pointer-events-auto rounded-2xl border shadow-xl backdrop-blur-sm transition-all duration-300',
        s.bg,
        visible ? 'translate-x-0 opacity-100 scale-100' : 'translate-x-full opacity-0 scale-95'
      )}
    >
      <div className="flex items-start gap-3 p-4">
        <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0', s.iconBg)}>
          {icons[toast.type]}
        </div>
        <div className="flex-1 min-w-0 pt-0.5">
          <p className={cn('text-sm font-semibold', s.title)}>{toast.title}</p>
          {toast.description && (
            <p className={cn('text-xs mt-0.5 opacity-80', s.desc)}>{toast.description}</p>
          )}
        </div>
        <button
          onClick={() => { setVisible(false); setTimeout(onClose, 300); }}
          className="flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center hover:bg-black/5 transition-colors mt-0.5"
        >
          <X className="w-3.5 h-3.5 opacity-60" />
        </button>
      </div>
      {/* Animated progress bar at bottom */}
      <div className="h-1 w-full bg-black/5 rounded-b-2xl overflow-hidden">
        <div
          className={cn('h-full rounded-full', s.bar)}
          style={{
            animation: 'toast-progress 4.7s linear forwards',
            transformOrigin: 'left',
          }}
        />
      </div>
    </div>
  );
}

export function Toaster() {
  return null;
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // No-op fallback for usage outside provider
    return {
      toast: () => {},
      success: () => {},
      error: () => {},
      info: () => {},
      warning: () => {},
    };
  }
  return ctx;
}

export { ToastContext };
