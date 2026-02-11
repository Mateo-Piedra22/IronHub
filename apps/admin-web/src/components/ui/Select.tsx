"use client";

import { forwardRef, type SelectHTMLAttributes, useId } from "react";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, placeholder, id, ...props }, ref) => {
    const reactId = useId();
    const inputId = id || `select-${reactId.replace(/:/g, "")}`;

    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-slate-300">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={inputId}
          className={cn(
            "w-full px-4 py-3 rounded-xl appearance-none",
            "bg-slate-900 border border-slate-800",
            "text-white",
            "focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500",
            "transition-all duration-200",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "cursor-pointer",
            "bg-no-repeat bg-[length:16px_16px] bg-[right_12px_center]",
            "bg-[url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2371717a'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E\")]",
            "pr-10",
            error && "border-danger-500 focus:ring-danger-500/50 focus:border-danger-500",
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
        {error && <p className="text-sm text-danger-400">{error}</p>}
      </div>
    );
  }
);

Select.displayName = "Select";

export default Select;
