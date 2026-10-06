import React from 'react';
import { Terminal, Shield, Cpu, Activity, Clock } from 'lucide-react';

export function DemoEventStream({ events }) {
  return (
    <div
      role="log"
      aria-live="polite"
      aria-label="Simulated Event Log"
      className="p-4 rounded-xl border border-white/10 bg-[#0a0d14] flex flex-col gap-3 font-mono h-64 overflow-y-auto select-text"
    >
      <div className="flex items-center justify-between text-xs pb-2 border-b border-white/[0.08] sticky top-0 bg-[#0a0d14] z-10">
        <div className="flex items-center gap-2 text-slate-300 font-bold uppercase tracking-wider">
          <Terminal size={14} className="text-cyan-400" />
          Simulated Event Stream
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-semibold">
          LIVE DEMO STREAM
        </span>
      </div>

      <div className="flex flex-col gap-2 text-xs">
        {events.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs italic">
            Awaiting scenario initialization... Start a scenario to stream simulated agent events.
          </div>
        ) : (
          events.map((evt, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2.5 p-2 rounded bg-white/[0.02] border border-white/[0.04] hover:border-white/10 transition-colors"
            >
              <span className="text-[11px] text-slate-500 shrink-0 font-medium">
                [{evt.time || '14:20:00'}]
              </span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-bold uppercase shrink-0 bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                {evt.agent || 'SYSTEM'}
              </span>
              <span className="text-slate-300 text-xs leading-relaxed flex-1">
                {evt.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
