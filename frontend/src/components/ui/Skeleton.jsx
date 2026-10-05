import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Enterprise Skeleton Component for progressive loading states
 */
export function Skeleton({ className = '', height = null, width = null, rounded = 'md' }) {
  const roundedStyles = {
    none: 'rounded-none',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    full: 'rounded-full',
  };

  const style = {};
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;

  return (
    <div
      style={style}
      className={`bg-white/[0.06] animate-pulse ${roundedStyles[rounded] || roundedStyles.md} ${className}`}
    />
  );
}

/**
 * Enterprise Spinner Component
 */
export function Spinner({ size = 'md', className = '', label = null }) {
  const sizeMap = {
    xs: 12,
    sm: 16,
    md: 24,
    lg: 32,
    xl: 48,
  };

  return (
    <div className={`inline-flex flex-col items-center justify-center gap-2 ${className}`}>
      <Loader2 size={sizeMap[size] || 24} className="animate-spin text-cyan-400" />
      {label && <span className="text-xs text-slate-400 font-medium">{label}</span>}
    </div>
  );
}
