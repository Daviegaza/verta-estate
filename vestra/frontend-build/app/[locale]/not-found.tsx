'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Home, Search, ArrowLeft } from 'lucide-react'

export default function NotFound() {
  const t = useTranslations()

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="text-center max-w-lg animate-fade-in-up">
        {/* Animated 404 */}
        <div className="relative mb-8 inline-block">
          <div className="text-[140px] font-black leading-none select-none
            bg-gradient-to-br from-emerald-400 via-emerald-500 to-emerald-700
            bg-clip-text text-transparent animate-float-slow">
            4
            <span className="inline-block animate-pulse-soft">0</span>
            4
          </div>
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-24 h-1
            bg-gradient-to-r from-transparent via-emerald-400 to-transparent rounded-full" />
        </div>

        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
          {t('notFound.title') || 'Page Not Found'}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mb-8 leading-relaxed">
          {t('notFound.description') ||
            "The property you're looking for might have been sold, or the page may have moved. Let's get you back on track."}
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/"
            className="btn-premium inline-flex items-center justify-center gap-2 px-6 py-3
              bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl
              shadow-lg shadow-emerald-500/25 transition-all duration-300"
          >
            <Home className="w-4 h-4" />
            {t('notFound.goHome') || 'Back to Home'}
          </Link>
          <Link
            href="/market"
            className="inline-flex items-center justify-center gap-2 px-6 py-3
              border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300
              font-semibold rounded-xl hover:border-emerald-300 dark:hover:border-emerald-600
              hover:text-emerald-600 dark:hover:text-emerald-400 transition-all duration-300"
          >
            <Search className="w-4 h-4" />
            {t('notFound.browseProperties') || 'Browse Properties'}
          </Link>
        </div>

        <button
          onClick={() => window.history.back()}
          className="mt-6 inline-flex items-center gap-1.5 text-sm text-gray-400
            hover:text-emerald-500 transition-colors duration-200"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          {t('notFound.goBack') || 'Go back'}
        </button>
      </div>
    </div>
  )
}
