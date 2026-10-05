import React, { forwardRef } from 'react';

/**
 * Enterprise Form Input with labels, helper text, error messages, and icon adornments
 */
export const Input = forwardRef(function Input(
  {
    label,
    helperText,
    error,
    required = false,
    leftIcon = null,
    rightIcon = null,
    className = '',
    id,
    disabled = false,
    ...props
  },
  ref
) {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={inputId} className="text-xs font-medium text-slate-300 flex items-center gap-1">
          <span>{label}</span>
          {required && <span className="text-rose-400">*</span>}
        </label>
      )}
      <div className="relative flex items-center">
        {leftIcon && (
          <span className="absolute left-3 text-slate-400 pointer-events-none shrink-0">{leftIcon}</span>
        )}
        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          className={`w-full bg-[#0d1017] border text-sm text-slate-100 rounded-lg px-3.5 py-2 transition-all duration-150 outline-none placeholder:text-slate-500 disabled:opacity-50 disabled:cursor-not-allowed ${
            leftIcon ? 'pl-9' : ''
          } ${rightIcon ? 'pr-9' : ''} ${
            error
              ? 'border-rose-500/50 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20'
              : 'border-white/10 hover:border-white/20 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20'
          } ${className}`}
          {...props}
        />
        {rightIcon && (
          <span className="absolute right-3 text-slate-400 shrink-0">{rightIcon}</span>
        )}
      </div>
      {error && <p className="text-xs text-rose-400">{error}</p>}
      {!error && helperText && <p className="text-xs text-slate-500">{helperText}</p>}
    </div>
  );
});

export const Textarea = forwardRef(function Textarea(
  {
    label,
    helperText,
    error,
    required = false,
    className = '',
    id,
    rows = 3,
    disabled = false,
    ...props
  },
  ref
) {
  const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={textareaId} className="text-xs font-medium text-slate-300 flex items-center gap-1">
          <span>{label}</span>
          {required && <span className="text-rose-400">*</span>}
        </label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        rows={rows}
        disabled={disabled}
        className={`w-full bg-[#0d1017] border text-sm text-slate-100 rounded-lg p-3 transition-all duration-150 outline-none placeholder:text-slate-500 disabled:opacity-50 disabled:cursor-not-allowed ${
          error
            ? 'border-rose-500/50 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20'
            : 'border-white/10 hover:border-white/20 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20'
        } ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-rose-400">{error}</p>}
      {!error && helperText && <p className="text-xs text-slate-500">{helperText}</p>}
    </div>
  );
});

export const Select = forwardRef(function Select(
  {
    label,
    helperText,
    error,
    required = false,
    options = [],
    children,
    className = '',
    id,
    disabled = false,
    ...props
  },
  ref
) {
  const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={selectId} className="text-xs font-medium text-slate-300 flex items-center gap-1">
          <span>{label}</span>
          {required && <span className="text-rose-400">*</span>}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        disabled={disabled}
        className={`w-full bg-[#0d1017] border text-sm text-slate-100 rounded-lg px-3 py-2 transition-all duration-150 outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
          error
            ? 'border-rose-500/50 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20'
            : 'border-white/10 hover:border-white/20 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20'
        } ${className}`}
        {...props}
      >
        {children ||
          options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0d1017] text-slate-100">
              {opt.label}
            </option>
          ))}
      </select>
      {error && <p className="text-xs text-rose-400">{error}</p>}
      {!error && helperText && <p className="text-xs text-slate-500">{helperText}</p>}
    </div>
  );
});
