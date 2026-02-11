"use client";

import { cloneElement, forwardRef, isValidElement, type ButtonHTMLAttributes, type ReactElement } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "success" | "warning" | "outline";
  size?: "xs" | "sm" | "md" | "lg";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  asChild?: boolean;
}

const variantClasses: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: cn(
    "bg-primary-600 hover:bg-primary-500 text-white font-semibold",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  ),
  secondary: cn(
    "bg-slate-800 border border-slate-700 text-slate-200",
    "hover:bg-slate-700 hover:border-slate-600",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  ),
  ghost: cn(
    "bg-transparent text-slate-400",
    "hover:bg-slate-800 hover:text-white",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  ),
  outline: cn(
    "bg-transparent border border-slate-700 text-slate-300",
    "hover:bg-slate-800 hover:border-slate-600 hover:text-white",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  ),
  danger: cn(
    "bg-danger-600/10 border border-danger-500/20 text-danger-400",
    "hover:bg-danger-600/20",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  ),
  success: cn(
    "bg-success-600/10 border border-success-500/20 text-success-400",
    "hover:bg-success-600/20",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  ),
  warning: cn(
    "bg-warning-600/10 border border-warning-500/20 text-warning-400",
    "hover:bg-warning-600/20",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  ),
};

const sizeClasses: Record<NonNullable<ButtonProps["size"]>, string> = {
  xs: "px-2.5 py-1.5 text-xs rounded-lg gap-1.5",
  sm: "px-3 py-2 text-sm rounded-lg gap-2",
  md: "px-4 py-2.5 text-sm rounded-xl gap-2",
  lg: "px-6 py-3 text-base rounded-xl gap-2.5",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      asChild = false,
      type,
      ...props
    },
    ref
  ) => {
    const resolvedClassName = cn(
      "inline-flex items-center justify-center font-medium transition-all duration-200",
      "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950",
      variantClasses[variant],
      sizeClasses[size],
      className
    );

    const resolvedChildren = (
      <>
        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : leftIcon}
        {children && <span>{children}</span>}
        {!isLoading && rightIcon}
      </>
    );

    if (asChild) {
      if (!isValidElement(children)) return null;
      type ChildProps = {
        className?: string;
        onClick?: React.MouseEventHandler<HTMLElement>;
        role?: string;
        tabIndex?: number;
        "aria-disabled"?: boolean;
        children?: React.ReactNode;
      };
      const child = children as ReactElement<ChildProps>;
      const mergedClassName = cn(resolvedClassName, child.props.className);
      return cloneElement(child, {
        className: mergedClassName,
        onClick: props.onClick ?? child.props.onClick,
        role: "button",
        tabIndex: disabled || isLoading ? -1 : 0,
        "aria-disabled": disabled || isLoading ? true : undefined,
        children: resolvedChildren,
      });
    }

    return (
      <button
        ref={ref}
        type={type ?? "button"}
        disabled={disabled || isLoading}
        className={resolvedClassName}
        {...props}
      >
        {resolvedChildren}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
