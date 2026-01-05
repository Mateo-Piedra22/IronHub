'use client';

import { cn } from '@/lib/utils';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { useState, useMemo, useCallback } from 'react';

// Column definition
export interface Column<T> {
    key: string;
    header: string;
    sortable?: boolean;
    width?: string;
    align?: 'left' | 'center' | 'right';
    render?: (row: T, index: number) => React.ReactNode;
}

// Table props
export interface DataTableProps<T> {
    data: T[];
    columns: Column<T>[];
    keyField?: string;
    loading?: boolean;
    emptyMessage?: string;
    onRowClick?: (row: T) => void;
    selectable?: boolean;
    selectedRows?: T[];
    onSelectionChange?: (selected: T[]) => void;
    pagination?: {
        page: number;
        pageSize: number;
        total: number;
        onPageChange: (page: number) => void;
        onPageSizeChange?: (size: number) => void;
    };
    className?: string;
    compact?: boolean;
}

// Sort state
type SortDirection = 'asc' | 'desc' | null;

export function DataTable<T extends object>({
    data,
    columns,
    keyField = 'id',
    loading = false,
    emptyMessage = 'No hay datos para mostrar',
    onRowClick,
    selectable = false,
    selectedRows = [],
    onSelectionChange,
    pagination,
    className,
    compact = false,
}: DataTableProps<T>) {
    const [sortKey, setSortKey] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<SortDirection>(null);

    // Handle sort
    const handleSort = useCallback((key: string) => {
        if (sortKey === key) {
            if (sortDirection === 'asc') {
                setSortDirection('desc');
            } else if (sortDirection === 'desc') {
                setSortDirection(null);
                setSortKey(null);
            } else {
                setSortDirection('asc');
            }
        } else {
            setSortKey(key);
            setSortDirection('asc');
        }
    }, [sortKey, sortDirection]);

    // Sorted data
    const sortedData = useMemo(() => {
        if (!sortKey || !sortDirection) return data;

        return [...data].sort((a, b) => {
            const aVal = (a as Record<string, unknown>)[sortKey];
            const bVal = (b as Record<string, unknown>)[sortKey];

            if (aVal === null || aVal === undefined) return 1;
            if (bVal === null || bVal === undefined) return -1;

            let comparison = 0;
            if (typeof aVal === 'string' && typeof bVal === 'string') {
                comparison = aVal.localeCompare(bVal, 'es', { sensitivity: 'base' });
            } else if (typeof aVal === 'number' && typeof bVal === 'number') {
                comparison = aVal - bVal;
            } else {
                comparison = String(aVal).localeCompare(String(bVal));
            }

            return sortDirection === 'asc' ? comparison : -comparison;
        });
    }, [data, sortKey, sortDirection]);

    // Selection handling
    const isSelected = useCallback(
        (row: T) => selectedRows.some((r) => (r as Record<string, unknown>)[keyField] === (row as Record<string, unknown>)[keyField]),
        [selectedRows, keyField]
    );

    const toggleRow = useCallback(
        (row: T) => {
            if (!onSelectionChange) return;
            if (isSelected(row)) {
                onSelectionChange(selectedRows.filter((r) => (r as Record<string, unknown>)[keyField] !== (row as Record<string, unknown>)[keyField]));
            } else {
                onSelectionChange([...selectedRows, row]);
            }
        },
        [selectedRows, onSelectionChange, isSelected, keyField]
    );

    const toggleAll = useCallback(() => {
        if (!onSelectionChange) return;
        if (selectedRows.length === data.length) {
            onSelectionChange([]);
        } else {
            onSelectionChange([...data]);
        }
    }, [data, selectedRows, onSelectionChange]);

    // Pagination
    const totalPages = pagination ? Math.ceil(pagination.total / pagination.pageSize) : 1;

    return (
        <div className={cn('overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900/50', className)}>
            {/* Table wrapper */}
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-neutral-800 bg-neutral-900/80 backdrop-blur-sm">
                            {selectable && (
                                <th className="w-12 px-4 py-3">
                                    <input
                                        type="checkbox"
                                        checked={data.length > 0 && selectedRows.length === data.length}
                                        onChange={toggleAll}
                                        className="w-4 h-4 rounded border-neutral-700 bg-neutral-900 text-iron-500 focus:ring-iron-500/50"
                                    />
                                </th>
                            )}
                            {columns.map((col) => (
                                <th
                                    key={col.key}
                                    className={cn(
                                        compact ? 'px-3 py-2' : 'px-4 py-3',
                                        'text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider',
                                        col.sortable && 'cursor-pointer select-none hover:text-white transition-colors',
                                        col.align === 'center' && 'text-center',
                                        col.align === 'right' && 'text-right'
                                    )}
                                    style={{ width: col.width }}
                                    onClick={() => col.sortable && handleSort(col.key)}
                                >
                                    <div className={cn(
                                        'flex items-center gap-1',
                                        col.align === 'center' && 'justify-center',
                                        col.align === 'right' && 'justify-end'
                                    )}>
                                        {col.header}
                                        {col.sortable && (
                                            <span className="inline-flex flex-col">
                                                <ChevronUp
                                                    className={cn(
                                                        'w-3 h-3 -mb-1',
                                                        sortKey === col.key && sortDirection === 'asc'
                                                            ? 'text-iron-400'
                                                            : 'text-neutral-600'
                                                    )}
                                                />
                                                <ChevronDown
                                                    className={cn(
                                                        'w-3 h-3 -mt-1',
                                                        sortKey === col.key && sortDirection === 'desc'
                                                            ? 'text-iron-400'
                                                            : 'text-neutral-600'
                                                    )}
                                                />
                                            </span>
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800">
                        {loading ? (
                            // Skeleton rows
                            Array.from({ length: 5 }).map((_, i) => (
                                <tr key={i}>
                                    {selectable && <td className="px-4 py-3"><div className="h-4 w-4 bg-neutral-800 rounded animate-pulse" /></td>}
                                    {columns.map((col) => (
                                        <td key={col.key} className={compact ? 'px-3 py-2' : 'px-4 py-3'}>
                                            <div className="h-4 bg-neutral-800 rounded animate-pulse" style={{ width: `${60 + Math.random() * 40}%` }} />
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : sortedData.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={columns.length + (selectable ? 1 : 0)}
                                    className="px-4 py-12 text-center text-neutral-500"
                                >
                                    {emptyMessage}
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((row, rowIndex) => (
                                <tr
                                    key={String((row as Record<string, unknown>)[keyField]) || rowIndex}
                                    className={cn(
                                        'transition-colors',
                                        onRowClick && 'cursor-pointer hover:bg-neutral-800/50',
                                        isSelected(row) && 'bg-iron-500/10'
                                    )}
                                    onClick={() => onRowClick?.(row)}
                                >
                                    {selectable && (
                                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                                            <input
                                                type="checkbox"
                                                checked={isSelected(row)}
                                                onChange={() => toggleRow(row)}
                                                className="w-4 h-4 rounded border-neutral-700 bg-neutral-900 text-iron-500 focus:ring-iron-500/50"
                                            />
                                        </td>
                                    )}
                                    {columns.map((col) => (
                                        <td
                                            key={col.key}
                                            className={cn(
                                                compact ? 'px-3 py-2 text-sm' : 'px-4 py-3',
                                                'text-neutral-300',
                                                col.align === 'center' && 'text-center',
                                                col.align === 'right' && 'text-right'
                                            )}
                                        >
                                            {col.render
                                                ? col.render(row, rowIndex)
                                                : String((row as Record<string, unknown>)[col.key] ?? '-')}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {pagination && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-800 bg-neutral-900/80">
                    <div className="text-sm text-neutral-500">
                        Mostrando {Math.min((pagination.page - 1) * pagination.pageSize + 1, pagination.total)} a{' '}
                        {Math.min(pagination.page * pagination.pageSize, pagination.total)} de {pagination.total}
                    </div>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => pagination.onPageChange(1)}
                            disabled={pagination.page <= 1}
                            className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronsLeft className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => pagination.onPageChange(pagination.page - 1)}
                            disabled={pagination.page <= 1}
                            className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="px-3 py-1 text-sm text-neutral-300">
                            {pagination.page} / {totalPages}
                        </span>
                        <button
                            onClick={() => pagination.onPageChange(pagination.page + 1)}
                            disabled={pagination.page >= totalPages}
                            className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => pagination.onPageChange(totalPages)}
                            disabled={pagination.page >= totalPages}
                            className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronsRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default DataTable;
