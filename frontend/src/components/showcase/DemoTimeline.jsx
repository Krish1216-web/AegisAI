import React from 'react';
import {
  Sparkles,
  Bot,
  BrainCircuit,
  FileText,
  GitBranch,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  Clock,
  ArrowRight
} from 'lucide-react';

const STAGE_CONFIGS = {
  REQUEST: { icon: Sparkles, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30' },
  UNDERSTAND: { icon: BrainCircuit, color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/30' },
  PLAN: { icon: Bot, color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/30' },
  RETRIEVE: { icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30' },
  REASON: { icon: GitBranch, color: 'text-teal-400', bg: 'bg-teal-500/10 border-teal-500/30' },
  EXECUTE: { icon: Cpu, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/30' },
  VERIFY: { icon: ShieldCheck, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30' },
  RESPOND: { icon: CheckCircle2, color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/30' }
};

export function DemoTimeline({ steps, currentStepIndex, isCompleted, onStepClick }) {
  if (!steps || steps.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Simulation Timeline"
      className="p-4 rounded-xl border border-white/10 bg-[#0d1017]/80 backdrop-blur-sm flex flex-col gap-3"
    >
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Clock size={13} className="text-cyan-400" />
          Execution Stage Progress
        </span>
        <span className="font-mono text-[11px] text-cyan-400 font-semibold">
          {isCompleted ? 'COMPLETED (100%)' : `STAGE ${Math.min(currentStepIndex + 1, steps.length)} OF ${steps.length}`}
        </span>
      </div>

      {/* Horizontal Steps Bar (Scrollable on small screens) */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 select-none">
        {steps.map((step, idx) => {
          const isPassed = idx < currentStepIndex || isCompleted;
          const isCurrent = idx === currentStepIndex && !isCompleted;
          const isPending = idx > currentStepIndex && !isCompleted;

          const config = STAGE_CONFIGS[step.stage] || { icon: Bot, color: 'text-slate-400', bg: 'bg-white/5 border-white/10' };
          const Icon = config.icon;

          return (
            <React.Fragment key={step.stage + idx}>
              <button
                onClick={() => onStepClick && onStepClick(idx)}
                disabled={isPending}
                aria-label={`Step ${idx + 1}: ${step.stage} - ${step.title}`}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-medium transition-all shrink-0 cursor-pointer ${
                  isCurrent
                    ? `${config.bg} ${config.color} ring-2 ring-cyan-500/40 font-bold scale-[1.02]`
                    : isPassed
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-white/[0.02] border-white/10 text-slate-500 opacity-60 cursor-not-allowed'
                }`}
              >
                <Icon size={14} className={isCurrent ? 'animate-pulse' : ''} />
                <span>{step.stage}</span>
                {isPassed && <CheckCircle2 size={12} className="text-emerald-400 ml-0.5" />}
              </button>

              {idx < steps.length - 1 && (
                <ArrowRight size={12} className={`shrink-0 ${isPassed ? 'text-emerald-500' : 'text-slate-600'}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
