import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, X } from 'lucide-react';

export default function WorkflowValidationPanel({
  validationResult,
  onFocusNode,
  onClose
}) {
  if (!validationResult) return null;

  const { valid, errors = [], warnings = [] } = validationResult;

  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-xl p-4 rounded-2xl border shadow-2xl backdrop-blur-xl z-40 select-none animate-slide-up ${
        valid
          ? 'bg-emerald-950/80 border-emerald-800/80 text-emerald-200'
          : 'bg-rose-950/80 border-rose-800/80 text-rose-200'
      }`}
    >
      <div className="flex items-center justify-between pb-2 border-b border-white/10 mb-2">
        <div className="flex items-center gap-2 font-bold text-xs">
          {valid ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          )}
          <span>
            {valid
              ? 'DAG Validation Passed — Workflow Ready'
              : `DAG Validation Failed (${errors.length} error${errors.length > 1 ? 's' : ''})`}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="max-h-36 overflow-y-auto space-y-1.5 text-xs">
        {errors.map((e, idx) => (
          <div
            key={idx}
            onClick={() => e.node_key && onFocusNode(e.node_key)}
            className="flex items-start gap-2 p-1.5 rounded-lg bg-black/30 hover:bg-black/50 cursor-pointer transition text-rose-300"
          >
            <span className="font-mono font-bold text-[10px] uppercase bg-rose-500/20 px-1.5 py-0.5 rounded text-rose-400">
              {e.code}
            </span>
            <span className="flex-1">{e.message}</span>
            {e.node_key && (
              <span className="text-[10px] font-mono text-slate-400">
                node: {e.node_key}
              </span>
            )}
          </div>
        ))}

        {warnings.map((w, idx) => (
          <div
            key={idx}
            onClick={() => w.node_key && onFocusNode(w.node_key)}
            className="flex items-start gap-2 p-1.5 rounded-lg bg-black/30 hover:bg-black/50 cursor-pointer transition text-amber-300"
          >
            <span className="font-mono font-bold text-[10px] uppercase bg-amber-500/20 px-1.5 py-0.5 rounded text-amber-400">
              {w.code}
            </span>
            <span className="flex-1">{w.message}</span>
            {w.node_key && (
              <span className="text-[10px] font-mono text-slate-400">
                node: {w.node_key}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
