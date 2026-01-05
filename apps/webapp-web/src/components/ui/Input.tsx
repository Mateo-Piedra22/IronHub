'use client';

import { forwardRef, InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { Search, Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

// Base Input
export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    hint?: string;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
    ({ className, label, error, hint, leftIcon, rightIcon, id, ...props }, ref) => {
        const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

        return (
            <div className="space-y-1.5">
                {label && (
                    <label htmlFor={inputId} className="block text-sm font-medium text-neutral-300">
                        {label}
                    </label>
                )}
                <div className="relative">
                    {leftIcon && (
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500">
                            {leftIcon}
                        </div>
                    )}
                    <input
                        ref={ref}
                        id={inputId}
                        className={cn(
                            'w-full px-4 py-3 rounded-xl',
                            'bg-neutral-900 border border-neutral-800',
                            'text-white placeholder-neutral-500',
                            'focus:outline-none focus:ring-2 focus:ring-iron-500/50 focus:border-iron-500',
                            'transition-all duration-200',
                            'disabled:opacity-50 disabled:cursor-not-allowed',
                            leftIcon && 'pl-10',
                            rightIcon && 'pr-10',
                            error && 'border-danger-500 focus:ring-danger-500/50 focus:border-danger-500',
                            className
                        )}
                        {...props}
                    />
                    {rightIcon && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500">
                            {rightIcon}
                        </div>
                    )}
                </div>
                {error && (
                    <p className="text-sm text-danger-400">{error}</p>
                )}
                {hint && !error && (
                    <p className="text-sm text-neutral-500">{hint}</p>
                )}
            </div>
        );
    }
);

Input.displayName = 'Input';

// Search Input variant
export interface SearchInputProps extends Omit<InputProps, 'leftIcon'> {
    onSearch?: (value: string) => void;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
    ({ onSearch, onChange, ...props }, ref) => {
        return (
            <Input
                ref={ref}
                type="search"
                leftIcon={<Search className="w-4 h-4" />}
                placeholder="Buscar..."
                onChange={(e) => {
                    onChange?.(e);
                    onSearch?.(e.target.value);
                }}
                {...props}
            />
        );
    }
);

SearchInput.displayName = 'SearchInput';

// Password Input with toggle
export const PasswordInput = forwardRef<HTMLInputElement, Omit<InputProps, 'type' | 'rightIcon'>>(
    (props, ref) => {
        const [show, setShow] = useState(false);

        return (
            <Input
                ref={ref}
                type={show ? 'text' : 'password'}
                rightIcon={
                    <button
                        type="button"
                        onClick={() => setShow(!show)}
                        className="p-1 hover:text-white transition-colors"
                        tabIndex={-1}
                    >
                        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                }
                {...props}
            />
        );
    }
);

PasswordInput.displayName = 'PasswordInput';

// Textarea
export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
    label?: string;
    error?: string;
    hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
    ({ className, label, error, hint, id, ...props }, ref) => {
        const inputId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;

        return (
            <div className="space-y-1.5">
                {label && (
                    <label htmlFor={inputId} className="block text-sm font-medium text-neutral-300">
                        {label}
                    </label>
                )}
                <textarea
                    ref={ref}
                    id={inputId}
                    className={cn(
                        'w-full px-4 py-3 rounded-xl resize-y min-h-[100px]',
                        'bg-neutral-900 border border-neutral-800',
                        'text-white placeholder-neutral-500',
                        'focus:outline-none focus:ring-2 focus:ring-iron-500/50 focus:border-iron-500',
                        'transition-all duration-200',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        error && 'border-danger-500 focus:ring-danger-500/50 focus:border-danger-500',
                        className
                    )}
                    {...props}
                />
                {error && (
                    <p className="text-sm text-danger-400">{error}</p>
                )}
                {hint && !error && (
                    <p className="text-sm text-neutral-500">{hint}</p>
                )}
            </div>
        );
    }
);

Textarea.displayName = 'Textarea';

// Select
export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    error?: string;
    options: { value: string | number; label: string; disabled?: boolean }[];
    placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
    ({ className, label, error, options, placeholder, id, ...props }, ref) => {
        const inputId = id || `select-${Math.random().toString(36).substr(2, 9)}`;

        return (
            <div className="space-y-1.5">
                {label && (
                    <label htmlFor={inputId} className="block text-sm font-medium text-neutral-300">
                        {label}
                    </label>
                )}
                <select
                    ref={ref}
                    id={inputId}
                    className={cn(
                        'w-full px-4 py-3 rounded-xl appearance-none',
                        'bg-neutral-900 border border-neutral-800',
                        'text-white',
                        'focus:outline-none focus:ring-2 focus:ring-iron-500/50 focus:border-iron-500',
                        'transition-all duration-200',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        'cursor-pointer',
                        // Custom arrow
                        'bg-no-repeat bg-[length:16px_16px] bg-[right_12px_center]',
                        "bg-[url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2371717a'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E\")]",
                        'pr-10',
                        error && 'border-danger-500 focus:ring-danger-500/50 focus:border-danger-500',
                        className
                    )}
                    {...props}
                >
                    {placeholder && (
                        <option value="" disabled>
                            {placeholder}
                        </option>
                    )}
                    {options.map((option) => (
                        <option key={option.value} value={option.value} disabled={option.disabled}>
                            {option.label}
                        </option>
                    ))}
                </select>
                {error && (
                    <p className="text-sm text-danger-400">{error}</p>
                )}
            </div>
        );
    }
);

Select.displayName = 'Select';

// Checkbox
export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
    label: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
    ({ className, label, id, ...props }, ref) => {
        const inputId = id || `checkbox-${Math.random().toString(36).substr(2, 9)}`;

        return (
            <label htmlFor={inputId} className="flex items-center gap-3 cursor-pointer group">
                <input
                    ref={ref}
                    type="checkbox"
                    id={inputId}
                    className={cn(
                        'w-5 h-5 rounded-md',
                        'bg-neutral-900 border border-neutral-700',
                        'text-iron-500',
                        'focus:outline-none focus:ring-2 focus:ring-iron-500/50',
                        'transition-all duration-200',
                        'cursor-pointer',
                        'checked:bg-iron-500 checked:border-iron-500',
                        className
                    )}
                    {...props}
                />
                <span className="text-sm text-neutral-300 group-hover:text-white transition-colors">
                    {label}
                </span>
            </label>
        );
    }
);

Checkbox.displayName = 'Checkbox';

export default Input;
