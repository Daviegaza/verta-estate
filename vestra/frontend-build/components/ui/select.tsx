'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown, Search, X, Check } from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps {
  options: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  hint?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  searchable?: boolean;
  id?: string;
}

// ─── Select ─────────────────────────────────────────────────────────────────

const Select = React.forwardRef<HTMLButtonElement, SelectProps>(
  (
    {
      options,
      value,
      onChange,
      placeholder = 'Select...',
      label,
      error,
      hint,
      className,
      disabled = false,
      required = false,
      searchable = false,
      id,
    },
    ref
  ) => {
    const [isOpen, setIsOpen] = React.useState(false);
    const [searchQuery, setSearchQuery] = React.useState('');
    const [highlightedIndex, setHighlightedIndex] = React.useState(-1);
    const containerRef = React.useRef<HTMLDivElement>(null);
    const listRef = React.useRef<HTMLUListElement>(null);
    const searchInputRef = React.useRef<HTMLInputElement>(null);

    const selectId = id || label?.toLowerCase().replace(/\s+/g, '-');
    const selectedOption = options.find((opt) => opt.value === value);

    const filteredOptions = searchable
      ? options.filter((opt) =>
          opt.label.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : options;

    // Close on click outside
    React.useEffect(() => {
      function handleClickOutside(e: MouseEvent) {
        if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
          setIsOpen(false);
          setSearchQuery('');
        }
      }
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Close on Escape
    React.useEffect(() => {
      if (!isOpen) return;
      function handleKey(e: KeyboardEvent) {
        if (e.key === 'Escape') {
          setIsOpen(false);
          setSearchQuery('');
        }
      }
      document.addEventListener('keydown', handleKey);
      return () => document.removeEventListener('keydown', handleKey);
    }, [isOpen]);

    // Focus search input when opening
    React.useEffect(() => {
      if (isOpen && searchable && searchInputRef.current) {
        requestAnimationFrame(() => searchInputRef.current?.focus());
      }
      if (isOpen) {
        setHighlightedIndex(-1);
      }
    }, [isOpen, searchable]);

    // Scroll highlighted item into view
    React.useEffect(() => {
      if (highlightedIndex < 0 || !listRef.current) return;
      const items = listRef.current.querySelectorAll<HTMLLIElement>('[role="option"]');
      if (items[highlightedIndex]) {
        items[highlightedIndex].scrollIntoView({ block: 'nearest' });
      }
    }, [highlightedIndex]);

    function handleSelect(opt: SelectOption) {
      if (opt.disabled) return;
      onChange?.(opt.value);
      setIsOpen(false);
      setSearchQuery('');
    }

    function handleKeyDown(e: React.KeyboardEvent) {
      if (!isOpen) {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
          e.preventDefault();
          setIsOpen(true);
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < filteredOptions.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev > 0 ? prev - 1 : filteredOptions.length - 1
          );
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < filteredOptions.length) {
            handleSelect(filteredOptions[highlightedIndex]);
          }
          break;
        case 'Tab':
          setIsOpen(false);
          setSearchQuery('');
          break;
      }
    }

    return (
      <div className="w-full" ref={containerRef}>
        {label && (
          <label
            htmlFor={selectId}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5"
          >
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}

        <div className="relative">
          <button
            ref={ref}
            id={selectId}
            type="button"
            disabled={disabled}
            aria-haspopup="listbox"
            aria-expanded={isOpen}
            aria-labelledby={label ? selectId : undefined}
            onClick={() => setIsOpen((prev) => !prev)}
            onKeyDown={handleKeyDown}
            className={cn(
              'flex w-full items-center justify-between rounded-xl border bg-white px-4 py-2.5 text-sm',
              'transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
              'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
              'dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 dark:disabled:bg-gray-800',
              error
                ? 'border-red-400 focus:ring-red-400'
                : 'border-gray-200 dark:border-gray-700',
              className
            )}
          >
            <span
              className={cn(
                'truncate',
                !selectedOption && 'text-gray-400 dark:text-gray-500'
              )}
            >
              {selectedOption ? selectedOption.label : placeholder}
            </span>
            <ChevronDown
              className={cn(
                'w-4 h-4 text-gray-400 flex-shrink-0 ml-2 transition-transform duration-200',
                isOpen && 'rotate-180'
              )}
            />
          </button>

          {/* Dropdown */}
          {isOpen && (
            <div
              className={cn(
                'absolute z-50 mt-1 w-full rounded-xl border bg-white shadow-lg',
                'dark:bg-gray-900 dark:border-gray-700',
                'animate-in fade-in zoom-in-95 duration-150',
                error ? 'border-red-400' : 'border-gray-200 dark:border-gray-700'
              )}
            >
              {searchable && (
                <div className="relative p-2 border-b border-gray-100 dark:border-gray-800">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search..."
                    className={cn(
                      'w-full rounded-lg border border-gray-200 bg-gray-50 pl-9 pr-8 py-2 text-sm',
                      'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
                      'dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100'
                    )}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setIsOpen(false);
                        setSearchQuery('');
                      }
                      e.stopPropagation();
                    }}
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                    >
                      <X className="w-3.5 h-3.5 text-gray-400" />
                    </button>
                  )}
                </div>
              )}

              <ul
                ref={listRef}
                role="listbox"
                aria-label={label || placeholder}
                className="py-1 max-h-60 overflow-y-auto"
              >
                {filteredOptions.length === 0 ? (
                  <li className="px-4 py-3 text-sm text-gray-400 text-center">
                    No options found
                  </li>
                ) : (
                  filteredOptions.map((opt, idx) => (
                    <li
                      key={opt.value}
                      role="option"
                      aria-selected={opt.value === value}
                      aria-disabled={opt.disabled}
                      className={cn(
                        'flex items-center justify-between px-4 py-2.5 text-sm cursor-pointer transition-colors',
                        'focus:outline-none',
                        opt.disabled
                          ? 'text-gray-300 cursor-not-allowed dark:text-gray-600'
                          : opt.value === value
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                            : highlightedIndex === idx
                              ? 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
                              : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
                      )}
                      onClick={() => handleSelect(opt)}
                      onMouseEnter={() => setHighlightedIndex(idx)}
                    >
                      <span>{opt.label}</span>
                      {opt.value === value && (
                        <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      )}
                    </li>
                  ))
                )}
              </ul>
            </div>
          )}
        </div>

        {error && (
          <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
            {error}
          </p>
        )}
        {hint && !error && (
          <p className="mt-1.5 text-xs text-gray-400 dark:text-gray-500">{hint}</p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export { Select };
export type { SelectOption, SelectProps };
