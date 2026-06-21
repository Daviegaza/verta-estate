'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Search, Heart, MessageCircle, PlusCircle, ArrowUp,
  Share2, HelpCircle, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'

interface FloatingQuickActionsProps {
  /** Whether to show the create listing button (for agents/sellers) */
  showCreateListing?: boolean
  className?: string
}

export default function FloatingQuickActions({
  showCreateListing = false,
  className,
}: FloatingQuickActionsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showScrollTop, setShowScrollTop] = useState(false)
  const [bounceAction, setBounceAction] = useState<string | null>(null)
  const router = useRouter()
  const { user } = useAuthStore()

  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 500)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Close on route change (via popstate/pushState)
  useEffect(() => {
    setIsOpen(false)
  }, [])

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleAction = (action: string) => {
    setBounceAction(action)
    setTimeout(() => setBounceAction(null), 500)

    switch (action) {
      case 'search':
        router.push('/market')
        break
      case 'favorites':
        router.push('/favorites')
        break
      case 'messages':
        router.push('/messages')
        break
      case 'create':
        router.push('/properties/new')
        break
      case 'share':
        if (navigator.share) {
          navigator.share({ title: 'VESTRA', url: window.location.href }).catch(() => {})
        }
        break
      case 'help':
        router.push('/help')
        break
    }
    setIsOpen(false)
  }

  const actions = [
    { id: 'search', icon: Search, label: 'Find Properties', show: true, color: 'bg-emerald-500 hover:bg-emerald-600' },
    { id: 'favorites', icon: Heart, label: 'Saved', show: !!user, color: 'bg-pink-500 hover:bg-pink-600' },
    { id: 'messages', icon: MessageCircle, label: 'Messages', show: !!user, color: 'bg-blue-500 hover:bg-blue-600' },
    { id: 'create', icon: PlusCircle, label: 'List Property', show: showCreateListing || user?.role === 'agent' || user?.role === 'seller', color: 'bg-amber-500 hover:bg-amber-600' },
    { id: 'share', icon: Share2, label: 'Share', show: true, color: 'bg-violet-500 hover:bg-violet-600' },
    { id: 'help', icon: HelpCircle, label: 'Help', show: true, color: 'bg-gray-500 hover:bg-gray-600' },
  ]

  return (
    <div className={cn('fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3', className)}>
      {/* Scroll to top */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="w-11 h-11 rounded-full bg-white dark:bg-gray-800 border border-gray-200
            dark:border-gray-700 shadow-lg flex items-center justify-center
            text-gray-500 hover:text-emerald-600 dark:text-gray-400 dark:hover:text-emerald-400
            transition-all duration-300 hover:shadow-xl hover:-translate-y-1
            animate-fade-in-up"
          aria-label="Scroll to top"
        >
          <ArrowUp className="w-5 h-5" />
        </button>
      )}

      {/* Action buttons */}
      <div className={cn(
        'flex flex-col-reverse items-end gap-3 transition-all duration-300',
        isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none',
      )}>
        {actions.filter((a) => a.show).reverse().map((action) => (
          <button
            key={action.id}
            onClick={() => handleAction(action.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-full text-white text-sm font-medium',
              'shadow-lg hover:shadow-xl transition-all duration-300',
              'hover:-translate-x-1',
              action.color,
              bounceAction === action.id && 'animate-scale-in',
              'animate-fade-in-left',
            )}
          >
            <action.icon className="w-4 h-4" />
            <span className="whitespace-nowrap">{action.label}</span>
          </button>
        ))}
      </div>

      {/* Main FAB */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-14 h-14 rounded-full shadow-2xl flex items-center justify-center',
          'transition-all duration-300 hover:shadow-3xl hover:scale-105',
          'bg-gradient-to-br from-emerald-500 to-emerald-600 text-white',
          'focus-visible:ring-4 focus-visible:ring-emerald-500/30',
          isOpen && 'rotate-45 bg-gray-600 dark:bg-gray-600',
        )}
        aria-label={isOpen ? 'Close quick actions' : 'Open quick actions'}
      >
        {isOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <PlusCircle className="w-6 h-6" />
        )}
      </button>

      {/* Backdrop on mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 dark:bg-black/40 backdrop-blur-sm z-[-1]
            md:hidden animate-fade-in"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}
