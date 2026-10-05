import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Enterprise IconButton Component with mandatory accessible labeling
 */
export function IconButton({
  icon,
  'aria-label': ariaLabel,
  variant = 'ghost',
  size = 'md',
  isLoading = false,
  disabled = false,
  className = '',
  onClick,
  ...props
}) {
  const baseStyles = 'inline-flex items-center justify-center rounded-lg transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer';

  const sizeStyles = {
    xs: 'p-1 text-xs',
    sm: 'p-1.5 text-xs',
    md: 'p-2 text-sm',
    lg: 'p-2.5 text-base',
  };

  const variantStyles = {
    primary: 'bg-cyan-500 text-black hover:bg-cyan-400 focus-visible:ring-cyan-400 shadow-sm hover:shadow-cyan-500/20 active:scale-95',
    secondary: 'bg-white/10 text-slate-100 hover:bg-white/15 focus-visible:ring-slate-400 border border-white/10 hover:border-white/20 active:scale-95',
    ghost: 'bg-transparent text-slate-400 hover:text-white hover:bg-white/5 focus-visible:ring-slate-400 active:scale-95',
    outline: 'bg-transparent text-slate-300 border border-white/10 hover:border-white/30 hover:bg-white/5 focus-visible:ring-slate-400 active:scale-95',
    danger: 'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 focus-visible:ring-rose-400 active:scale-95',
  };

  return (
    <button
      type="button"
      aria-label={ariaLabel}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${sizeStyles[size] || sizeStyles.md} ${variantStyles[variant] || variantStyles.ghost} ${className}`}
      {...props}
    >
      {isLoading ? <Loader2 size={16} className="animate-spin" /> : icon}
    </button>
  );
}
