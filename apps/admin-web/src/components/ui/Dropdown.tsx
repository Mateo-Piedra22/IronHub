"use client";

import { useState, useRef, useEffect } from "react";
import { MoreVertical } from "lucide-react";
import { Button } from "./Button";

interface DropdownItem {
  label: string;
  onClick?: () => void;
  icon?: React.ComponentType<{ className?: string }>;
  variant?: "default" | "danger";
  disabled?: boolean;
}

interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: "left" | "right";
  width?: "auto" | "sm" | "md" | "lg";
  className?: string;
}

export function Dropdown({ trigger, items, align = "left", width = "auto", className = "" }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleItemClick = (item: DropdownItem) => {
    if (!item.disabled && item.onClick) {
      item.onClick();
      setIsOpen(false);
    }
  };

  const getWidthClasses = () => {
    switch (width) {
      case "sm": return "w-32";
      case "md": return "w-48";
      case "lg": return "w-64";
      default: return "w-auto min-w-40";
    }
  };

  const getAlignmentClasses = () => {
    return align === "right" ? "right-0" : "left-0";
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <div onClick={() => setIsOpen(!isOpen)}>
        {trigger}
      </div>

      {isOpen && (
        <div className={`absolute z-50 mt-2 ${getAlignmentClasses()} ${getWidthClasses()} rounded-xl bg-slate-800 border border-slate-700 shadow-lg ${className}`}>
          <div className="py-1">
            {items.map((item, index) => (
              <button
                key={index}
                onClick={() => handleItemClick(item)}
                disabled={item.disabled}
                className={`
                  w-full px-4 py-2 text-left text-sm flex items-center gap-3
                  transition-colors duration-150 ease-in-out
                  ${item.disabled 
                    ? 'text-slate-500 cursor-not-allowed' 
                    : item.variant === "danger"
                      ? 'text-red-400 hover:bg-red-900/20 hover:text-red-300'
                      : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }
                  ${index === 0 ? 'rounded-t-xl' : ''}
                  ${index === items.length - 1 ? 'rounded-b-xl' : ''}
                `}
              >
                {item.icon && (
                  <item.icon className="w-4 h-4 flex-shrink-0" />
                )}
                <span className="flex-1">{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Quick dropdown component for common actions
interface QuickDropdownProps {
  items: DropdownItem[];
  className?: string;
  icon?: React.ComponentType<{ className?: string }>;
  variant?: "ghost" | "secondary" | "primary" | "danger" | "success" | "warning" | "outline";
  size?: "sm" | "md" | "lg";
}

export function QuickDropdown({ 
  items, 
  className = "", 
  icon: Icon = MoreVertical,
  variant = "ghost",
  size = "sm"
}: QuickDropdownProps) {
  return (
    <Dropdown
      trigger={
        <Button variant={variant} size={size} className={className}>
          <Icon className="w-4 h-4" />
        </Button>
      }
      items={items}
      width="md"
    />
  );
}
