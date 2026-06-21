'use client'

import { useState, useEffect, useRef } from 'react'
import { TrendingUp, TrendingDown, Minus, MapPin, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MarketPulseItem {
  city: string
  area: string
  priceChange: number  // percentage
  status: 'hot' | 'rising' | 'stable' | 'cooling' | 'declining'
  lastUpdated: string
  avgPrice: number
  changeLabel: string
}

const DEFAULT_PULSE_DATA: MarketPulseItem[] = [
  { city: 'Nairobi', area: 'Karen', priceChange: 12.4, status: 'hot', lastUpdated: '2m ago', avgPrice: 185000, changeLabel: '+12.4% YoY' },
  { city: 'Nairobi', area: 'Kilimani', priceChange: 8.2, status: 'rising', lastUpdated: '5m ago', avgPrice: 142000, changeLabel: '+8.2% YoY' },
  { city: 'Mombasa', area: 'Nyali', priceChange: 15.1, status: 'hot', lastUpdated: '3m ago', avgPrice: 98000, changeLabel: '+15.1% YoY' },
  { city: 'Nairobi', area: 'Westlands', priceChange: -2.3, status: 'cooling', lastUpdated: '7m ago', avgPrice: 156000, changeLabel: '-2.3% YoY' },
  { city: 'Kisumu', area: 'Milimani', priceChange: 6.7, status: 'rising', lastUpdated: '4m ago', avgPrice: 72000, changeLabel: '+6.7% YoY' },
  { city: 'Nairobi', area: 'Eastlands', priceChange: 22.8, status: 'hot', lastUpdated: '1m ago', avgPrice: 45000, changeLabel: '+22.8% YoY' },
  { city: 'Nakuru', area: 'Milimani', priceChange: 4.1, status: 'stable', lastUpdated: '6m ago', avgPrice: 58000, changeLabel: '+4.1% YoY' },
  { city: 'Nairobi', area: 'Kileleshwa', priceChange: -5.2, status: 'declining', lastUpdated: '8m ago', avgPrice: 168000, changeLabel: '-5.2% YoY' },
]

export default function MarketPulseTicker() {
  const [items, setItems] = useState<MarketPulseItem[]>(DEFAULT_PULSE_DATA)
  const [isPaused, setIsPaused] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll animation
  useEffect(() => {
    if (isPaused) return

    const interval = setInterval(() => {
      if (scrollRef.current) {
        const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current
        if (scrollLeft + clientWidth >= scrollWidth) {
          scrollRef.current.scrollTo({ left: 0, behavior: 'smooth' })
        } else {
          scrollRef.current.scrollBy({ left: 1, behavior: 'smooth' })
        }
      }
    }, 50)

    return () => clearInterval(interval)
  }, [isPaused])

  const getStatusIcon = (status: MarketPulseItem['status']) => {
    switch (status) {
      case 'hot': return <TrendingUp className="w-3.5 h-3.5 text-red-500" />
      case 'rising': return <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
      case 'stable': return <Minus className="w-3.5 h-3.5 text-gray-400" />
      case 'cooling': return <TrendingDown className="w-3.5 h-3.5 text-amber-500" />
      case 'declining': return <TrendingDown className="w-3.5 h-3.5 text-red-500" />
    }
  }

  const getStatusColor = (status: MarketPulseItem['status']) => {
    switch (status) {
      case 'hot': return 'bg-red-100 dark:bg-red-950/30 border-red-200 dark:border-red-800'
      case 'rising': return 'bg-emerald-100 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800'
      case 'stable': return 'bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700'
      case 'cooling': return 'bg-amber-100 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800'
      case 'declining': return 'bg-red-100 dark:bg-red-950/30 border-red-200 dark:border-red-800'
    }
  }

  return (
    <div className="relative w-full overflow-hidden bg-gradient-to-r from-gray-50 to-white
      dark:from-gray-900 dark:to-gray-800 border-y border-gray-200 dark:border-gray-700/50">
      {/* Label */}
      <div className="absolute left-0 top-0 bottom-0 z-10 flex items-center px-4
        bg-gradient-to-r from-gray-50 dark:from-gray-900 to-transparent">
        <div className="flex items-center gap-2 pr-4 border-r border-gray-200 dark:border-gray-700">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-soft" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100 whitespace-nowrap">
            Market Pulse
          </span>
          <Clock className="w-3 h-3 text-gray-400" />
        </div>
      </div>

      {/* Scrolling content */}
      <div
        ref={scrollRef}
        className="flex overflow-x-hidden pl-36 py-2.5"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* Duplicate items for seamless loop */}
        {[...items, ...items].map((item, index) => (
          <div
            key={`${item.area}-${index}`}
            className={cn(
              'flex items-center gap-3 px-4 py-2 mx-1.5 rounded-xl border',
              'shrink-0 cursor-pointer transition-all duration-200',
              'hover:shadow-md hover:-translate-y-0.5',
              getStatusColor(item.status),
            )}
          >
            <MapPin className="w-3 h-3 text-gray-400 dark:text-gray-500" />
            <div className="text-left">
              <p className="text-xs font-semibold text-gray-900 dark:text-gray-100 whitespace-nowrap">
                {item.area}, {item.city}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                KES {item.avgPrice.toLocaleString()}/sqm
              </p>
            </div>
            <div className="flex items-center gap-1">
              {getStatusIcon(item.status)}
              <span className={cn(
                'text-xs font-bold',
                item.priceChange > 0 ? 'text-emerald-600 dark:text-emerald-400' :
                item.priceChange < 0 ? 'text-red-600 dark:text-red-400' :
                'text-gray-500',
              )}>
                {item.changeLabel}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
