import React, { useState } from 'react';
import { 
  AlertTriangle, 
  AlertOctagon, 
  Code2, 
  Copy, 
  Check, 
  FileText, 
  Layers, 
  Database,
  GitBranch,
  Bot
} from 'lucide-react';

export default function PlatformResultViewer({ execution }) {
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState('formatted'); // 'formatted' | 'raw'

  if (!execution) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] rounded-xl text-center">
        <Layers size={32} className="text-slate-600 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Execution Result Available</h4>
        <p className="text-xs text-slate-500 mt-1">Execute a capability to view structured output and evidence synthesis.</p>
      </div>
    );
  }

  const output = execution.output || {};
  const hasErrors = execution.errors && execution.errors.length > 0;
  const hasWarnings = execution.warnings && execution.warnings.length > 0;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(output, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const mainAnswer = output.response || output.answer || output.result || output.summary || output.content;

  return (
    <div className="flex flex-col gap-6 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-6 rounded-xl backdrop-blur-md">
      {/* Header & Mode Switcher */}
      <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-cyan-400" />
          <h4 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
            Execution Result
          </h4>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode(viewMode === 'formatted' ? 'raw' : 'formatted')}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-all cursor-pointer"
          >
            <Code2 size={13} />
            <span>{viewMode === 'formatted' ? 'View Raw JSON' : 'View Formatted'}</span>
          </button>
          
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-all cursor-pointer"
          >
            {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy JSON'}</span>
          </button>
        </div>
      </div>

      {/* Errors Banner */}
      {hasErrors && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300">
          <AlertOctagon size={18} className="shrink-0 mt-0.5 text-rose-400" />
          <div className="flex flex-col gap-1">
            <h5 className="text-xs font-bold uppercase tracking-wider text-rose-400">Execution Error</h5>
            {execution.errors.map((err, idx) => (
              <p key={idx} className="text-xs font-mono">
                [{err.code}] {err.message}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Warnings Banner */}
      {hasWarnings && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 text-amber-300">
          <AlertTriangle size={16} className="shrink-0 mt-0.5 text-amber-400" />
          <div className="flex flex-col gap-1">
            <h5 className="text-xs font-bold uppercase tracking-wider text-amber-400">Warnings</h5>
            {execution.warnings.map((w, idx) => (
              <p key={idx} className="text-xs">{w}</p>
            ))}
          </div>
        </div>
      )}

      {/* Content Rendering */}
      {viewMode === 'raw' ? (
        <pre className="p-4 rounded-lg bg-black/50 border border-slate-800 text-xs font-mono text-cyan-300/90 overflow-x-auto max-h-96">
          {JSON.stringify(output, null, 2)}
        </pre>
      ) : (
        <div className="flex flex-col gap-5">
          {/* Main Synthesized Response text */}
          {mainAnswer && typeof mainAnswer === 'string' && (
            <div className="p-4 rounded-xl bg-black/40 border border-cyan-500/20 text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans shadow-sm">
              {mainAnswer}
            </div>
          )}

          {/* Agent Plan steps */}
          {output.plan && Array.isArray(output.plan) && (
            <div className="flex flex-col gap-2">
              <h5 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                <Bot size={13} className="text-purple-400" /> Cognitive Execution Plan
              </h5>
              <div className="flex flex-col gap-2">
                {output.plan.map((step, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-2.5 rounded-lg bg-black/30 border border-slate-800 text-xs">
                    <span className="w-5 h-5 rounded-full bg-purple-500/20 text-purple-300 text-[10px] font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <span className="text-slate-300">{typeof step === 'string' ? step : JSON.stringify(step)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Structured Document Evidence */}
          {output.document_evidence && Array.isArray(output.document_evidence) && (
            <div className="flex flex-col gap-2">
              <h5 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                <Database size={13} className="text-cyan-400" /> Document Evidence Chunks
              </h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {output.document_evidence.map((doc, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-black/30 border border-cyan-500/10 flex flex-col gap-1 text-xs">
                    <span className="font-semibold text-cyan-300">{doc.title || `Evidence ${idx + 1}`}</span>
                    <p className="text-slate-400 line-clamp-3 text-[11px]">{doc.text || doc.snippet}</p>
                    <span className="text-[10px] font-mono text-slate-500">Score: {doc.score || '0.90'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Structured Graph Evidence */}
          {output.graph_evidence && Array.isArray(output.graph_evidence) && (
            <div className="flex flex-col gap-2">
              <h5 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                <GitBranch size={13} className="text-emerald-400" /> Knowledge Graph Evidence
              </h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {output.graph_evidence.map((g, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-black/30 border border-emerald-500/10 flex flex-col gap-1 text-xs">
                    <span className="font-semibold text-emerald-300">{g.name || g.label || `Entity ${idx + 1}`}</span>
                    <p className="text-slate-400 text-[11px]">{g.description || 'Verified graph node'}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
