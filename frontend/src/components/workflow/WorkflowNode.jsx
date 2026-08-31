import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import {
  Play,
  Square,
  Bot,
  FileSearch,
  GitBranch,
  Bookmark,
  Cpu,
  FileCode,
  Terminal,
  HelpCircle,
  Clock,
  Shuffle,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  Settings
} from 'lucide-react';

const NODE_TYPE_METADATA = {
  start: { label: 'Start Trigger', icon: Play, color: 'emerald', border: 'border-emerald-500/50', bg: 'bg-emerald-950/40', text: 'text-emerald-400' },
  end: { label: 'End Output', icon: Square, color: 'rose', border: 'border-rose-500/50', bg: 'bg-rose-950/40', text: 'text-rose-400' },
  agent: { label: 'AI Agent', icon: Bot, color: 'purple', border: 'border-purple-500/50', bg: 'bg-purple-950/40', text: 'text-purple-400' },
  rag: { label: 'RAG Retriever', icon: FileSearch, color: 'cyan', border: 'border-cyan-500/50', bg: 'bg-cyan-950/40', text: 'text-cyan-400' },
  graph: { label: 'Knowledge Graph', icon: GitBranch, color: 'indigo', border: 'border-indigo-500/50', bg: 'bg-indigo-950/40', text: 'text-indigo-400' },
  memory: { label: 'Agent Memory', icon: Bookmark, color: 'amber', border: 'border-amber-500/50', bg: 'bg-amber-950/40', text: 'text-amber-400' },
  mcp_tool: { label: 'MCP Tool', icon: Cpu, color: 'teal', border: 'border-teal-500/50', bg: 'bg-teal-950/40', text: 'text-teal-400', isMcp: true },
  mcp_resource: { label: 'MCP Resource', icon: FileCode, color: 'teal', border: 'border-teal-500/50', bg: 'bg-teal-950/40', text: 'text-teal-400', isMcp: true },
  mcp_prompt: { label: 'MCP Prompt', icon: Terminal, color: 'teal', border: 'border-teal-500/50', bg: 'bg-teal-950/40', text: 'text-teal-400', isMcp: true },
  local_tool: { label: 'Local Tool', icon: Terminal, color: 'slate', border: 'border-slate-500/50', bg: 'bg-slate-900/60', text: 'text-slate-300' },
  condition: { label: 'Condition Branch', icon: HelpCircle, color: 'yellow', border: 'border-yellow-500/50', bg: 'bg-yellow-950/40', text: 'text-yellow-400' },
  human_approval: { label: 'Human Approval', icon: Clock, color: 'orange', border: 'border-orange-500/50', bg: 'bg-orange-950/40', text: 'text-orange-400' },
  transform: { label: 'Data Transform', icon: Shuffle, color: 'blue', border: 'border-blue-500/50', bg: 'bg-blue-950/40', text: 'text-blue-400' }
};

function WorkflowNodeComponent({ id, data, selected }) {
  const nodeType = data?.node_type || 'agent';
  const meta = NODE_TYPE_METADATA[nodeType] || NODE_TYPE_METADATA.agent;
  const Icon = meta.icon;

  const isStart = nodeType === 'start';
  const isEnd = nodeType === 'end';
  const hasError = data?.hasError;
  const isConfigured = data?.isConfigured !== false;

  return (
    <div
      className={`relative rounded-2xl min-w-[220px] max-w-[280px] p-3.5 backdrop-blur-xl transition-all shadow-xl select-none ${
        selected ? 'ring-2 ring-indigo-400 shadow-indigo-500/20' : 'hover:border-slate-600'
      } ${meta.border} ${meta.bg} border`}
    >
      {/* Handles */}
      {!isStart && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !bg-slate-400 !border-2 !border-slate-900 hover:!bg-indigo-400 transition"
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg bg-black/40 ${meta.text}`}>
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-100 truncate max-w-[130px]" title={data?.name || meta.label}>
              {data?.name || meta.label}
            </div>
            <div className="text-[10px] font-mono text-slate-400 leading-none mt-0.5">
              {data?.node_key}
            </div>
          </div>
        </div>

        {/* Delete button when selected */}
        {data?.onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onDelete(id);
            }}
            className="p-1 rounded-md text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
            title="Delete Node"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Badges / Status */}
      <div className="flex items-center gap-1.5 flex-wrap mt-2 pt-2 border-t border-white/5">
        <span className={`px-2 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider ${meta.text} bg-black/30`}>
          {nodeType}
        </span>

        {meta.isMcp && (
          <span className="px-1.5 py-0.5 rounded text-[8px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
            UNTRUSTED_MCP
          </span>
        )}

        {hasError ? (
          <span className="flex items-center gap-1 text-[9px] text-rose-400 ml-auto font-mono">
            <AlertTriangle className="w-3 h-3" /> Error
          </span>
        ) : isConfigured ? (
          <span className="flex items-center gap-1 text-[9px] text-emerald-400 ml-auto font-mono">
            <CheckCircle2 className="w-3 h-3" /> Ready
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[9px] text-amber-400 ml-auto font-mono">
            <AlertTriangle className="w-3 h-3" /> Incomplete
          </span>
        )}
      </div>

      {!isEnd && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!w-3 !h-3 !bg-slate-400 !border-2 !border-slate-900 hover:!bg-indigo-400 transition"
        />
      )}
    </div>
  );
}

export default memo(WorkflowNodeComponent);
