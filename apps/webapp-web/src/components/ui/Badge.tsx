import React from 'react';

interface BadgeProps {
    children: React.ReactNode;
    variant?: 'default' | 'secondary' | 'outline' | 'success';
    className?: string;
    size?: 'sm' | 'md' | 'lg';
}

export function Badge({ children, variant = 'default', className = '', size = 'md' }: BadgeProps) {
    const baseClasses = 'inline-flex items-center rounded-full text-xs font-medium';
    
    const sizeClasses = {
        sm: 'px-1.5 py-0.5 text-xs',
        md: 'px-2 py-1 text-xs',
        lg: 'px-3 py-1.5 text-sm'
    };
    
    const variantClasses = {
        default: 'bg-blue-500 text-white',
        secondary: 'bg-slate-700 text-slate-300',
        outline: 'border border-slate-600 text-slate-300',
        success: 'bg-green-500 text-white'
    };

    return (
        <span className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}>
            {children}
        </span>
    );
}
