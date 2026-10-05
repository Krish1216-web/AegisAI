import React from 'react';

/**
 * Enterprise Status Badge Component
 * Normalizes all execution, job, system, and security states into consistent visual representations.
 */
export function StatusBadge({ status, size = 'sm', showDot = true, className = '' }) {
  if (!status) return null;

  const normalized = String(status).toUpperCase();

  const getStatusConfig = (s) => {
    switch (s) {
      // Success / Complete states
      case 'COMPLETED':
      case 'SUCCEEDED':
      case 'ONLINE':
      case 'SAFE':
      case 'ACTIVE':
      case 'PUBLISHED':
      case 'SUCCESS':
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
          dot: 'bg-emerald-400',
          label: s,
        };

      // In-flight / Running states
      case 'EXECUTING':
      case 'RUNNING':
      case 'CLAIMED':
      case 'PLANNING':
      case 'PLANNED':
      case 'VALIDATING':
      case 'VERIFYING':
        return {
          bg: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300',
          dot: 'bg-cyan-400 animate-pulse',
          label: s,
        };

      // Queued / Pending / Retry states
      case 'REQUESTED':
      case 'QUEUED':
      case 'PENDING':
      case 'RETRY_WAIT':
      case 'DRAFT':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
          dot: 'bg-amber-400',
          label: s,
        };

      // Warning / Degraded states
      case 'DEGRADED':
      case 'WARNING':
        return {
          bg: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300',
          dot: 'bg-yellow-400 animate-pulse',
          label: s,
        };

      // Failure / Blocked / Error states
      case 'FAILED':
      case 'DEAD_LETTERED':
      case 'OFFLINE':
      case 'BLOCKED':
      case 'CRITICAL':
      case 'ERROR':
        return {
          bg: 'bg-rose-500/10 border-rose-500/30 text-rose-300',
          dot: 'bg-rose-400',
          label: s,
        };

      // Cancelled / Neutral states
      case 'CANCELLED':
      case 'CANCEL_REQUESTED':
      case 'INACTIVE':
      case 'ARCHIVED':
      case 'UNKNOWN':
      default:
        return {
          bg: 'bg-slate-500/10 border-slate-500/30 text-slate-300',
          dot: 'bg-slate-400',
          label: s,
        };
    }
  };

  const config = getStatusConfig(normalized);

  const sizeStyles = {
    xs: 'text-[10px] px-1.5 py-0.5 gap-1 font-medium',
    sm: 'text-xs px-2 py-0.5 gap-1.5 font-medium',
    md: 'text-xs px-2.5 py-1 gap-2 font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center rounded-md border tracking-wider uppercase font-mono ${config.bg} ${sizeStyles[size] || sizeStyles.sm} ${className}`}
    >
      {showDot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${config.dot}`} />}
      <span>{config.label}</span>
    </span>
  );
}
