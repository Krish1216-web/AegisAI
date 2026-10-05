import React from 'react';

/**
 * Generic Badge Component
 * Variants: default, primary, success, warning, danger, info, outline
 */
export function Badge({
  children,
  variant = 'default',
  size = 'sm',
  className = '',
  icon = null,
}) {
  const sizeStyles = {
    xs: 'text-[10px] px-1.5 py-0.5 font-medium',
    sm: 'text-xs px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-semibold',
  };

  const variantStyles = {
    default: 'bg-white/10 text-slate-300 border border-white/10',
    primary: 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30',
    success: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
    warning: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
    danger: 'bg-rose-500/15 text-rose-300 border border-rose-500/30',
    info: 'bg-blue-500/15 text-blue-300 border border-blue-500/30',
    outline: 'bg-transparent text-slate-300 border border-white/20',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md tracking-wide ${sizeStyles[size] || sizeStyles.sm} ${variantStyles[variant] || variantStyles.default} ${className}`}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
}
