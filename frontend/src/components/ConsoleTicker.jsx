import React, { useEffect, useRef } from 'react';
import { Terminal, Shield } from 'lucide-react';

export default function ConsoleTicker({ logs }) {
  const tickerEndRef = useRef(null);

  useEffect(() => {
    tickerEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const latestLog = logs[logs.length - 1];

  const getAgentColor = (agent) => {
    switch (agent?.toLowerCase()) {
      case 'orchestrator':
      case 'sys': return 'text-cyan-400';
      case 'planning': return 'text-purple-400';
      case 'research': return 'text-pink-400';
      case 'execution': return 'text-yellow-400';
      case 'memory': return 'text-green-400';
      default: return 'text-slate-400';
    }
  };

  return (
    <footer className="h-10 border-t border-[rgba(255,255,255,0.06)] bg-[#090a0d] px-6 flex items-center justify-between text-xs text-slate-400 shrink-0 font-mono select-none">
      <div className="flex items-center gap-3 overflow-hidden flex-1">
        <Terminal size={12} className="text-cyan-400 shrink-0 animate-pulse" />
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider shrink-0 border-r border-[rgba(255,255,255,0.12)] pr-3">LIVE_CONSOLE</span>
        
        {/* Log Ticker Screen */}
        <div className="flex items-center gap-2 overflow-hidden whitespace-nowrap text-slate-300">
          {latestLog ? (
            <div className="flex items-center gap-2 animate-fade-in">
              <span className="text-slate-600">[{latestLog.timestamp}]</span>
              <span className={`font-semibold ${getAgentColor(latestLog.agent)}`}>[{latestLog.agent.toUpperCase()}]</span>
              <span className="truncate">{latestLog.text}</span>
            </div>
          ) : (
            <span className="text-slate-600">No active process streams. Core stand-by.</span>
          )}
        </div>
      </div>
      
      {/* Telemetry diagnostics */}
      <div className="flex items-center gap-4 shrink-0 text-[10px] text-slate-500 pl-4 border-l border-[rgba(255,255,255,0.12)]">
        <div className="flex items-center gap-1.5">
          <Shield size={10} className="text-green-400" />
          <span>PORT: SECURE</span>
        </div>
        <div>
          <span>FPS: 60.0</span>
        </div>
        <div>
          <span>LATENCY: 12ms</span>
        </div>
      </div>
    </footer>
  );
}
