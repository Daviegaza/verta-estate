import { getRequestConfig } from 'next-intl/server';
import { routing } from './routing';

type ValidLocale = (typeof routing.locales)[number];

export default getRequestConfig(async ({ requestLocale }) => {
  let locale: ValidLocale = routing.defaultLocale;

  const requested = await requestLocale;

  if (requested && (routing.locales as readonly string[]).includes(requested)) {
    locale = requested as ValidLocale;
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
