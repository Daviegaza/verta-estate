'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

// ─── Types ──────────────────────────────────────────────────────────────────

interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
  disabled?: boolean;
}

type TabsVariant = 'underline' | 'pills';

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
  variant?: TabsVariant;
  className?: string;
  tabClassName?: string;
  contentClassName?: string;
}

// ─── Tabs ───────────────────────────────────────────────────────────────────

function Tabs({
  tabs,
  defaultTab,
  onChange,
  variant = 'underline',
  className,
  tabClassName,
  contentClassName,
}: TabsProps) {
  const [activeTab, setActiveTab] = React.useState(defaultTab || tabs[0]?.id || '');
  const [focusedIndex, setFocusedIndex] = React.useState(-1);
  const tabListRef = React.useRef<HTMLDivElement>(null);
  const tabRefs = React.useRef<(HTMLButtonElement | null)[]>([]);

  const activeIndex = tabs.findIndex((t) => t.id === activeTab);

  React.useEffect(() => {
    if (defaultTab) setActiveTab(defaultTab);
  }, [defaultTab]);

  function handleSelect(tabId: string) {
    setActiveTab(tabId);
    onChange?.(tabId);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    const enabledTabs = tabs.filter((t) => !t.disabled);
    const currentIdx = enabledTabs.findIndex((t) => t.id === activeTab);

    let nextIdx = -1;

    switch (e.key) {
      case 'ArrowRight':
        e.preventDefault();
        nextIdx = (currentIdx + 1) % enabledTabs.length;
        break;
      case 'ArrowLeft':
        e.preventDefault();
        nextIdx = (currentIdx - 1 + enabledTabs.length) % enabledTabs.length;
        break;
      case 'Home':
        e.preventDefault();
        nextIdx = 0;
        break;
      case 'End':
        e.preventDefault();
        nextIdx = enabledTabs.length - 1;
        break;
      default:
        return;
    }

    if (nextIdx >= 0) {
      const nextTab = enabledTabs[nextIdx];
      setActiveTab(nextTab.id);
      onChange?.(nextTab.id);
      tabRefs.current[tabs.indexOf(nextTab)]?.focus();
    }
  }

  React.useEffect(() => {
    tabRefs.current = tabRefs.current.slice(0, tabs.length);
  }, [tabs.length]);

  const activeContent = tabs.find((t) => t.id === activeTab)?.content;

  return (
    <div className={cn('w-full', className)}>
      {/* Tab List */}
      <div
        ref={tabListRef}
        role="tablist"
        aria-orientation="horizontal"
        onKeyDown={handleKeyDown}
        className={cn(
          'flex',
          variant === 'underline'
            ? 'border-b border-gray-200 dark:border-gray-800 gap-0'
            : 'gap-1.5 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl',
          tabClassName
        )}
      >
        {tabs.map((tab, idx) => {
          const isActive = tab.id === activeTab;
          const isDisabled = tab.disabled;

          return (
            <button
              key={tab.id}
              ref={(el) => { tabRefs.current[idx] = el; }}
              role="tab"
              aria-selected={isActive}
              aria-disabled={isDisabled}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              disabled={isDisabled}
              onClick={() => !isDisabled && handleSelect(tab.id)}
              className={cn(
                'relative whitespace-nowrap text-sm font-medium transition-all duration-200',
                'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                variant === 'underline' && cn(
                  'px-4 py-3 -mb-px',
                  isActive
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                ),
                variant === 'pills' && cn(
                  'px-4 py-2 rounded-lg text-sm',
                  isActive
                    ? 'bg-white dark:bg-gray-900 text-emerald-600 dark:text-emerald-400 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
                ),
                isActive && variant === 'underline' && 'ring-0 focus:ring-offset-0'
              )}
            >
              {tab.label}
              {/* Animated underline indicator */}
              {variant === 'underline' && isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-500 dark:bg-emerald-400 rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className={cn('pt-4', contentClassName)}
      >
        {activeContent}
      </div>
    </div>
  );
}

Tabs.displayName = 'Tabs';

export { Tabs };
export type { Tab, TabsProps, TabsVariant };
