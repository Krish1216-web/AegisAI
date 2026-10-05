import React from 'react';
import { Check } from 'lucide-react';

/**
 * Enterprise Checkbox Component
 */
export function Checkbox({
  checked = false,
  onChange,
  label,
  description = null,
  disabled = false,
  id,
  className = '',
}) {
  const checkboxId = id || `chk-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <label
      htmlFor={checkboxId}
      className={`inline-flex items-start gap-2.5 select-none cursor-pointer ${disabled ? 'opacity-50 pointer-events-none' : ''} ${className}`}
    >
      <div className="relative flex items-center justify-center mt-0.5">
        <input
          type="checkbox"
          id={checkboxId}
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange && onChange(e.target.checked)}
          className="sr-only peer"
        />
        <div
          className={`w-4 h-4 rounded border transition-all duration-150 flex items-center justify-center ${
            checked
              ? 'bg-cyan-500 border-cyan-500 text-black'
              : 'border-white/20 bg-[#0d1017] hover:border-white/40'
          }`}
        >
          {checked && <Check size={12} strokeWidth={3} />}
        </div>
      </div>
      {(label || description) && (
        <div className="flex flex-col">
          {label && <span className="text-xs font-medium text-slate-200">{label}</span>}
          {description && <span className="text-[11px] text-slate-400">{description}</span>}
        </div>
      )}
    </label>
  );
}

/**
 * Enterprise Switch Component
 */
export function Switch({
  checked = false,
  onChange,
  label = null,
  description = null,
  disabled = false,
  id,
  className = '',
}) {
  const switchId = id || `sw-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <label
      htmlFor={switchId}
      className={`inline-flex items-center justify-between gap-3 select-none cursor-pointer ${disabled ? 'opacity-50 pointer-events-none' : ''} ${className}`}
    >
      {(label || description) && (
        <div className="flex flex-col">
          {label && <span className="text-xs font-medium text-slate-200">{label}</span>}
          {description && <span className="text-[11px] text-slate-400">{description}</span>}
        </div>
      )}
      <div className="relative inline-flex items-center">
        <input
          type="checkbox"
          id={switchId}
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange && onChange(e.target.checked)}
          className="sr-only peer"
        />
        <div
          className={`w-9 h-5 rounded-full transition-colors duration-200 ease-in-out border ${
            checked ? 'bg-cyan-500 border-cyan-400' : 'bg-white/10 border-white/10'
          }`}
        >
          <div
            className={`w-3.5 h-3.5 rounded-full bg-white transition-transform duration-200 ease-in-out mt-[2px] ml-[2px] ${
              checked ? 'translate-x-4 bg-black' : 'translate-x-0 bg-slate-300'
            }`}
          />
        </div>
      </div>
    </label>
  );
}
