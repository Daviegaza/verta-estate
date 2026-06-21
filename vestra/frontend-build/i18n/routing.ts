import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'sw'],
  defaultLocale: 'en',
  localePrefix: 'as-needed',
  localeDetection: true,
});
