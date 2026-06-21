'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Home, RefreshCw, AlertTriangle, Copy, Check } from 'lucide-react'
import { useState } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const t = useTranslations()
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    console.error('Page error:', error)
  }, [error])

  const errorId = error.digest || crypto.randomUUID?.() || 'unknown'
  const isOffline = error.message?.includes('fetch') || error.message?.includes('network')

  const copyErrorId = async () => {
    await navigator.clipboard.writeText(errorId)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="text-center max-w-lg animate-fade-in-up">
        {/* Error Icon */}
        <div className="mb-8 inline-flex items-center justify-center w-24 h-24
          rounded-full bg-red-50 dark:bg-red-950/30 animate-scale-in">
          <AlertTriangle className="w-10 h-10 text-red-500 dark:text-red-400" />
        </div>

        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
          {isOffline
            ? (t('error.offline') || 'Connection Lost')
            : (t('error.title') || 'Something went wrong')}
        </h1>

        <p className="text-gray-500 dark:text-gray-400 mb-6 leading-relaxed">
          {isOffline
            ? (t('error.offlineDescription') || 'Please check your internet connection and try again.')
            : (t('error.description') || "We've encountered an unexpected error. Our team has been notified.")}
        </p>

        {/* Error ID for support */}
        <div className="mb-8 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl inline-block">
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">
            {t('error.referenceId') || 'Reference ID'}
          </p>
          <div className="flex items-center gap-2">
            <code className="text-sm text-gray-600 dark:text-gray-300 font-mono">{errorId}</code>
            <button
              onClick={copyErrorId}
              className="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700
                transition-colors duration-200"
              title="Copy error ID"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-500" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-gray-400" />
              )}
            </button>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={reset}
            className="btn-premium inline-flex items-center justify-center gap-2 px-6 py-3
              bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl
              shadow-lg shadow-emerald-500/25 transition-all duration-300"
          >
            <RefreshCw className="w-4 h-4" />
            {t('error.tryAgain') || 'Try Again'}
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-6 py-3
              border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300
              font-semibold rounded-xl hover:border-emerald-300 dark:hover:border-emerald-600
              hover:text-emerald-600 dark:hover:text-emerald-400 transition-all duration-300"
          >
            <Home className="w-4 h-4" />
            {t('error.goHome') || 'Back to Home'}
          </Link>
        </div>

        {/* Support link */}
        <p className="mt-8 text-sm text-gray-400 dark:text-gray-500">
          {t('error.needHelp') || 'Need help?'}{' '}
          <Link
            href="/contact"
            className="text-emerald-500 hover:text-emerald-600 dark:text-emerald-400
              underline underline-offset-2 transition-colors"
          >
            {t('error.contactSupport') || 'Contact Support'}
          </Link>
        </p>
      </div>
    </div>
  )
}
