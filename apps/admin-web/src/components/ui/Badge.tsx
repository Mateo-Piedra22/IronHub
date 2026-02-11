import { cn } from "@/lib/utils";

export interface BadgeProps {
  children: React.ReactNode;
  variant?:
    | "default"
    | "secondary"
    | "outline"
    | "success"
    | "warning"
    | "danger"
    | "error"
    | "neutral";
  className?: string;
  size?: "sm" | "md" | "lg";
}

const sizeClasses: Record<NonNullable<BadgeProps["size"]>, string> = {
  sm: "px-1.5 py-0.5 text-xs",
  md: "px-2.5 py-1 text-xs",
  lg: "px-3 py-1.5 text-sm",
};

const variantClasses: Record<NonNullable<BadgeProps["variant"]>, string> = {
  default: "badge badge-neutral",
  secondary: "badge badge-neutral",
  outline: "badge border border-slate-700 text-slate-300 bg-transparent",
  success: "badge badge-success",
  warning: "badge badge-warning",
  danger: "badge badge-danger",
  error: "badge badge-danger",
  neutral: "badge badge-neutral",
};

export function Badge({ children, variant = "default", className, size = "md" }: BadgeProps) {
  return (
    <span className={cn(variantClasses[variant], sizeClasses[size], className)}>
      {children}
    </span>
  );
}

export default Badge;
