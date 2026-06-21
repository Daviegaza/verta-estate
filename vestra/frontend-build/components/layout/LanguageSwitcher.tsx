'use client';

import { useState, useEffect, useCallback } from 'react';
import { useLocale } from 'next-intl';
import { Globe } from 'lucide-react';
import { setCookie } from '@/lib/utils';

const LOCALES = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'sw', label: 'SW', name: 'Kiswahili' },
] as const;

export default function LanguageSwitcher() {
  const currentLocale = useLocale();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const switchLocale = useCallback(
    (newLocale: string) => {
      if (newLocale === currentLocale) return;
      localStorage.setItem('vestra_locale', newLocale);
      setCookie('NEXT_LOCALE', newLocale);
      window.location.reload();
    },
    [currentLocale]
  );

  const nextLocale = currentLocale === 'en' ? 'sw' : 'en';
  const nextLocaleData = LOCALES.find((l) => l.code === nextLocale);
  const currentLocaleData = LOCALES.find((l) => l.code === currentLocale);

  if (!mounted) {
    return (
      <button
        className="p-2 rounded-xl transition-colors text-gray-400"
        disabled
        aria-label="Switch Language"
      >
        <Globe className="w-4 h-4" />
      </button>
    );
  }

  return (
    <button
      onClick={() => switchLocale(nextLocale)}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold border border-gray-200 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:hover:border-gray-600 dark:hover:bg-gray-800 transition-all"
      title={`${nextLocaleData?.name}`}
      aria-label={`Switch language to ${nextLocaleData?.name}`}
    >
      <Globe className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
      <span className="text-gray-600 dark:text-gray-300 tracking-wide">
        {currentLocaleData?.label}
      </span>
      <span className="text-gray-400 dark:text-gray-500 text-[10px]">/</span>
      <span className="text-gray-400 dark:text-gray-500 tracking-wide">
        {nextLocaleData?.label}
      </span>
    </button>
  );
}
