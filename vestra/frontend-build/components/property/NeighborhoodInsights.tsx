'use client'

import { useMemo } from 'react'
import {
  School, ShoppingBag, Bus, Building2, Trees, Shield,
  TrendingUp, TrendingDown, MapPin, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NeighborhoodData {
  city: string
  area: string
  avgPricePerSqm: number
  priceTrend: 'up' | 'down' | 'stable'
  priceTrendPct: number
  safetyScore: number // 0-100
  amenities: {
    schools: number
    hospitals: number
    shopping: number
    transport: number
    parks: number
  }
  developmentScore: number // 0-100
  rentalDemand: 'high' | 'medium' | 'low'
  appreciationForecast: number // annual %
}

interface NeighborhoodInsightsProps {
  data: NeighborhoodData
  className?: string
}

const ScoreBar = ({ score, label, color = 'emerald' }: { score: number; label: string; color?: string }) => (
  <div className="space-y-1.5">
    <div className="flex justify-between text-xs">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className={cn(
        'font-semibold',
        score >= 70 ? `text-${color}-600 dark:text-${color}-400` :
        score >= 40 ? 'text-amber-600 dark:text-amber-400' :
        'text-red-600 dark:text-red-400',
      )}>{score}/100</span>
    </div>
    <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
      <div
        className={cn(
          'h-full rounded-full transition-all duration-1000 ease-out',
          score >= 70 ? `bg-${color}-500` :
          score >= 40 ? 'bg-amber-500' :
          'bg-red-500',
        )}
        style={{ width: `${score}%` }}
      />
    </div>
  </div>
)

const DemandBadge = ({ level }: { level: 'high' | 'medium' | 'low' }) => {
  const config = {
    high: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300', label: 'High Demand 🔥' },
    medium: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', label: 'Moderate' },
    low: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', label: 'Low' },
  }
  const c = config[level]
  return (
    <span className={cn('inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold', c.bg, c.text)}>
      {c.label}
    </span>
  )
}

export default function NeighborhoodInsights({ data, className }: NeighborhoodInsightsProps) {
  const amenityItems = useMemo(() => [
    { icon: School, label: 'Schools', count: data.amenities.schools, color: 'text-blue-500' },
    { icon: Building2, label: 'Hospitals', count: data.amenities.hospitals, color: 'text-red-500' },
    { icon: ShoppingBag, label: 'Shopping', count: data.amenities.shopping, color: 'text-purple-500' },
    { icon: Bus, label: 'Transport', count: data.amenities.transport, color: 'text-amber-500' },
    { icon: Trees, label: 'Parks', count: data.amenities.parks, color: 'text-emerald-500' },
  ], [data.amenities])

  const highlights = useMemo(() => {
    const items: { icon: typeof MapPin; label: string; value: string; color: string }[] = []

    if (data.safetyScore >= 70) {
      items.push({ icon: Shield, label: 'Safe Area', value: `${data.safetyScore}/100`, color: 'text-emerald-500' })
    }
    if (data.priceTrend === 'up' && data.priceTrendPct > 5) {
      items.push({ icon: TrendingUp, label: 'Fast Appreciating', value: `+${data.priceTrendPct}%`, color: 'text-emerald-500' })
    }
    if (data.developmentScore >= 60) {
      items.push({ icon: Zap, label: 'Developing Area', value: `${data.developmentScore}/100`, color: 'text-blue-500' })
    }
    if (data.rentalDemand === 'high') {
      items.push({ icon: TrendingUp, label: 'High Rental Demand', value: '🔥', color: 'text-emerald-500' })
    }

    return items
  }, [data])

  return (
    <div className={cn('space-y-6', className)}>
      {/* Location Header */}
      <div className="flex items-center gap-2">
        <MapPin className="w-5 h-5 text-emerald-500" />
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            {data.area}, {data.city}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">Neighborhood Insights</p>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Avg Price/sqm</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            KES {data.avgPricePerSqm.toLocaleString()}
          </p>
          <div className="flex items-center gap-1 mt-1">
            {data.priceTrend === 'up' ? (
              <TrendingUp className="w-3 h-3 text-emerald-500" />
            ) : data.priceTrend === 'down' ? (
              <TrendingDown className="w-3 h-3 text-red-500" />
            ) : null}
            <span className={cn(
              'text-xs font-medium',
              data.priceTrend === 'up' && 'text-emerald-600',
              data.priceTrend === 'down' && 'text-red-600',
              data.priceTrend === 'stable' && 'text-gray-400',
            )}>
              {data.priceTrend === 'up' ? '+' : data.priceTrend === 'down' ? '-' : ''}{data.priceTrendPct}% YoY
            </span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Rental Demand</p>
          <div className="mt-1">
            <DemandBadge level={data.rentalDemand} />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            {data.appreciationForecast > 0 ? '+' : ''}{data.appreciationForecast}% annual appreciation forecast
          </p>
        </div>
      </div>

      {/* Scores */}
      <div className="space-y-3">
        <ScoreBar score={data.safetyScore} label="Safety" color="emerald" />
        <ScoreBar score={data.developmentScore} label="Development" color="blue" />
      </div>

      {/* Amenities */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Nearby Amenities</h4>
        <div className="grid grid-cols-5 gap-2">
          {amenityItems.map((item) => (
            <div
              key={item.label}
              className="text-center p-2 rounded-xl bg-gray-50 dark:bg-gray-800/50
                border border-gray-100 dark:border-gray-700/50
                hover:border-emerald-200 dark:hover:border-emerald-800
                transition-all duration-200"
            >
              <item.icon className={cn('w-4 h-4 mx-auto mb-1', item.color)} />
              <p className="text-xs text-gray-500 dark:text-gray-400">{item.label}</p>
              <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{item.count}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Highlights */}
      {highlights.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Area Highlights</h4>
          <div className="flex flex-wrap gap-2">
            {highlights.map((h) => (
              <span
                key={h.label}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full
                  bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-800/50
                  text-xs font-medium text-emerald-700 dark:text-emerald-300"
              >
                <h.icon className={cn('w-3 h-3', h.color)} />
                {h.label}: {h.value}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Bottom note */}
      <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
        Data based on recent transactions and market analysis
      </p>
    </div>
  )
}
