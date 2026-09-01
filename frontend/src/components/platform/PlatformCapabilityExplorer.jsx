import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { 
  Bot, 
  Database, 
  GitBranch, 
  Server, 
  Workflow, 
  Bookmark, 
  Search, 
  Play, 
  Shield, 
  ExternalLink,
  Tag,
  CheckCircle2,
  XCircle,
  Cpu,
  Layers
} from 'lucide-react';

const CATEGORY_MAP = {
  all: { label: 'All Capabilities', icon: Layers },
  agent: { label: 'Multi-Agent', icon: Bot, color: 'text-purple-400 border-purple-500/30 bg-purple-500/10' },
  rag: { label: 'Cognitive RAG', icon: Database, color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10' },
  knowledge_graph: { label: 'Knowledge Graph', icon: GitBranch, color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' },
  mcp: { label: 'MCP Tools', icon: Server, color: 'text-amber-400 border-amber-500/30 bg-amber-500/10' },
  workflow: { label: 'Workflows', icon: Workflow, color: 'text-blue-400 border-blue-500/30 bg-blue-500/10' },
  memory: { label: 'Memory', icon: Bookmark, color: 'text-pink-400 border-pink-500/30 bg-pink-500/10' }
};

const SPECIALIZED_ROUTES = {
  agent: { path: '/user/chat', label: 'AI Workspace' },
  rag: { path: '/user/documents', label: 'Documents Hub' },
  knowledge_graph: { path: '/user/graph', label: 'Knowledge Graph' },
  mcp: { path: '/user/mcp-marketplace', label: 'MCP Market' },
  workflow: { path: '/user/workflows', label: 'Workflow Builder' },
  memory: { path: '/user/memory', label: 'Memory Explorer' }
};

export default function PlatformCapabilityExplorer({
  capabilities = [],
  selectedCapability,
  onSelectCapability,
  onOpenExecute
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const filteredCapabilities = useMemo(() => {
    return capabilities.filter(cap => {
      const matchesSearch = 
        cap.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        cap.capability_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (cap.description && cap.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (cap.tags && cap.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase())));

      const matchesCategory = selectedCategory === 'all' || cap.capability_type === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [capabilities, searchQuery, selectedCategory]);

  return (
    <div className="flex flex-col gap-6">
      {/* Search & Category Filter Bar */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-4 rounded-xl backdrop-blur-md">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search capabilities by name, ID, or tag..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-black/40 border border-slate-700/60 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 transition-all"
          />
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(CATEGORY_MAP).map(([key, item]) => {
            const Icon = item.icon;
            const active = selectedCategory === key;
            return (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  active 
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10' 
                    : 'bg-white/5 text-slate-400 hover:text-slate-200 border border-transparent hover:border-white/10'
                }`}
              >
                <Icon size={14} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Capabilities Grid */}
      {filteredCapabilities.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 bg-[#0d101740] border border-dashed border-slate-800 rounded-xl text-center">
          <Layers size={36} className="text-slate-600 mb-3" />
          <h4 className="text-sm font-semibold text-slate-300">No Capabilities Found</h4>
          <p className="text-xs text-slate-500 mt-1 max-w-sm">
            No platform capabilities match the search criteria. Try modifying your filter or search query.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCapabilities.map(cap => {
            const catConfig = CATEGORY_MAP[cap.capability_type] || { label: cap.capability_type, icon: Cpu, color: 'text-slate-400 bg-slate-500/10 border-slate-500/20' };
            const Icon = catConfig.icon;
            const isSelected = selectedCapability?.capability_id === cap.capability_id;
            const specializedRoute = SPECIALIZED_ROUTES[cap.capability_type];

            return (
              <div
                key={cap.capability_id}
                onClick={() => onSelectCapability(cap)}
                className={`flex flex-col justify-between p-5 rounded-xl border transition-all cursor-pointer group relative overflow-hidden ${
                  isSelected 
                    ? 'bg-[#101726] border-cyan-500/50 shadow-lg shadow-cyan-500/5 ring-1 ring-cyan-500/30' 
                    : 'bg-[#0d101780] border-[rgba(255,255,255,0.06)] hover:border-slate-700 hover:bg-[#0f1420]'
                }`}
              >
                {/* Header */}
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg border shrink-0 ${catConfig.color}`}>
                        <Icon size={18} />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-100 group-hover:text-cyan-300 transition-colors">
                          {cap.name}
                        </h4>
                        <span className="font-mono text-[10px] text-slate-400">
                          {cap.capability_id}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {cap.enabled ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 size={10} /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          <XCircle size={10} /> Disabled
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-4">
                    {cap.description || 'No detailed description provided.'}
                  </p>

                  {/* Tags */}
                  {cap.tags && cap.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-4">
                      {cap.tags.slice(0, 4).map(tag => (
                        <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-white/5 text-slate-400 border border-white/5">
                          <Tag size={9} /> {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer Controls */}
                <div className="flex items-center justify-between pt-3 border-t border-[rgba(255,255,255,0.06)] text-xs">
                  <div className="flex items-center gap-2 text-slate-500 text-[11px]">
                    <Shield size={12} className="text-slate-400" />
                    <span>v{cap.version}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {specializedRoute && (
                      <Link
                        to={specializedRoute.path}
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-all"
                        title={`Open in ${specializedRoute.label}`}
                      >
                        <ExternalLink size={14} />
                      </Link>
                    )}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectCapability(cap);
                        if (onOpenExecute) onOpenExecute(cap);
                      }}
                      className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer"
                    >
                      <Play size={11} className="fill-current" /> Execute
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
