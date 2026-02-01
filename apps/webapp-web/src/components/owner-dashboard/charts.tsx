'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';

export function ChartCard({
    title,
    subtitle,
    right,
    children,
    className,
}: {
    title: string;
    subtitle?: string;
    right?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <div className={cn('card p-5', className)}>
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="text-white font-semibold">{title}</div>
                    {subtitle ? <div className="text-xs text-slate-500 mt-1">{subtitle}</div> : null}
                </div>
                {right ? <div className="flex-shrink-0">{right}</div> : null}
            </div>
            <div className="mt-4">{children}</div>
        </div>
    );
}

export function LineChart({
    data,
    height = 140,
    strokeClassName = 'stroke-primary-400',
    fillClassName = 'fill-primary-500/15',
}: {
    data: number[];
    height?: number;
    strokeClassName?: string;
    fillClassName?: string;
}) {
    const { dLine, dArea } = useMemo(() => {
        const values = (data || []).filter((n) => Number.isFinite(n)) as number[];
        if (!values.length) return { dLine: '', dArea: '' };
        const max = Math.max(...values);
        const min = Math.min(...values);
        const range = max - min || 1;
        const pts = values.map((v, i) => {
            const x = values.length === 1 ? 0 : (i / (values.length - 1)) * 100;
            const y = (1 - (v - min) / range) * 100;
            return { x, y };
        });
        const line = pts.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ');
        const area = `${line} L 100 100 L 0 100 Z`;
        return { dLine: line, dArea: area };
    }, [data]);

    return (
        <div className="w-full">
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full" style={{ height }}>
                <path d="M 0 100 L 100 100" className="stroke-slate-800/60" fill="none" strokeWidth="1" />
                {dArea ? <path d={dArea} className={cn(fillClassName)} /> : null}
                {dLine ? <path d={dLine} className={cn(strokeClassName)} fill="none" strokeWidth="2" /> : null}
            </svg>
        </div>
    );
}

export function BarChart({
    values,
    height = 140,
    barClassName = 'fill-primary-500/60',
}: {
    values: number[];
    height?: number;
    barClassName?: string;
}) {
    const bars = useMemo(() => {
        const vals = (values || []).map((v) => (Number.isFinite(v) ? Number(v) : 0));
        const max = Math.max(1, ...vals);
        const count = Math.max(1, vals.length);
        const gap = 2;
        const totalGap = gap * (count - 1);
        const width = (100 - totalGap) / count;
        return vals.map((v, i) => {
            const x = i * (width + gap);
            const h = (v / max) * 100;
            return { x, y: 100 - h, w: width, h };
        });
    }, [values]);

    return (
        <div className="w-full">
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full" style={{ height }}>
                {bars.map((b, i) => (
                    <rect key={i} x={b.x} y={b.y} width={b.w} height={b.h} className={cn(barClassName)} rx="1" ry="1" />
                ))}
            </svg>
        </div>
    );
}

export function DonutChart({
    segments,
    size = 120,
    thickness = 14,
}: {
    segments: Array<{ label: string; value: number; className: string }>;
    size?: number;
    thickness?: number;
}) {
    const radius = (size - thickness) / 2;
    const circumference = 2 * Math.PI * radius;
    const totalRaw = segments.reduce((acc, s) => acc + (Number.isFinite(s.value) ? s.value : 0), 0);
    const total = totalRaw || 1;
    let offset = 0;
    const showEmpty = !segments.length || totalRaw <= 0;
    const legendSegments = showEmpty ? [{ label: 'Total', value: 0, className: 'stroke-slate-500' }] : segments;

    return (
        <div className="flex items-center gap-4">
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
                <circle cx={size / 2} cy={size / 2} r={radius} stroke="rgba(148,163,184,0.25)" strokeWidth={thickness} fill="none" />
                {showEmpty ? (
                    <text x={size / 2} y={size / 2 + 4} textAnchor="middle" className="fill-slate-400" fontSize="12">
                        0
                    </text>
                ) : null}
                {segments.map((s) => {
                    const v = Number.isFinite(s.value) ? s.value : 0;
                    const dash = (v / total) * circumference;
                    const dasharray = `${dash} ${circumference - dash}`;
                    const dashoffset = -offset;
                    offset += dash;
                    return (
                        <circle
                            key={s.label}
                            cx={size / 2}
                            cy={size / 2}
                            r={radius}
                            strokeWidth={thickness}
                            fill="none"
                            strokeLinecap="butt"
                            className={cn(s.className)}
                            strokeDasharray={dasharray}
                            strokeDashoffset={dashoffset}
                            transform={`rotate(-90 ${size / 2} ${size / 2})`}
                        />
                    );
                })}
            </svg>
            <div className="space-y-1">
                {legendSegments.map((s) => (
                    <div key={s.label} className="flex items-center gap-2 text-sm">
                        <div className={cn('w-2.5 h-2.5 rounded-full', s.className.replace('stroke-', 'bg-'))} />
                        <div className="text-slate-300">{s.label}</div>
                        <div className="text-slate-500">{Number.isFinite(s.value) ? s.value : 0}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export function HeatmapTable({
    cohorts,
}: {
    cohorts: Array<{ cohort: string; values: number[] }>;
}) {
    const computedCols = useMemo(() => {
        let maxCols = 0;
        for (const c of cohorts || []) {
            maxCols = Math.max(maxCols, Array.isArray(c.values) ? c.values.length : 0);
        }
        return maxCols;
    }, [cohorts]);
    const cols = (cohorts || []).length && computedCols > 0 ? computedCols : 6;
    const cohortsSafe = (cohorts || []).length && computedCols > 0 ? cohorts : [{ cohort: '—', values: Array.from({ length: cols }).map(() => NaN) }];

    const cellClass = (v: number) => {
        if (!Number.isFinite(v)) return 'bg-slate-900/50 text-slate-500';
        if (v >= 0.8) return 'bg-emerald-500/20 text-emerald-200';
        if (v >= 0.6) return 'bg-emerald-500/10 text-emerald-200';
        if (v >= 0.4) return 'bg-primary-500/15 text-primary-200';
        if (v >= 0.2) return 'bg-yellow-500/10 text-yellow-200';
        return 'bg-red-500/10 text-red-200';
    };

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
                <thead>
                    <tr className="text-slate-500">
                        <th className="text-left font-medium py-2 pr-3">Cohorte</th>
                        {Array.from({ length: cols }).map((_, i) => (
                            <th key={i} className="text-left font-medium py-2 px-2">
                                M{i}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {cohortsSafe.map((c) => (
                        <tr key={c.cohort} className="border-t border-slate-800/60">
                            <td className="py-2 pr-3 text-slate-300">{c.cohort}</td>
                            {Array.from({ length: cols }).map((_, i) => {
                                const v = Array.isArray(c.values) ? Number(c.values[i]) : NaN;
                                const pct = Number.isFinite(v) ? `${Math.round(v * 100)}%` : '-';
                                return (
                                    <td key={i} className="py-2 px-2">
                                        <div className={cn('rounded-md px-2 py-1 inline-flex min-w-[44px] justify-center', cellClass(v))}>{pct}</div>
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
