import React from 'react';
import { StatusBadge } from './StatusBadge';
import { Clock, CheckCircle2, AlertCircle } from 'lucide-react';

/**
 * Enterprise Execution Timeline Component
 * Represents multi-step agent reasoning/execution progress with safe milestones.
 */
export function Timeline({ steps = [], currentStepIndex = 0, className = '' }) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {steps.map((step, idx) => {
        const isCompleted = idx < currentStepIndex;
        const isCurrent = idx === currentStepIndex;
        const isPending = idx > currentStepIndex;

        const iconColor = isCompleted
          ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
          : isCurrent
          ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40 animate-pulse'
          : 'bg-white/[0.04] text-slate-500 border-white/[0.08]';

        return (
          <div key={step.id || idx} className="relative flex items-start gap-3.5 group">
            {/* Connecting line */}
            {idx < steps.length - 1 && (
              <div
                className={`absolute left-3.5 top-8 bottom-0 w-[2px] -ml-[1px] ${
                  isCompleted ? 'bg-emerald-500/40' : 'bg-white/[0.06]'
                }`}
              />
            )}

            {/* Icon Node */}
            <div
              className={`w-7 h-7 rounded-full border flex items-center justify-center text-xs shrink-0 z-10 transition-colors ${iconColor}`}
            >
              {isCompleted ? <CheckCircle2 size={14} /> : isCurrent ? <Clock size={14} /> : idx + 1}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 pb-4">
              <div className="flex items-center justify-between gap-3">
                <h5 className="text-xs font-semibold tracking-wide text-slate-200">{step.title}</h5>
                {step.status && <StatusBadge status={step.status} size="xs" />}
              </div>
              {step.description && (
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{step.description}</p>
              )}
              {step.timestamp && (
                <span className="text-[10px] text-slate-500 font-mono mt-1 inline-block">
                  {step.timestamp}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Enterprise ActivityItem Component
 */
export function ActivityItem({ icon, actor, action, target, timestamp, details = null, className = '' }) {
  return (
    <div className={`flex items-start gap-3 py-3 border-b border-white/[0.04] text-xs ${className}`}>
      {icon && <div className="p-1.5 rounded-md bg-white/[0.04] text-slate-400 border border-white/[0.06] shrink-0 mt-0.5">{icon}</div>}
      <div className="flex-1 min-w-0">
        <p className="text-slate-300">
          <strong className="text-slate-100 font-semibold">{actor}</strong>{' '}
          <span className="text-slate-400">{action}</span>{' '}
          {target && <span className="text-cyan-400 font-medium">{target}</span>}
        </p>
        {details && <p className="text-slate-400 mt-0.5 text-[11px]">{details}</p>}
        {timestamp && <span className="text-[10px] text-slate-500 font-mono mt-1 inline-block">{timestamp}</span>}
      </div>
    </div>
  );
}
