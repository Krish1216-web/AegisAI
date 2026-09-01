import React, { useState } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  FileText, 
  GitBranch, 
  Server, 
  Bookmark, 
  ExternalLink,
  Layers,
  Sparkles
} from 'lucide-react';

const TRUST_CONFIG = {
  verified_rag: {
    label: 'VERIFIED RAG',
    badge: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    icon: ShieldCheck,
    description: 'Cryptographically grounded document evidence extracted from verified workspace embeddings.'
  },
  verified_graph: {
    label: 'VERIFIED GRAPH',
    badge: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
    icon: ShieldCheck,
    description: 'Deterministic entity node & relationship structure verified by Knowledge Graph Intelligence.'
  },
  untrusted_mcp: {
    label: 'UNTRUSTED MCP',
    badge: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    icon: ShieldAlert,
    description: 'External MCP tool or resource output. Treated strictly as passive data, never as system instructions.'
  },
  trusted_internal: {
    label: 'TRUSTED INTERNAL',
    badge: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    icon: ShieldCheck,
    description: 'Synthesized multi-agent reasoning, planning step, or deterministic transformation.'
  }
};

const SOURCE_TYPE_MAP = {
  document_chunk: { label: 'Document Chunk', icon: FileText },
  document: { label: 'Document', icon: FileText },
  graph_node: { label: 'Graph Entity', icon: GitBranch },
  graph_edge: { label: 'Graph Relationship', icon: GitBranch },
  mcp_tool: { label: 'MCP Tool Result', icon: Server },
  mcp_resource: { label: 'MCP Resource', icon: Server },
  mcp_prompt: { label: 'MCP Prompt', icon: Server },
  memory: { label: 'Memory Fact', icon: Bookmark },
  research: { label: 'Research Link', icon: ExternalLink },
  agent_reasoning: { label: 'Agent Reasoning', icon: Sparkles }
};

export default function PlatformEvidenceViewer({ provenance = [] }) {
  const [selectedItem, setSelectedItem] = useState(null);

  if (!provenance || provenance.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] rounded-xl text-center">
        <Layers size={32} className="text-slate-600 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Provenance Records</h4>
        <p className="text-xs text-slate-500 mt-1">Execute a capability to view verified citations, graph evidence, and MCP provenance.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-6 rounded-xl backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <div>
          <h4 className="text-sm font-bold text-slate-100 uppercase tracking-wide flex items-center gap-2">
            <ShieldCheck size={16} className="text-emerald-400" />
            <span>Unified Provenance & Citations ({provenance.length})</span>
          </h4>
          <span className="text-xs text-slate-400 mt-0.5 block">
            End-to-end evidence tracking with deterministic trust ratings
          </span>
        </div>
      </div>

      {/* Trust Legend */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.04)] text-xs">
        {Object.entries(TRUST_CONFIG).slice(0, 3).map(([key, config]) => {
          const Icon = config.icon;
          return (
            <div key={key} className="flex items-start gap-2.5">
              <Icon size={15} className={`mt-0.5 shrink-0 ${key === 'untrusted_mcp' ? 'text-amber-400' : 'text-emerald-400'}`} />
              <div>
                <span className="font-bold text-[11px] text-slate-200">{config.label}</span>
                <p className="text-[10px] text-slate-400 leading-tight mt-0.5">{config.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Evidence Cards List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {provenance.map((item, idx) => {
          const trustKey = (item.trust_level || 'trusted_internal').toLowerCase();
          const trust = TRUST_CONFIG[trustKey] || TRUST_CONFIG.trusted_internal;
          const TrustIcon = trust.icon;

          const sourceKey = (item.source_type || 'document_chunk').toLowerCase();
          const source = SOURCE_TYPE_MAP[sourceKey] || { label: item.source_type, icon: FileText };
          const SourceIcon = source.icon;

          return (
            <div
              key={item.id || idx}
              onClick={() => setSelectedItem(item)}
              className="flex flex-col justify-between p-4 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)] hover:border-cyan-500/30 transition-all cursor-pointer group"
            >
              <div>
                {/* Source Badge & Trust Badge */}
                <div className="flex items-center justify-between gap-2 mb-2.5">
                  <span className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-white/5 text-slate-300 border border-white/10">
                    <SourceIcon size={12} className="text-cyan-400" />
                    <span>{source.label}</span>
                  </span>

                  <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${trust.badge}`}>
                    <TrustIcon size={11} />
                    <span>{trust.label}</span>
                  </span>
                </div>

                {/* Title */}
                <h5 className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors mb-1.5 truncate">
                  {item.title || `Evidence ${item.source_id}`}
                </h5>

                {/* Snippet */}
                {item.snippet && (
                  <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed mb-3 font-sans">
                    {item.snippet}
                  </p>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between pt-2.5 border-t border-[rgba(255,255,255,0.04)] text-[11px] font-mono text-slate-500">
                <span className="truncate max-w-[160px]">ID: {item.source_id}</span>
                {item.confidence !== undefined && (
                  <span className="text-cyan-400 font-semibold">
                    Conf: {(item.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Snippet Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f1420] border border-cyan-500/40 rounded-xl p-6 max-w-xl w-full shadow-2xl flex flex-col gap-4 animate-scale-up">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="text-sm font-bold text-slate-100">
                  {selectedItem.title || selectedItem.source_id}
                </h4>
                <span className="text-xs font-mono text-cyan-400">
                  {selectedItem.source_type} &bull; {selectedItem.trust_level}
                </span>
              </div>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-200 text-xs px-2 py-1 bg-white/5 rounded cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Evidence Snippet</label>
              <div className="p-3 bg-black/50 border border-slate-800 rounded-lg text-xs text-slate-300 leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap">
                {selectedItem.snippet || 'No text snippet attached.'}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Source Metadata</label>
              <pre className="p-3 bg-black/50 border border-slate-800 rounded-lg text-[11px] font-mono text-cyan-300 max-h-40 overflow-y-auto">
                {JSON.stringify(selectedItem.metadata || {}, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedItem(null)}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-white/10 hover:bg-white/20 text-slate-200 cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
