import React from 'react';
import { AlertTriangle, Sparkles, Shield, Info } from 'lucide-react';

/**
 * Persistent Non-Dismissible Demo Banner & Watermark Component
 */
export function DemoBanner({ onExit, currentScenarioTitle }) {
  return (
    <div
      role="region"
      aria-label="Demo Mode Notice"
      className="bg-gradient-to-r from-amber-500/15 via-cyan-500/10 to-purple-500/15 border-b border-amber-500/30 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs text-amber-200 shadow-lg shadow-black/20"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono font-bold tracking-wider text-[11px] border border-amber-500/30 shrink-0">
          <AlertTriangle size={13} className="text-amber-400" />
          DEMO MODE
        </span>
        <span className="text-slate-300 font-medium truncate">
          Simulated Presentation Environment — <strong className="text-white font-semibold">No production data or actions are modified.</strong>
        </span>
        {currentScenarioTitle && (
          <span className="hidden md:inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-white/5 border border-white/10 text-cyan-300 font-mono">
            <Sparkles size={11} />
            {currentScenarioTitle}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono text-slate-400">
          <Shield size={12} className="text-emerald-400" />
          SYNTHETIC TENANT: AEGIS-DEMO
        </span>
        {onExit && (
          <button
            onClick={onExit}
            className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 hover:text-white text-xs font-semibold transition-all cursor-pointer"
          >
            Exit Showcase
          </button>
        )}
      </div>
    </div>
  );
}

export function DemoWatermark() {
  return (
    <div
      aria-hidden="true"
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-400 select-none pointer-events-none"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
      SIMULATED SHOWCASE
    </div>
  );
}
