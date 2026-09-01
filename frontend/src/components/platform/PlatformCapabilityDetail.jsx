import React from 'react';
import { 
  Play, 
  Tag, 
  Code, 
  Lock, 
  ExternalLink,
  Layers,
  FileCode
} from 'lucide-react';
import { Link } from 'react-router-dom';

const SPECIALIZED_ROUTES = {
  agent: { path: '/user/chat', label: 'AI Workspace' },
  rag: { path: '/user/documents', label: 'Documents Hub' },
  knowledge_graph: { path: '/user/graph', label: 'Knowledge Graph' },
  mcp: { path: '/user/mcp-marketplace', label: 'MCP Market' },
  workflow: { path: '/user/workflows', label: 'Workflow Builder' },
  memory: { path: '/user/memory', label: 'Memory Explorer' }
};

export default function PlatformCapabilityDetail({ 
  capability, 
  onOpenExecute,
  onClose 
}) {
  if (!capability) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] rounded-xl text-center">
        <Layers size={36} className="text-slate-600 mb-3" />
        <h4 className="text-sm font-semibold text-slate-300">No Capability Selected</h4>
        <p className="text-xs text-slate-500 mt-1">Select a capability card from the explorer to inspect its schema and execution parameters.</p>
      </div>
    );
  }

  const specializedRoute = SPECIALIZED_ROUTES[capability.capability_type];

  return (
    <div className="flex flex-col gap-6 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-6 rounded-xl backdrop-blur-md">
      {/* Top Header & Actions */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-5 border-b border-[rgba(255,255,255,0.06)]">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-slate-100">{capability.name}</h3>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              {capability.capability_type.toUpperCase()}
            </span>
          </div>
          <span className="font-mono text-xs text-slate-400 mt-1 block">
            {capability.capability_id} &bull; v{capability.version}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {specializedRoute && (
            <Link
              to={specializedRoute.path}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-all"
            >
              <ExternalLink size={13} />
              <span>{specializedRoute.label}</span>
            </Link>
          )}

          <button
            onClick={() => onOpenExecute(capability)}
            disabled={!capability.enabled}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer ${
              capability.enabled
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black shadow-cyan-500/20'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
            }`}
          >
            <Play size={13} className="fill-current" />
            <span>Launch in Console</span>
          </button>
        </div>
      </div>

      {/* Description & Metadata */}
      <div>
        <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Description</h5>
        <p className="text-sm text-slate-300 leading-relaxed">
          {capability.description || 'No detailed documentation specified for this capability.'}
        </p>
      </div>

      {/* Tags & Permissions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Required Permissions */}
        <div className="p-4 rounded-lg bg-black/30 border border-[rgba(255,255,255,0.04)]">
          <h6 className="flex items-center gap-2 text-xs font-semibold text-slate-300 mb-2">
            <Lock size={13} className="text-amber-400" />
            <span>Required Security Permissions</span>
          </h6>
          {capability.required_permissions && capability.required_permissions.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {capability.required_permissions.map(perm => (
                <span key={perm} className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  {perm}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-slate-500">Standard authenticated user access</span>
          )}
        </div>

        {/* Tags */}
        <div className="p-4 rounded-lg bg-black/30 border border-[rgba(255,255,255,0.04)]">
          <h6 className="flex items-center gap-2 text-xs font-semibold text-slate-300 mb-2">
            <Tag size={13} className="text-cyan-400" />
            <span>Capability Tags</span>
          </h6>
          {capability.tags && capability.tags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {capability.tags.map(tag => (
                <span key={tag} className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                  #{tag}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-slate-500">No tags configured</span>
          )}
        </div>
      </div>

      {/* JSON Schemas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Input Schema */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
              <FileCode size={13} className="text-cyan-400" /> Input JSON Schema
            </span>
          </div>
          <pre className="p-4 rounded-lg bg-black/50 border border-slate-800 text-xs font-mono text-cyan-300/90 overflow-x-auto max-h-64">
            {JSON.stringify(capability.input_schema || {}, null, 2)}
          </pre>
        </div>

        {/* Output Schema */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
              <Code size={13} className="text-emerald-400" /> Output JSON Schema
            </span>
          </div>
          <pre className="p-4 rounded-lg bg-black/50 border border-slate-800 text-xs font-mono text-emerald-300/90 overflow-x-auto max-h-64">
            {JSON.stringify(capability.output_schema || {}, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
