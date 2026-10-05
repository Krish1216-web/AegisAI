import React from 'react';
import { Button } from './Button';

/**
 * Enterprise EmptyState Component
 * Standardizes clear explanations and next actions when a list or view has no data.
 */
export function EmptyState({
  icon = null,
  title = 'No records found',
  description = 'There is no data available to display at this moment.',
  actionLabel = null,
  onAction = null,
  secondaryActionLabel = null,
  onSecondaryAction = null,
  className = '',
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-xl border border-dashed border-white/[0.1] bg-[#0d101740] ${className}`}
    >
      {icon && (
        <div className="p-3.5 rounded-full bg-white/[0.04] text-slate-400 border border-white/[0.08] mb-4 shadow-inner">
          {icon}
        </div>
      )}
      <h4 className="text-sm font-semibold tracking-wide text-slate-200">{title}</h4>
      <p className="text-xs text-slate-400 max-w-sm mt-1 leading-relaxed">{description}</p>
      {(actionLabel || secondaryActionLabel) && (
        <div className="flex items-center gap-3 mt-5">
          {secondaryActionLabel && (
            <Button variant="ghost" size="sm" onClick={onSecondaryAction}>
              {secondaryActionLabel}
            </Button>
          )}
          {actionLabel && (
            <Button variant="primary" size="sm" onClick={onAction}>
              {actionLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
