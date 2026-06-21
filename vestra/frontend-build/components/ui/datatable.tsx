'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
  headerClassName?: string;
  hideOnMobile?: boolean;
}

interface DataTableProps<T extends Record<string, unknown>> {
  columns: Column<T>[];
  data: T[];
  sortable?: boolean;
  selectable?: boolean;
  onRowClick?: (row: T) => void;
  className?: string;
  emptyMessage?: string;
  getRowId?: (row: T) => string | number;
  defaultSortKey?: string;
  defaultSortDirection?: 'asc' | 'desc';
}

// ─── DataTable ──────────────────────────────────────────────────────────────

function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  sortable: globallySortable = false,
  selectable = false,
  onRowClick,
  className,
  emptyMessage = 'No data available',
  getRowId,
  defaultSortKey,
  defaultSortDirection = 'asc',
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = React.useState<string | undefined>(defaultSortKey);
  const [sortDirection, setSortDirection] = React.useState<'asc' | 'desc'>(defaultSortDirection);
  const [selectedRows, setSelectedRows] = React.useState<Set<string | number>>(new Set());

  // Sorting
  const sortedData = React.useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];

      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      let cmp = 0;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        cmp = aVal.localeCompare(bVal);
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        cmp = aVal - bVal;
      } else {
        cmp = String(aVal).localeCompare(String(bVal));
      }

      return sortDirection === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDirection]);

  function handleSort(column: Column<T>) {
    if (!globallySortable || !column.sortable) return;
    if (sortKey === column.key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(column.key);
      setSortDirection('asc');
    }
  }

  function getSortIcon(column: Column<T>) {
    if (!globallySortable || !column.sortable) return null;
    if (sortKey !== column.key) return <ChevronsUpDown className="w-3.5 h-3.5 text-gray-300" />;
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-3.5 h-3.5 text-emerald-600" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 text-emerald-600" />
    );
  }

  function toggleSelectAll() {
    if (selectedRows.size === data.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(data.map((_, i) => getRowKey(data[i], i))));
    }
  }

  function toggleRow(row: T, index: number) {
    const id = getRowKey(row, index);
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function getRowKey(row: T, index: number): string | number {
    return getRowId ? getRowId(row) : index;
  }

  const allSelected = data.length > 0 && selectedRows.size === data.length;

  return (
    <div className={cn('w-full overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800', className)}>
      <table className="w-full min-w-[600px]">
        {/* Header */}
        <thead>
          <tr className="border-b border-gray-100 dark:border-gray-800 bg-gray-50/80 dark:bg-gray-900/80">
            {selectable && (
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                  aria-label="Select all rows"
                />
              </th>
            )}
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider',
                  globallySortable && col.sortable && 'cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200',
                  col.hideOnMobile && 'hidden sm:table-cell',
                  col.headerClassName
                )}
                onClick={() => handleSort(col)}
                aria-sort={
                  sortKey === col.key
                    ? sortDirection === 'asc'
                      ? 'ascending'
                      : 'descending'
                    : undefined
                }
              >
                <div className="flex items-center gap-1.5">
                  {col.header}
                  {getSortIcon(col)}
                </div>
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {sortedData.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length + (selectable ? 1 : 0)}
                className="px-4 py-12 text-center text-sm text-gray-400 dark:text-gray-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedData.map((row, rowIdx) => {
              const rowId = getRowKey(row, rowIdx);
              const isSelected = selectedRows.has(rowId);

              return (
                <tr
                  key={rowId}
                  className={cn(
                    'transition-colors duration-150',
                    onRowClick && 'cursor-pointer',
                    isSelected
                      ? 'bg-emerald-50/50 dark:bg-emerald-900/20'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-900/50'
                  )}
                  onClick={() => onRowClick?.(row)}
                >
                  {selectable && (
                    <td className="w-10 px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleRow(row, rowIdx)}
                        className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                        aria-label={`Select row ${rowIdx + 1}`}
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        'px-4 py-3 text-sm text-gray-700 dark:text-gray-300',
                        col.hideOnMobile && 'hidden sm:table-cell',
                        col.className
                      )}
                    >
                      {col.render ? col.render(row) : String(row[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

DataTable.displayName = 'DataTable';

export { DataTable };
export type { Column, DataTableProps };
