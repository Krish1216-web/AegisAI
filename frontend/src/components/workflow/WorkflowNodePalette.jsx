import React, { useState } from 'react';
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
  Search,
  Layers,
  Info
} from 'lucide-react';

const NODE_CATALOG = [
  {
    category: 'Control Flow',
    items: [
      { type: 'start', name: 'Start Trigger', desc: 'Entry point for workflow execution', icon: Play, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
      { type: 'end', name: 'End Output', desc: 'Terminal node returning final output', icon: Square, color: 'text-rose-400', bg: 'bg-rose-500/10' },
      { type: 'condition', name: 'Condition Branch', desc: 'Deterministic conditional evaluation', icon: HelpCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
      { type: 'human_approval', name: 'Human Approval', desc: 'Pauses execution until reviewer approval', icon: Clock, color: 'text-orange-400', bg: 'bg-orange-500/10' },
      { type: 'transform', name: 'Data Transform', desc: 'Declarative field mapping & expressions', icon: Shuffle, color: 'text-blue-400', bg: 'bg-blue-500/10' }
    ]
  },
  {
    category: 'AI & Cognition',
    items: [
      { type: 'agent', name: 'AI Agent', desc: 'Execute specialized AI Agent task', icon: Bot, color: 'text-purple-400', bg: 'bg-purple-500/10' },
      { type: 'rag', name: 'RAG Retriever', desc: 'Vector semantic search over workspace docs', icon: FileSearch, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
      { type: 'graph', name: 'Knowledge Graph', desc: 'Graph entity reasoning & path traversal', icon: GitBranch, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
      { type: 'memory', name: 'Agent Memory', desc: 'Retrieve or persist long-term memory facts', icon: Bookmark, color: 'text-amber-400', bg: 'bg-amber-500/10' }
    ]
  },
  {
    category: 'MCP & Integrations',
    items: [
      { type: 'mcp_tool', name: 'MCP Tool', desc: 'Execute tool from active MCP servers', icon: Cpu, color: 'text-teal-400', bg: 'bg-teal-500/10', isMcp: true },
      { type: 'mcp_resource', name: 'MCP Resource', desc: 'Read read-only resource URI context', icon: FileCode, color: 'text-teal-400', bg: 'bg-teal-500/10', isMcp: true },
      { type: 'mcp_prompt', name: 'MCP Prompt', desc: 'Render remote MCP prompt template', icon: Terminal, color: 'text-teal-400', bg: 'bg-teal-500/10', isMcp: true },
      { type: 'local_tool', name: 'Local Tool', desc: 'Execute system registered utility tool', icon: Terminal, color: 'text-slate-300', bg: 'bg-slate-800' }
    ]
  }
];

export default function WorkflowNodePalette({ onAddNode, hasStartNode }) {
  const [searchTerm, setSearchTerm] = useState('');

  const handleDragStart = (e, nodeType) => {
    e.dataTransfer.setData('application/reactflow/type', nodeType);
    e.dataTransfer.effectAllowed = 'move';
  };

  const filteredCatalog = NODE_CATALOG.map((cat) => ({
    ...cat,
    items: cat.items.filter(
      (item) =>
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.desc.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.type.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })).filter((cat) => cat.items.length > 0);

  return (
    <aside className="w-64 bg-slate-950/80 border-r border-slate-800 flex flex-col h-full overflow-hidden select-none z-10 backdrop-blur-md">
      {/* Search Header */}
      <div className="p-3.5 border-b border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            Node Palette
          </span>
          <span className="text-[10px] text-slate-500 font-mono">13 types</span>
        </div>
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Catalog List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {filteredCatalog.map((cat, idx) => (
          <div key={idx} className="space-y-1.5">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1">
              {cat.category}
            </h4>
            <div className="space-y-1">
              {cat.items.map((item) => {
                const Icon = item.icon;
                const isStartDisabled = item.type === 'start' && hasStartNode;

                return (
                  <div
                    key={item.type}
                    draggable={!isStartDisabled}
                    onDragStart={(e) => handleDragStart(e, item.type)}
                    onClick={() => !isStartDisabled && onAddNode(item.type)}
                    className={`group p-2 rounded-xl border border-slate-800/80 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 transition cursor-grab active:cursor-grabbing flex items-start gap-2.5 ${
                      isStartDisabled ? 'opacity-40 cursor-not-allowed' : ''
                    }`}
                    title={isStartDisabled ? 'A workflow can only have one Start Trigger node.' : 'Drag to canvas or click to add'}
                  >
                    <div className={`p-1.5 rounded-lg ${item.bg} ${item.color} shrink-0 mt-0.5`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-200 truncate group-hover:text-indigo-300">
                          {item.name}
                        </span>
                        {item.isMcp && (
                          <span className="text-[8px] font-mono px-1 py-0.2 rounded bg-amber-500/10 text-amber-400">
                            MCP
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-slate-400 line-clamp-1 leading-snug">
                        {item.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="p-2.5 border-t border-slate-800 bg-slate-950 text-[10px] text-slate-500 flex items-center gap-1.5">
        <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span>Drag a node onto canvas or click to add</span>
      </div>
    </aside>
  );
}
