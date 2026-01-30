'use client';

import { create } from 'zustand';
import { AnimatePresence, motion } from 'framer-motion';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

// Toast types
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
    id: string;
    type: ToastType;
    message: string;
    duration?: number;
    action?: {
        label: string;
        onClick: () => void;
    };
}

// Toast store
interface ToastStore {
    toasts: Toast[];
    addToast: (toast: Omit<Toast, 'id'>) => string;
    removeToast: (id: string) => void;
    clearAll: () => void;
}

export const useToastStore = create<ToastStore>((set, get) => ({
    toasts: [],
    addToast: (toast) => {
        const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        set((state) => ({
            toasts: [...state.toasts, { ...toast, id }],
        }));

        // Auto remove after duration
        const duration = toast.duration || 5000;
        if (duration > 0) {
            setTimeout(() => {
                get().removeToast(id);
            }, duration);
        }

        return id;
    },
    removeToast: (id) => {
        set((state) => ({
            toasts: state.toasts.filter((t) => t.id !== id),
        }));
    },
    clearAll: () => {
        set({ toasts: [] });
    },
}));

// Hook for easy toast creation
export function useToast() {
    const { addToast, removeToast, clearAll } = useToastStore();

    const toast = useCallback(
        (
            input:
                | string
                | {
                      title?: string;
                      description?: string;
                      variant?: ToastType;
                      duration?: number;
                      action?: Toast['action'];
                  },
            type: ToastType = 'info',
            options?: { duration?: number; action?: Toast['action'] }
        ) => {
            if (typeof input === 'string') {
                return addToast({
                    message: input,
                    type,
                    duration: options?.duration,
                    action: options?.action,
                });
            }

            const resolvedType = input.variant || type;
            const message = [input.title, input.description].filter(Boolean).join(' · ') || 'OK';
            return addToast({
                message,
                type: resolvedType,
                duration: input.duration ?? options?.duration,
                action: input.action ?? options?.action,
            });
        },
        [addToast]
    );

    const success = useCallback(
        (message: string, options?: { duration?: number; action?: Toast['action'] }) => {
            return toast(message, 'success', options);
        },
        [toast]
    );

    const error = useCallback(
        (message: string, options?: { duration?: number; action?: Toast['action'] }) => {
            return toast(message, 'error', { duration: 8000, ...options });
        },
        [toast]
    );

    const warning = useCallback(
        (message: string, options?: { duration?: number; action?: Toast['action'] }) => {
            return toast(message, 'warning', { duration: 6000, ...options });
        },
        [toast]
    );

    const info = useCallback(
        (message: string, options?: { duration?: number; action?: Toast['action'] }) => {
            return toast(message, 'info', options);
        },
        [toast]
    );

    return {
        toast,
        success,
        error,
        warning,
        info,
        dismiss: removeToast,
        clearAll,
    };
}

// Toast icon mapping
const icons = {
    success: CheckCircle2,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info,
};

const iconColors = {
    success: 'text-success-400',
    error: 'text-danger-400',
    warning: 'text-warning-400',
    info: 'text-primary-400',
};

const borderColors = {
    success: 'border-l-success-500',
    error: 'border-l-danger-500',
    warning: 'border-l-warning-500',
    info: 'border-l-primary-500',
};

// Single Toast component
function ToastItem({ toast }: { toast: Toast }) {
    const { removeToast } = useToastStore();
    const Icon = icons[toast.type];

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={cn(
                'pointer-events-auto',
                'min-w-[320px] max-w-[420px]',
                'bg-slate-900 border border-slate-800 border-l-4 rounded-xl',
                'shadow-elevated',
                'flex items-start gap-3 p-4',
                borderColors[toast.type]
            )}
            role="alert"
        >
            <Icon className={cn('w-5 h-5 mt-0.5 flex-shrink-0', iconColors[toast.type])} />
            <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-100">{toast.message}</p>
                {toast.action && (
                    <button
                        onClick={() => {
                            toast.action?.onClick();
                            removeToast(toast.id);
                        }}
                        className="mt-2 text-sm font-medium text-primary-400 hover:text-primary-300 transition-colors"
                    >
                        {toast.action.label}
                    </button>
                )}
            </div>
            <button
                onClick={() => removeToast(toast.id)}
                className="p-1 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 transition-colors flex-shrink-0"
                aria-label="Cerrar notificación"
            >
                <X className="w-4 h-4" />
            </button>
        </motion.div>
    );
}

// Toast container component - add to layout
export function ToastContainer() {
    const { toasts } = useToastStore();

    return (
        <div
            className="fixed top-4 right-4 z-[100] flex flex-col gap-3 pointer-events-none"
            aria-live="polite"
            aria-atomic="true"
        >
            <AnimatePresence mode="popLayout">
                {toasts.map((toast) => (
                    <ToastItem key={toast.id} toast={toast} />
                ))}
            </AnimatePresence>
        </div>
    );
}

// Global showToast function for non-React contexts
export function showToast(message: string, type: ToastType = 'info', duration?: number) {
    return useToastStore.getState().addToast({ message, type, duration });
}

export default ToastContainer;

