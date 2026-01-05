'use client';

import { forwardRef, ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'warning' | 'outline';
    size?: 'xs' | 'sm' | 'md' | 'lg';
    isLoading?: boolean;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
}

const variantClasses = {
    primary: [
        'bg-gradient-to-r from-iron-600 to-iron-500',
        'text-white font-semibold',
        'hover:shadow-glow-md hover:from-iron-500 hover:to-iron-400',
        'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none',
    ].join(' '),
    secondary: [
        'bg-neutral-800 border border-neutral-700',
        'text-neutral-200',
        'hover:bg-neutral-700 hover:border-neutral-600',
        'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
    ghost: [
        'bg-transparent',
        'text-neutral-400',
        'hover:bg-neutral-800 hover:text-white',
        'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
    outline: [
        'bg-transparent border border-neutral-700',
        'text-neutral-300',
        'hover:bg-neutral-800 hover:border-neutral-600 hover:text-white',
        'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
    danger: [
        'bg-danger-500 border border-danger-500',
        'text-white font-semibold',
        'hover:bg-danger-600 hover:border-danger-600',
        'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
    success: [
        'bg-success-500 border border-success-500',
        'text-white font-semibold',
        'hover:bg-success-600 hover:border-success-600',
        'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
    warning: [
        'bg-warning-500 border border-warning-500',
        'text-black font-semibold',
        'hover:bg-warning-600 hover:border-warning-600',
        'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
};

const sizeClasses = {
    xs: 'px-2.5 py-1.5 text-xs rounded-lg gap-1.5',
    sm: 'px-3 py-2 text-sm rounded-lg gap-2',
    md: 'px-4 py-2.5 text-sm rounded-xl gap-2',
    lg: 'px-6 py-3 text-base rounded-xl gap-2.5',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            className,
            variant = 'primary',
            size = 'md',
            isLoading = false,
            leftIcon,
            rightIcon,
            children,
            disabled,
            ...props
        },
        ref
    ) => {
        return (
            <button
                ref={ref}
                disabled={disabled || isLoading}
                className={cn(
                    'inline-flex items-center justify-center',
                    'font-medium transition-all duration-200',
                    'focus:outline-none focus-visible:ring-2 focus-visible:ring-iron-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-900',
                    variantClasses[variant],
                    sizeClasses[size],
                    className
                )}
                {...props}
            >
                {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    leftIcon
                )}
                {children && <span>{children}</span>}
                {!isLoading && rightIcon}
            </button>
        );
    }
);

Button.displayName = 'Button';

// Icon-only button variant
export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    isLoading?: boolean;
    'aria-label': string;
}

const iconSizeClasses = {
    sm: 'w-8 h-8 rounded-lg',
    md: 'w-10 h-10 rounded-xl',
    lg: 'w-12 h-12 rounded-xl',
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
    (
        {
            className,
            variant = 'ghost',
            size = 'md',
            isLoading = false,
            children,
            disabled,
            ...props
        },
        ref
    ) => {
        return (
            <button
                ref={ref}
                disabled={disabled || isLoading}
                className={cn(
                    'inline-flex items-center justify-center',
                    'transition-all duration-200',
                    'focus:outline-none focus-visible:ring-2 focus-visible:ring-iron-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-900',
                    variantClasses[variant],
                    iconSizeClasses[size],
                    className
                )}
                {...props}
            >
                {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    children
                )}
            </button>
        );
    }
);

IconButton.displayName = 'IconButton';

export default Button;
