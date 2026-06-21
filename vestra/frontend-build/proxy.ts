import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

export const proxy = createMiddleware(routing);

export const config = {
  matcher: [
    '/((?!api|_next|_next/static|_next/image|icons|screenshots|favicon.ico|manifest.json|sw.js|robots.txt|sitemap.xml).*)',
  ],
};
