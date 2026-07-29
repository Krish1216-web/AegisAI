import React, { useState } from 'react';
import { Bot, Search, Star, Download, Sparkles, CheckCircle, ShieldCheck } from 'lucide-react';

export default function UserAiMarket({ triggerNotification }) {
  const [search, setSearch] = useState('');
  const [agents, setAgents] = useState([
    { name: 'Coding Agent', desc: 'Refactor typescript repositories, build components, and audit files.', version: 'v2.4.1', rating: 4.9, downloads: '14.8k', dev: 'Aegis Core Team', status: 'installed' },
    { name: 'DevOps & CI/CD Agent', desc: 'Monitor GitHub workflows, docker files, and manage cloud setups.', version: 'v1.8.0', rating: 4.7, downloads: '6.2k', dev: 'Aegis Core Team', status: 'available' },
    { name: 'Data Science Analyst', desc: 'Plot Recharts grids, parse CSV files, and generate math equations.', version: 'v1.5.0', rating: 4.8, downloads: '9.1k', dev: 'OpenAI Studio', status: 'available' },
    { name: 'Financial Auditor', desc: 'Scan ledger files, track storage expenses, and generate sheets.', version: 'v2.1.0', rating: 4.6, downloads: '3.4k', dev: 'Vercel Labs', status: 'installed' },
    { name: 'Medical Research Assistant', desc: 'Decompose medical papers, summarize terms, and search studies.', version: 'v1.1.2', rating: 4.9, downloads: '1.2k', dev: 'Anthropic Guild', status: 'available' },
    { name: 'Legal compliance Audit Node', desc: 'Cross-reference corporate documents and check privacy matrices.', version: 'v1.0.4', rating: 4.5, downloads: '890', dev: 'Cursor Devs', status: 'available' }
  ]);

  const handleInstall = (name) => {
    setAgents(prev => prev.map(ag => {
      if (ag.name === name) {
        const nextStatus = ag.status === 'installed' ? 'available' : 'installed';
        triggerNotification(
          nextStatus === 'installed' ? 'Agent Installed' : 'Agent Uninstalled',
          `${name} has been ${nextStatus === 'installed' ? 'added to your active workspace' : 'removed'}.`
        );
        return { ...ag, status: nextStatus };
      }
      return ag;
    }));
  };

  const filtered = agents.filter(item => 
    item.name.toLowerCase().includes(search.toLowerCase()) || 
    item.dev.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      
      {/* Top Header & Search */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">AI Agent Center & Marketplace</h2>
          <p className="text-xs text-slate-400 mt-1">Acquire and deploy specialized autonomous agents to handle complex enterprise assignments.</p>
        </div>

        <div className="relative group">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search AI agents... (e.g. Coding)"
            className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-1.5 pl-9 pr-4 text-xs text-slate-300 w-64 outline-none focus:border-cyan-500/30 transition-all"
          />
        </div>
      </div>

      {/* Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Installed Agents', value: agents.filter(a => a.status === 'installed').length.toString(), detail: 'Available in chat workspaces' },
          { label: 'Available Plugins', value: agents.length.toString(), detail: 'Certified registry nodes' },
          { label: 'Daily Agent Operations', value: '43,921', detail: 'Total active execution threads' }
        ].map((stat, idx) => (
          <div key={idx} className="glass-panel p-4 flex flex-col gap-1">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">{stat.label}</span>
            <span className="text-xl font-bold text-white mt-1">{stat.value}</span>
            <span className="text-[9px] text-slate-500">{stat.detail}</span>
          </div>
        ))}
      </div>

      {/* Grid of Agents */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((item, idx) => {
          const isInstalled = item.status === 'installed';
          return (
            <div key={idx} className={`glass-panel p-5 flex flex-col justify-between hover:-translate-y-0.5 transition-all ${isInstalled ? 'border-cyan-500/10' : 'border-transparent'}`}>
              <div>
                <div className="flex justify-between items-start">
                  <div className="w-8 h-8 rounded-lg bg-white/3 flex items-center justify-center border border-[rgba(255,255,255,0.04)] shrink-0">
                    <Bot size={14} className={isInstalled ? 'text-cyan-400' : 'text-slate-400'} />
                  </div>
                  <span className="text-[9px] font-bold text-slate-500 bg-white/3 px-2 py-0.5 rounded font-mono">{item.version}</span>
                </div>

                <h4 className="text-xs font-bold text-white mt-3 flex items-center gap-1.5">
                  {item.name}
                  {isInstalled && <ShieldCheck size={12} className="text-cyan-400" />}
                </h4>
                <span className="text-[9px] text-slate-500 uppercase tracking-wider block mt-1">Dev: {item.dev}</span>
                <p className="text-[11px] text-slate-400 mt-2.5 leading-relaxed line-clamp-3">{item.desc}</p>
              </div>

              {/* Install and rating actions */}
              <div className="mt-6 border-t border-[rgba(255,255,255,0.04)] pt-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1 text-[10px] text-yellow-400">
                    <Star size={10} fill="currentColor" />
                    <span className="font-semibold">{item.rating}</span>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-slate-500">
                    <Download size={10} />
                    <span>{item.downloads}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleInstall(item.name)}
                  className={`btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 cursor-pointer font-semibold ${isInstalled ? 'hover:border-rose-500/20 text-rose-400' : 'hover:border-cyan-500/20 text-cyan-400'}`}
                >
                  {isInstalled ? 'UNINSTALL' : 'INSTALL'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
