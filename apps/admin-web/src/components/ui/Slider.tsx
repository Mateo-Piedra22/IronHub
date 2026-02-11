"use client";

import { useState, useRef, useEffect } from "react";

interface SliderProps {
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
  step?: number;
  disabled?: boolean;
  showValue?: boolean;
  label?: string;
  className?: string;
  orientation?: "horizontal" | "vertical";
  size?: "sm" | "md" | "lg";
  color?: "primary" | "secondary" | "success" | "warning" | "danger";
}

export function Slider({
  min,
  max,
  value,
  onChange,
  step = 1,
  disabled = false,
  showValue = true,
  label,
  className = "",
  orientation = "horizontal",
  size = "md",
  color = "primary"
}: SliderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [currentValue, setCurrentValue] = useState(value);
  const sliderRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setCurrentValue(value);
  }, [value]);

  const getColorClasses = () => {
    const colorMap = {
      primary: {
        track: "bg-primary-500",
        thumb: "bg-primary-500 hover:bg-primary-600 border-primary-600",
        range: "bg-primary-500"
      },
      secondary: {
        track: "bg-slate-500",
        thumb: "bg-slate-500 hover:bg-slate-600 border-slate-600",
        range: "bg-slate-500"
      },
      success: {
        track: "bg-green-500",
        thumb: "bg-green-500 hover:bg-green-600 border-green-600",
        range: "bg-green-500"
      },
      warning: {
        track: "bg-yellow-500",
        thumb: "bg-yellow-500 hover:bg-yellow-600 border-yellow-600",
        range: "bg-yellow-500"
      },
      danger: {
        track: "bg-red-500",
        thumb: "bg-red-500 hover:bg-red-600 border-red-600",
        range: "bg-red-500"
      }
    };
    return colorMap[color];
  };

  const getSizeClasses = () => {
    const sizeMap = {
      sm: {
        track: orientation === "horizontal" ? "h-1" : "w-1",
        thumb: "w-3 h-3",
        container: orientation === "horizontal" ? "h-6" : "w-6"
      },
      md: {
        track: orientation === "horizontal" ? "h-2" : "w-2",
        thumb: "w-4 h-4",
        container: orientation === "horizontal" ? "h-8" : "w-8"
      },
      lg: {
        track: orientation === "horizontal" ? "h-3" : "w-3",
        thumb: "w-5 h-5",
        container: orientation === "horizontal" ? "h-10" : "w-10"
      }
    };
    return sizeMap[size];
  };

  const colorClasses = getColorClasses();
  const sizeClasses = getSizeClasses();

  const percentage = ((currentValue - min) / (max - min)) * 100;

  const handleMouseDown = (e: React.MouseEvent) => {
    if (disabled) return;
    setIsDragging(true);
    updateValue(e);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || disabled) return;
    updateValue(e);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const updateValue = (e: React.MouseEvent | MouseEvent) => {
    if (!sliderRef.current) return;

    const rect = sliderRef.current.getBoundingClientRect();
    let newValue: number;

    if (orientation === "horizontal") {
      const clientX = 'clientX' in e ? e.clientX : (e as MouseEvent).clientX;
      const x = clientX - rect.left;
      const percentage = Math.max(0, Math.min(1, x / rect.width));
      newValue = min + percentage * (max - min);
    } else {
      const clientY = 'clientY' in e ? e.clientY : (e as MouseEvent).clientY;
      const y = clientY - rect.top;
      const percentage = Math.max(0, Math.min(1, 1 - (y / rect.height)));
      newValue = min + percentage * (max - min);
    }

    // Apply step
    newValue = Math.round(newValue / step) * step;
    newValue = Math.max(min, Math.min(max, newValue));

    setCurrentValue(newValue);
    onChange(newValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    let newValue = currentValue;
    switch (e.key) {
      case "ArrowLeft":
      case "ArrowDown":
        newValue = Math.max(min, currentValue - step);
        break;
      case "ArrowRight":
      case "ArrowUp":
        newValue = Math.min(max, currentValue + step);
        break;
      case "Home":
        newValue = min;
        break;
      case "End":
        newValue = max;
        break;
      default:
        return;
    }

    e.preventDefault();
    setCurrentValue(newValue);
    onChange(newValue);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging]);

  const containerClasses = `
    relative ${sizeClasses.container} ${className}
    ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
    ${orientation === "vertical" ? "flex items-center" : ""}
  `;

  const trackClasses = `
    ${sizeClasses.track} rounded-full bg-slate-700 relative
    ${orientation === "vertical" ? "h-full" : "w-full"}
  `;

  const rangeClasses = `
    absolute ${sizeClasses.track} ${colorClasses.range} rounded-full top-0 left-0
    ${orientation === "vertical" ? "bottom-0 w-full" : "h-full"}
  `;

  const thumbClasses = `
    ${sizeClasses.thumb} ${colorClasses.thumb} rounded-full border-2 
    absolute top-1/2 transform -translate-y-1/2 shadow-lg transition-all duration-150
    ${isDragging ? "scale-110" : "hover:scale-105"}
    ${orientation === "vertical" ? "left-1/2 transform -translate-x-1/2 -translate-y-1/2" : ""}
    ${disabled ? "cursor-not-allowed" : "cursor-grab active:cursor-grabbing"}
  `;

  const thumbPosition = orientation === "vertical" 
    ? `bottom: ${percentage}%; left: 50%; transform: translateX(-50%) translateY(50%);`
    : `left: ${percentage}%; top: 50%; transform: translateX(-50%) translateY(-50%);`;

  return (
    <div className={orientation === "horizontal" ? "w-full" : "h-full"}>
      {label && (
        <div className="flex justify-between items-center mb-2">
          <label className="text-sm font-medium text-slate-300">{label}</label>
          {showValue && (
            <span className="text-sm text-slate-400">{currentValue}</span>
          )}
        </div>
      )}

      <div
        ref={sliderRef}
        className={containerClasses}
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
        tabIndex={disabled ? -1 : 0}
        role="slider"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={currentValue}
        aria-disabled={disabled}
      >
        <div className={trackClasses}>
          <div
            className={rangeClasses}
            style={
              orientation === "vertical"
                ? { height: `${percentage}%` }
                : { width: `${percentage}%` }
            }
          />
          <div
            className={thumbClasses}
            style={{ 
              ...thumbPosition,
              cursor: disabled ? "not-allowed" : isDragging ? "grabbing" : "grab"
            }}
          />
        </div>

        {/* Hidden input for form compatibility */}
        <input
          ref={inputRef}
          type="range"
          min={min}
          max={max}
          step={step}
          value={currentValue}
          onChange={(e) => {
            const newValue = Number(e.target.value);
            setCurrentValue(newValue);
            onChange(newValue);
          }}
          disabled={disabled}
          className="sr-only"
          tabIndex={-1}
        />
      </div>

      {!label && showValue && (
        <div className="text-center mt-2">
          <span className="text-sm text-slate-400">{currentValue}</span>
        </div>
      )}
    </div>
  );
}

// Range Slider component for dual-handle sliders
interface RangeSliderProps {
  min: number;
  max: number;
  value: [number, number];
  onChange: (value: [number, number]) => void;
  step?: number;
  disabled?: boolean;
  showValues?: boolean;
  label?: string;
  className?: string;
}

export function RangeSlider({
  min,
  max,
  value,
  onChange,
  step = 1,
  disabled = false,
  showValues = true,
  label,
  className = ""
}: RangeSliderProps) {
  const [isDraggingMin, setIsDraggingMin] = useState(false);
  const [isDraggingMax, setIsDraggingMax] = useState(false);
  const [currentValue, setCurrentValue] = useState<[number, number]>(value);
  const sliderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCurrentValue(value);
  }, [value]);

  const percentageMin = ((currentValue[0] - min) / (max - min)) * 100;
  const percentageMax = ((currentValue[1] - min) / (max - min)) * 100;

  const updateValue = (clientX: number, isMin: boolean) => {
    if (!sliderRef.current) return;

    const rect = sliderRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, x / rect.width));
    const newValue = min + percentage * (max - min);

    // Apply step
    const steppedValue = Math.round(newValue / step) * step;
    const clampedValue = Math.max(min, Math.min(max, steppedValue));

    let newRange: [number, number];
    if (isMin) {
      newRange = [Math.min(clampedValue, currentValue[1]), currentValue[1]];
    } else {
      newRange = [currentValue[0], Math.max(clampedValue, currentValue[0])];
    }

    setCurrentValue(newRange);
    onChange(newRange);
  };

  const handleMouseDown = (e: React.MouseEvent, isMin: boolean) => {
    if (disabled) return;
    if (isMin) {
      setIsDraggingMin(true);
    } else {
      setIsDraggingMax(true);
    }
    updateValue(e.clientX, isMin);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDraggingMin && !isDraggingMax) return;
    updateValue(e.clientX, isDraggingMin);
  };

  const handleMouseUp = () => {
    setIsDraggingMin(false);
    setIsDraggingMax(false);
  };

  useEffect(() => {
    if (isDraggingMin || isDraggingMax) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDraggingMin, isDraggingMax]);

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <div className="flex justify-between items-center mb-2">
          <label className="text-sm font-medium text-slate-300">{label}</label>
          {showValues && (
            <span className="text-sm text-slate-400">
              {currentValue[0]} - {currentValue[1]}
            </span>
          )}
        </div>
      )}

      <div
        ref={sliderRef}
        className={`relative h-8 ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        onMouseDown={(e) => {
          // Determine which handle is closer to click
          const rect = sliderRef.current?.getBoundingClientRect();
          if (!rect) return;
          
          const x = e.clientX - rect.left;
          const percentage = x / rect.width;
          const clickValue = min + percentage * (max - min);
          
          const distToMin = Math.abs(clickValue - currentValue[0]);
          const distToMax = Math.abs(clickValue - currentValue[1]);
          
          handleMouseDown(e, distToMin <= distToMax);
        }}
      >
        {/* Track */}
        <div className="absolute top-1/2 transform -translate-y-1/2 w-full h-2 bg-slate-700 rounded-full">
          {/* Range */}
          <div
            className="absolute h-2 bg-primary-500 rounded-full"
            style={{
              left: `${percentageMin}%`,
              width: `${percentageMax - percentageMin}%`
            }}
          />
        </div>

        {/* Min Handle */}
        <div
          className={`absolute top-1/2 w-4 h-4 bg-primary-500 border-2 border-primary-600 rounded-full shadow-lg transform -translate-y-1/2 -translate-x-1/2 transition-all duration-150 hover:scale-110 ${
            isDraggingMin ? "scale-110 cursor-grabbing" : "cursor-grab hover:scale-105"
          } ${disabled ? "cursor-not-allowed" : ""}`}
          style={{ left: `${percentageMin}%` }}
          onMouseDown={(e) => {
            e.stopPropagation();
            handleMouseDown(e, true);
          }}
        />

        {/* Max Handle */}
        <div
          className={`absolute top-1/2 w-4 h-4 bg-primary-500 border-2 border-primary-600 rounded-full shadow-lg transform -translate-y-1/2 -translate-x-1/2 transition-all duration-150 hover:scale-110 ${
            isDraggingMax ? "scale-110 cursor-grabbing" : "cursor-grab hover:scale-105"
          } ${disabled ? "cursor-not-allowed" : ""}`}
          style={{ left: `${percentageMax}%` }}
          onMouseDown={(e) => {
            e.stopPropagation();
            handleMouseDown(e, false);
          }}
        />
      </div>

      {!label && showValues && (
        <div className="flex justify-between mt-2">
          <span className="text-sm text-slate-400">{currentValue[0]}</span>
          <span className="text-sm text-slate-400">{currentValue[1]}</span>
        </div>
      )}
    </div>
  );
}
