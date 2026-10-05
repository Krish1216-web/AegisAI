import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Enterprise Button Component
 * Variants: primary, secondary, ghost, outline, danger, success
 * Sizes: xs, sm, md, lg
 */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  leftIcon = null,
  rightIcon = null,
  className = '',
  type = 'button',
  onClick,
  ...props
}) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer';

  const sizeStyles = {
    xs: 'text-xs px-2 py-1 gap-1',
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  };

  const variantStyles = {
    primary: 'bg-cyan-500 text-black hover:bg-cyan-400 focus-visible:ring-cyan-400 font-semibold shadow-sm hover:shadow-cyan-500/20 active:scale-[0.98]',
    secondary: 'bg-white/10 text-slate-100 hover:bg-white/15 focus-visible:ring-slate-400 border border-white/10 hover:border-white/20 active:scale-[0.98]',
    ghost: 'bg-transparent text-slate-300 hover:text-white hover:bg-white/5 focus-visible:ring-slate-400',
    outline: 'bg-transparent text-slate-200 border border-white/20 hover:border-white/40 hover:bg-white/5 focus-visible:ring-slate-400',
    danger: 'bg-rose-500/15 text-rose-300 border border-rose-500/30 hover:bg-rose-500/25 hover:border-rose-500/50 focus-visible:ring-rose-400 active:scale-[0.98]',
    success: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 hover:border-emerald-500/50 focus-visible:ring-emerald-400 active:scale-[0.98]',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${sizeStyles[size] || sizeStyles.md} ${variantStyles[variant] || variantStyles.primary} ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 size={size === 'xs' || size === 'sm' ? 14 : 16} className="animate-spin" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="shrink-0">{leftIcon}</span>}
          <span>{children}</span>
          {rightIcon && <span className="shrink-0">{rightIcon}</span>}
        </>
      )}
    </button>
  );
}
