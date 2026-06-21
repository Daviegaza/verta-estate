'use client'

import { useState, useMemo, useEffect } from 'react'
import { TrendingUp, TrendingDown, Home, Wallet, Percent, Calendar } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/utils'

interface ROICalculatorProps {
  /** Current property price in KES */
  defaultPrice?: number
  /** Estimated monthly rent in KES */
  defaultRent?: number
  /** Down payment percentage */
  defaultDownPayment?: number
  className?: string
  onCalculate?: (result: ROIResult) => void
}

interface ROIResult {
  purchasePrice: number
  downPayment: number
  loanAmount: number
  monthlyMortgage: number
  monthlyRent: number
  monthlyExpenses: number
  monthlyCashflow: number
  annualCashflow: number
  cashOnCash: number
  capRate: number
  fiveYearReturn: number
  breakEvenMonths: number
  totalROI: number
}

const DEFAULT_INTEREST_RATE = 13.5 // Kenya mortgage rate
const DEFAULT_LOAN_TERM = 20 // years
const DEFAULT_EXPENSE_RATIO = 0.35 // 35% of rent goes to expenses

export default function ROICalculator({
  defaultPrice = 5_000_000,
  defaultRent = 40_000,
  defaultDownPayment = 20,
  className,
  onCalculate,
}: ROICalculatorProps) {
  const [price, setPrice] = useState(defaultPrice)
  const [monthlyRent, setMonthlyRent] = useState(defaultRent)
  const [downPaymentPct, setDownPaymentPct] = useState(defaultDownPayment)
  const [interestRate, setInterestRate] = useState(DEFAULT_INTEREST_RATE)
  const [loanTerm, setLoanTerm] = useState(DEFAULT_LOAN_TERM)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [animateResults, setAnimateResults] = useState(false)

  const result = useMemo((): ROIResult => {
    const downPayment = (price * downPaymentPct) / 100
    const loanAmount = price - downPayment
    const monthlyRate = interestRate / 100 / 12
    const numPayments = loanTerm * 12

    // Monthly mortgage payment (amortizing)
    const monthlyMortgage =
      loanAmount > 0
        ? (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
          (Math.pow(1 + monthlyRate, numPayments) - 1)
        : 0

    const monthlyExpenses = monthlyRent * DEFAULT_EXPENSE_RATIO
    const monthlyCashflow = monthlyRent - monthlyMortgage - monthlyExpenses
    const annualCashflow = monthlyCashflow * 12
    const cashOnCash = downPayment > 0 ? (annualCashflow / downPayment) * 100 : 0
    const capRate = price > 0 ? ((monthlyRent * 12 * (1 - DEFAULT_EXPENSE_RATIO)) / price) * 100 : 0
    const fiveYearReturn = downPayment > 0 ? ((annualCashflow * 5) / downPayment) * 100 : 0
    const breakEvenMonths = monthlyCashflow > 0 ? Math.ceil(downPayment / monthlyCashflow) : Infinity
    const totalROI = downPayment > 0 ? ((annualCashflow * 10) / downPayment) * 100 : 0

    return {
      purchasePrice: price,
      downPayment,
      loanAmount,
      monthlyMortgage,
      monthlyRent,
      monthlyExpenses,
      monthlyCashflow,
      annualCashflow,
      cashOnCash,
      capRate,
      fiveYearReturn,
      breakEvenMonths,
      totalROI,
    }
  }, [price, monthlyRent, downPaymentPct, interestRate, loanTerm])

  useEffect(() => {
    setAnimateResults(true)
    const t = setTimeout(() => setAnimateResults(false), 500)
    return () => clearTimeout(t)
  }, [result])

  useEffect(() => {
    onCalculate?.(result)
  }, [result, onCalculate])

  const isProfitable = result.monthlyCashflow > 0
  const isExcellent = result.cashOnCash > 12

  return (
    <div className={cn('space-y-6', className)}>
      {/* Inputs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            Purchase Price (KES)
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium text-sm">KES</span>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(Number(e.target.value) || 0)}
              className="w-full pl-12 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700
                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500
                transition-all duration-200 text-sm"
              min={500_000}
              step={100_000}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            Monthly Rent (KES)
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium text-sm">KES</span>
            <input
              type="number"
              value={monthlyRent}
              onChange={(e) => setMonthlyRent(Number(e.target.value) || 0)}
              className="w-full pl-12 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700
                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500
                transition-all duration-200 text-sm"
              min={5_000}
              step={1_000}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            Down Payment (%)
          </label>
          <input
            type="range"
            value={downPaymentPct}
            onChange={(e) => setDownPaymentPct(Number(e.target.value))}
            min={5}
            max={100}
            step={5}
            className="w-full mt-2 accent-emerald-500"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>5%</span>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">{downPaymentPct}%</span>
            <span>100%</span>
          </div>
        </div>
      </div>

      {/* Advanced Toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-sm text-emerald-600 dark:text-emerald-400 hover:underline
          font-medium transition-colors duration-200"
      >
        {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Options'}
      </button>

      {showAdvanced && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-fade-in-up">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Interest Rate (%)
            </label>
            <input
              type="number"
              value={interestRate}
              onChange={(e) => setInterestRate(Number(e.target.value) || 0)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700
                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 text-sm"
              min={5}
              max={25}
              step={0.1}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Loan Term (years)
            </label>
            <select
              value={loanTerm}
              onChange={(e) => setLoanTerm(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700
                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 text-sm"
            >
              {[5, 10, 15, 20, 25, 30].map((y) => (
                <option key={y} value={y}>{y} years</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Results */}
      <div className={cn(
        'grid grid-cols-2 lg:grid-cols-4 gap-4',
        animateResults && 'animate-fade-in-up',
      )}>
        {/* Monthly Cashflow */}
        <div className={cn(
          'p-4 rounded-2xl border transition-all duration-300',
          isProfitable
            ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800'
            : 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800',
        )}>
          <div className="flex items-center gap-2 mb-2">
            <Wallet className={cn(
              'w-4 h-4',
              isProfitable ? 'text-emerald-600' : 'text-red-500',
            )} />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Monthly Cashflow</span>
          </div>
          <p className={cn(
            'text-xl font-bold',
            isProfitable ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-600 dark:text-red-400',
          )}>
            {isProfitable ? '+' : ''}{formatCurrency(Math.round(result.monthlyCashflow))}
          </p>
          <div className="flex items-center gap-1 mt-1">
            {isProfitable ? (
              <TrendingUp className="w-3 h-3 text-emerald-500" />
            ) : (
              <TrendingDown className="w-3 h-3 text-red-500" />
            )}
            <span className="text-xs text-gray-400">per month</span>
          </div>
        </div>

        {/* Cash on Cash Return */}
        <div className="p-4 rounded-2xl border border-gray-200 dark:border-gray-700
          bg-white dark:bg-gray-800/50 transition-all duration-300">
          <div className="flex items-center gap-2 mb-2">
            <Percent className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Cash-on-Cash</span>
          </div>
          <p className={cn(
            'text-xl font-bold',
            isExcellent ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-900 dark:text-gray-100',
          )}>
            {result.cashOnCash.toFixed(1)}%
          </p>
          <span className="text-xs text-gray-400">
            {isExcellent ? 'Excellent return' : isProfitable ? 'Good return' : 'Negative return'}
          </span>
        </div>

        {/* Cap Rate */}
        <div className="p-4 rounded-2xl border border-gray-200 dark:border-gray-700
          bg-white dark:bg-gray-800/50 transition-all duration-300">
          <div className="flex items-center gap-2 mb-2">
            <Home className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Cap Rate</span>
          </div>
          <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {result.capRate.toFixed(1)}%
          </p>
          <span className="text-xs text-gray-400">
            {result.capRate > 8 ? 'Above market avg' : 'Below market avg'}
          </span>
        </div>

        {/* Break Even */}
        <div className="p-4 rounded-2xl border border-gray-200 dark:border-gray-700
          bg-white dark:bg-gray-800/50 transition-all duration-300">
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Break Even</span>
          </div>
          <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {result.breakEvenMonths === Infinity ? 'N/A' : `${result.breakEvenMonths} mo`}
          </p>
          <span className="text-xs text-gray-400">
            {result.breakEvenMonths === Infinity
              ? 'Not with current cashflow'
              : `${(result.breakEvenMonths / 12).toFixed(1)} years`}
          </span>
        </div>
      </div>

      {/* Detailed Breakdown */}
      <div className="p-5 rounded-2xl border border-gray-200 dark:border-gray-700
        bg-gray-50/50 dark:bg-gray-800/30">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Detailed Breakdown</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700/50">
            <span className="text-gray-500 dark:text-gray-400">Down Payment</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">{formatCurrency(result.downPayment)}</span>
          </div>
          <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700/50">
            <span className="text-gray-500 dark:text-gray-400">Loan Amount</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">{formatCurrency(result.loanAmount)}</span>
          </div>
          <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700/50">
            <span className="text-gray-500 dark:text-gray-400">Monthly Mortgage</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">{formatCurrency(Math.round(result.monthlyMortgage))}</span>
          </div>
          <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700/50">
            <span className="text-gray-500 dark:text-gray-400">Monthly Expenses</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">{formatCurrency(Math.round(result.monthlyExpenses))}</span>
          </div>
          <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700/50">
            <span className="text-gray-500 dark:text-gray-400">Annual Cashflow</span>
            <span className={cn(
              'font-semibold',
              result.annualCashflow > 0 ? 'text-emerald-600' : 'text-red-500',
            )}>
              {result.annualCashflow > 0 ? '+' : ''}{formatCurrency(Math.round(result.annualCashflow))}
            </span>
          </div>
          <div className="flex justify-between py-1.5">
            <span className="text-gray-500 dark:text-gray-400">5-Year ROI</span>
            <span className={cn(
              'font-semibold',
              result.fiveYearReturn > 50 ? 'text-emerald-600' : 'text-gray-900 dark:text-gray-100',
            )}>
              {result.fiveYearReturn.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Verdict */}
      <div className={cn(
        'p-4 rounded-2xl border text-center',
        isExcellent
          ? 'bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/20 dark:to-teal-950/20 border-emerald-200 dark:border-emerald-800'
          : isProfitable
            ? 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800'
            : 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800',
      )}>
        <p className={cn(
          'text-sm font-semibold',
          isExcellent && 'text-emerald-700 dark:text-emerald-300',
          isProfitable && !isExcellent && 'text-blue-700 dark:text-blue-300',
          !isProfitable && 'text-amber-700 dark:text-amber-300',
        )}>
          {isExcellent
            ? '🏆 Excellent Investment — Strong positive cashflow with great returns'
            : isProfitable
              ? '👍 Good Investment — Positive cashflow, consider negotiating for better returns'
              : '⚠️ Caution — Negative monthly cashflow. Consider a larger down payment or negotiate the price'}
        </p>
      </div>
    </div>
  )
}
