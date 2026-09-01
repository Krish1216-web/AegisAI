import React from 'react';
import { 
  CheckCircle2, 
  Activity,
  Terminal,
  StopCircle
} from 'lucide-react';

const LIFECYCLE_STAGES = [
  { id: 'requested', label: 'Requested' },
  { id: 'validating', label: 'Validating' },
  { id: 'planned', label: 'Planned' },
  { id: 'executing', label: 'Executing' },
  { id: 'verifying', label: 'Verifying' },
  { id: 'completed', label: 'Completed' }
];

const STATUS_COLOR_MAP = {
  completed: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10',
  executing: 'text-cyan-400 border-cyan-500/40 bg-cyan-500/10',
  planned: 'text-blue-400 border-blue-500/40 bg-blue-500/10',
  validating: 'text-indigo-400 border-indigo-500/40 bg-indigo-500/10',
  requested: 'text-slate-400 border-slate-500/40 bg-slate-500/10',
  waiting: 'text-amber-400 border-amber-500/40 bg-amber-500/10',
  failed: 'text-rose-400 border-rose-500/40 bg-rose-500/10',
  cancelled: 'text-slate-400 border-slate-500/40 bg-slate-500/10',
  denied: 'text-rose-400 border-rose-500/40 bg-rose-500/10'
};

export default function PlatformExecutionTimeline({
  execution,
  events = [],
  onCancelExecution,
  isCancelling = false
}) {
  if (!execution) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] rounded-xl text-center">
        <Activity size={32} className="text-slate-600 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Active Execution</h4>
        <p className="text-xs text-slate-500 mt-1">Execute a capability from the console to view its live lifecycle progress and event stream.</p>
      </div>
    );
  }

  const currentStatus = execution.status?.toLowerCase() || 'requested';
  const stageIndex = LIFECYCLE_STAGES.findIndex(s => s.id === currentStatus);
  const isTerminal = ['completed', 'failed', 'cancelled', 'denied'].includes(currentStatus);
  const isCancellable = ['requested', 'validating', 'planned', 'executing', 'waiting'].includes(currentStatus);

  return (
    <div className="flex flex-col gap-6 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-6 rounded-xl backdrop-blur-md">
      {/* Top Bar: Execution Status & Cancel Action */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg border ${STATUS_COLOR_MAP[currentStatus] || STATUS_COLOR_MAP.requested}`}>
            <Activity size={18} className={!isTerminal ? 'animate-pulse' : ''} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-slate-100">
                Execution: {execution.capability_id}
              </h4>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${STATUS_COLOR_MAP[currentStatus] || STATUS_COLOR_MAP.requested}`}>
                {execution.status}
              </span>
            </div>
            <span className="font-mono text-[11px] text-slate-400 block mt-0.5">
              ID: {execution.execution_id} &bull; {execution.duration_ms}ms
            </span>
          </div>
        </div>

        {/* Cancel Action */}
        {isCancellable && onCancelExecution && (
          <button
            onClick={() => onCancelExecution(execution.execution_id)}
            disabled={isCancelling}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 transition-all cursor-pointer"
          >
            <StopCircle size={13} />
            <span>{isCancelling ? 'Cancelling...' : 'Cancel Execution'}</span>
          </button>
        )}
      </div>

      {/* 6-Stage Deterministic Lifecycle Stepper */}
      <div className="py-2">
        <div className="flex items-center justify-between relative">
          <div className="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 bg-slate-800 w-full z-0" />
          
          {LIFECYCLE_STAGES.map((stage, idx) => {
            const isCompleted = isTerminal && currentStatus === 'completed' ? true : (stageIndex !== -1 && idx < stageIndex);
            const isCurrent = stage.id === currentStatus;
            const isFailed = isTerminal && currentStatus !== 'completed' && isCurrent;

            return (
              <div key={stage.id} className="flex flex-col items-center gap-2 relative z-10">
                <div 
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all border ${
                    isFailed 
                      ? 'bg-rose-500/20 border-rose-500 text-rose-400 ring-4 ring-rose-500/10'
                      : isCurrent
                      ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 ring-4 ring-cyan-500/20 animate-pulse'
                      : isCompleted
                      ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                      : 'bg-[#0d1017] border-slate-800 text-slate-500'
                  }`}
                >
                  {isCompleted ? <CheckCircle2 size={13} /> : idx + 1}
                </div>
                <span className={`text-[10px] font-semibold tracking-wider uppercase ${isCurrent ? 'text-cyan-300' : isCompleted ? 'text-slate-300' : 'text-slate-500'}`}>
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Real-Time Platform Events Timeline */}
      <div className="flex flex-col gap-3 pt-2">
        <div className="flex items-center justify-between">
          <h5 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
            <Terminal size={13} className="text-cyan-400" /> Platform Execution Events ({events.length})
          </h5>
          <span className="text-[10px] text-slate-500 font-mono">Correlation: {execution.correlation_id}</span>
        </div>

        <div className="flex flex-col gap-2 max-h-60 overflow-y-auto pr-1">
          {events.length === 0 ? (
            <div className="p-4 rounded-lg bg-black/30 border border-slate-800 text-center text-xs text-slate-500 font-mono">
              Execution started &bull; Awaiting telemetry stream...
            </div>
          ) : (
            events.map((evt, idx) => (
              <div 
                key={evt.event_id || idx}
                className="flex items-start gap-3 p-2.5 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.04)] text-xs font-mono"
              >
                <span className="text-[10px] text-slate-500 shrink-0 mt-0.5">
                  {new Date(evt.timestamp || Date.now()).toLocaleTimeString()}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shrink-0">
                  {evt.event_type || 'LIFECYCLE'}
                </span>
                <div className="flex-1 text-slate-300 text-[11px] truncate">
                  <span className="text-cyan-300 font-semibold">{evt.payload?.action || evt.source_component}: </span>
                  <span className="text-slate-400">{JSON.stringify(evt.payload || {})}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
