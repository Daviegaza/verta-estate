'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

interface DatePickerProps {
  value?: Date;
  onChange?: (date: Date) => void;
  minDate?: Date;
  maxDate?: Date;
  label?: string;
  className?: string;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  id?: string;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  // Returns 0=Sun, 1=Mon, ... 6=Sat
  return new Date(year, month, 1).getDay();
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate();
}

function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

function formatDateLocal(date: Date): string {
  // Kenyan format: DD/MM/YYYY
  const d = String(date.getDate()).padStart(2, '0');
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const y = date.getFullYear();
  return `${d}/${m}/${y}`;
}

function formatDateLong(date: Date): string {
  return date.toLocaleDateString('en-KE', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// ─── DatePicker ─────────────────────────────────────────────────────────────

function DatePicker({
  value,
  onChange,
  minDate,
  maxDate,
  label,
  className,
  placeholder = 'Select date...',
  disabled = false,
  required = false,
  id,
}: DatePickerProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [viewYear, setViewYear] = React.useState(value?.getFullYear() || new Date().getFullYear());
  const [viewMonth, setViewMonth] = React.useState(value?.getMonth() || new Date().getMonth());
  const [isFocused, setIsFocused] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const calendarRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const datePickerId = id || label?.toLowerCase().replace(/\s+/g, '-');

  // Close on click outside
  React.useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on Escape
  React.useEffect(() => {
    if (!isOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setIsOpen(false);
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen]);

  // Focus trap within calendar
  React.useEffect(() => {
    if (!isOpen || !calendarRef.current) return;
    const focusable = calendarRef.current.querySelector<HTMLElement>('button');
    focusable?.focus();
  }, [isOpen]);

  function goToPrevMonth() {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  }

  function goToNextMonth() {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  }

  function goToToday() {
    const today = new Date();
    setViewYear(today.getFullYear());
    setViewMonth(today.getMonth());
  }

  function isDisabled(date: Date): boolean {
    if (minDate && date < minDate) return true;
    if (maxDate && date > maxDate) return true;
    return false;
  }

  function handleSelectDate(day: number) {
    const selected = new Date(viewYear, viewMonth, day);
    if (isDisabled(selected)) return;
    onChange?.(selected);
    setIsOpen(false);
  }

  function handleInputFocus() {
    if (!disabled) setIsOpen(true);
  }

  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth);
  // Convert Sunday=0 to Monday=1 ... Saturday=6, Sunday=7
  const startOffset = firstDay === 0 ? 6 : firstDay - 1;

  const today = new Date();

  return (
    <div ref={containerRef} className={cn('w-full relative', className)}>
      {label && (
        <label
          htmlFor={datePickerId}
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5"
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      {/* Input trigger */}
      <div className="relative">
        <input
          ref={inputRef}
          id={datePickerId}
          type="text"
          readOnly
          value={value ? formatDateLocal(value) : ''}
          placeholder={placeholder}
          disabled={disabled}
          onFocus={handleInputFocus}
          className={cn(
            'w-full rounded-xl border bg-white px-4 py-2.5 pl-10 text-sm cursor-pointer',
            'text-gray-900 placeholder:text-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
            'transition-all duration-200',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            'dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 dark:disabled:bg-gray-800',
            isOpen && 'ring-2 ring-emerald-500 border-transparent',
            className
          )}
          aria-label={label || 'Date picker'}
          aria-haspopup="dialog"
          aria-expanded={isOpen}
        />
        <CalendarDays className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
      </div>

      {/* Calendar dropdown */}
      {isOpen && (
        <div
          ref={calendarRef}
          role="dialog"
          aria-label="Date picker calendar"
          className={cn(
            'absolute z-50 mt-1 w-[320px] rounded-xl border bg-white shadow-xl',
            'dark:bg-gray-900 dark:border-gray-700',
            'animate-in fade-in zoom-in-95 duration-150'
          )}
        >
          {/* Month/Year navigation */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
            <button
              onClick={goToPrevMonth}
              className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label="Previous month"
            >
              <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>

            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {MONTHS[viewMonth]} {viewYear}
            </span>

            <button
              onClick={goToNextMonth}
              className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label="Next month"
            >
              <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
          </div>

          {/* Day-of-week header */}
          <div className="grid grid-cols-7 px-4 pt-3 pb-1">
            {DAYS_OF_WEEK.map((day) => (
              <div
                key={day}
                className="text-center text-xs font-semibold text-gray-400 dark:text-gray-500 py-1"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 px-4 pb-3 gap-0.5">
            {/* Empty cells before first day */}
            {Array.from({ length: startOffset }).map((_, i) => (
              <div key={`empty-${i}`} />
            ))}

            {/* Day cells */}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const date = new Date(viewYear, viewMonth, day);
              const isDateToday = isToday(date);
              const isSelected = value ? isSameDay(date, value) : false;
              const disabled = isDisabled(date);

              return (
                <button
                  key={day}
                  onClick={() => handleSelectDate(day)}
                  disabled={disabled}
                  aria-label={`${formatDateLocal(date)}${isDateToday ? ' (today)' : ''}`}
                  aria-selected={isSelected}
                  className={cn(
                    'w-full aspect-square rounded-lg text-sm font-medium transition-all duration-100',
                    'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1',
                    disabled
                      ? 'text-gray-300 cursor-not-allowed dark:text-gray-600'
                      : isSelected
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : isDateToday
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                          : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                  )}
                >
                  {day}
                </button>
              );
            })}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 dark:border-gray-800">
            <button
              onClick={goToToday}
              className="text-xs font-medium text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300 transition-colors"
            >
              Today
            </button>

            {value && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {formatDateLong(value)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

DatePicker.displayName = 'DatePicker';

export { DatePicker };
export type { DatePickerProps };
