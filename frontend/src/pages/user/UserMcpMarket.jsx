import React, { useState } from 'react';
import { Server, Search, CheckCircle, Wifi, RefreshCw, Power, Plus, Lock } from 'lucide-react';

export default function UserMcpMarket({ triggerNotification }) {
  const [search, setSearch] = useState('');
  const [integrations, setIntegrations] = useState([
    { name: 'GitHub Server', desc: 'Read repository issues, PR audits, and commit hooks.', type: 'VCS', latency: '24ms', requests: 1240, status: 'connected', health: 100 },
    { name: 'AWS Cloud Registry', desc: 'Interact with cloud S3 directories and monitor EC2.', type: 'Cloud', latency: '48ms', requests: 832, status: 'connected', health: 98 },
    { name: 'Slack Daemon', desc: 'Broadcast workflow outputs and pull user confirmations.', type: 'Comms', latency: '12ms', requests: 212, status: 'disconnected', health: 100 },
    { name: 'Notion Database Node', desc: 'Access vector tables and structured wikis.', type: 'Database', latency: '32ms', requests: 4320, status: 'connected', health: 100 },
    { name: 'MySQL Connector', desc: 'Execute database schema audits and query tables.', type: 'Database', latency: '18ms', requests: 9284, status: 'connected', health: 99 },
    { name: 'PostgreSQL Server', desc: 'Index relational columns and run analytical updates.', type: 'Database', latency: '14ms', requests: 124, status: 'disconnected', health: 100 },
    { name: 'Docker Daemon', desc: 'Provision mock virtual containers and check logs.', type: 'DevOps', latency: '8ms', requests: 88, status: 'connected', health: 100 },
    { name: 'Discord Webhook Hub', desc: 'Ping channels with debug alerts and threat matrix.', type: 'Comms', latency: '22ms', requests: 49, status: 'disconnected', health: 100 }
  ]);

  const handleToggleConnect = (name) => {
    setIntegrations(prev => prev.map(item => {
      if (item.name === name) {
        const nextStatus = item.status === 'connected' ? 'disconnected' : 'connected';
        triggerNotification(
          nextStatus === 'connected' ? 'MCP Connected' : 'MCP Terminated',
          `Daemon gateway for ${name} has been ${nextStatus === 'connected' ? 'activated' : 'paused'}.`
        );
        return {
          ...item,
          status: nextStatus,
          requests: nextStatus === 'connected' ? item.requests + 1 : item.requests
        };
      }
      return item;
    }));
  };

  const filtered = integrations.filter(item => 
    item.name.toLowerCase().includes(search.toLowerCase()) || 
    item.type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      
      {/* Top Header & Search bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">Model Context Protocol (MCP) Marketplace</h2>
          <p className="text-xs text-slate-400 mt-1">Connect your AI operating system directly to external platforms, databases, and runtimes.</p>
        </div>

        <div className="relative group">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter MCP servers... (e.g. Database)"
            className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-1.5 pl-9 pr-4 text-xs text-slate-300 w-64 outline-none focus:border-cyan-500/30 transition-all"
          />
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Active Connections', value: integrations.filter(i => i.status === 'connected').length.toString(), detail: 'Nodes synchronized' },
          { label: 'Marketplace registries', value: integrations.length.toString(), detail: 'Available servers' },
          { label: 'Average Ping Latency', value: '24.8ms', detail: 'Local network link' },
          { label: 'Total API Requests', value: '16.1k', detail: 'Accumulated logs' }
        ].map((stat, idx) => (
          <div key={idx} className="glass-panel p-4 flex flex-col gap-1">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">{stat.label}</span>
            <span className="text-xl font-bold text-white mt-1">{stat.value}</span>
            <span className="text-[9px] text-slate-500">{stat.detail}</span>
          </div>
        ))}
      </div>

      {/* Grid of integrations */}
      <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-4">
        {filtered.map((item, idx) => {
          const isConnected = item.status === 'connected';
          return (
            <div key={idx} className={`glass-panel p-5 flex flex-col justify-between hover:-translate-y-0.5 transition-all ${isConnected ? 'border-cyan-500/10' : 'border-transparent'}`}>
              <div>
                <div className="flex justify-between items-start">
                  <div className="w-8 h-8 rounded-lg bg-white/3 flex items-center justify-center border border-[rgba(255,255,255,0.04)] shrink-0">
                    <Server size={14} className={isConnected ? 'text-cyan-400' : 'text-slate-400'} />
                  </div>
                  <span className="text-[9px] font-bold text-slate-500 bg-white/3 px-2 py-0.5 rounded uppercase tracking-wider">{item.type}</span>
                </div>

                <h4 className="text-xs font-bold text-white tracking-wide mt-3">{item.name}</h4>
                <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed line-clamp-2">{item.desc}</p>
              </div>

              {/* Server stats indicators */}
              <div className="mt-5 border-t border-[rgba(255,255,255,0.04)] pt-4 flex flex-col gap-3">
                <div className="grid grid-cols-3 gap-2 text-[10px]">
                  <div>
                    <span className="text-slate-500 block">Latency</span>
                    <span className="font-semibold text-white font-mono">{isConnected ? item.latency : '--'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Health</span>
                    <span className="font-semibold text-white font-mono">{isConnected ? `${item.health}%` : '--'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Queries</span>
                    <span className="font-semibold text-white font-mono">{isConnected ? item.requests : '--'}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-1">
                  <div className="flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-cyan-400 animate-pulse' : 'bg-slate-500'}`}></span>
                    <span className="text-[9px] text-slate-500 uppercase font-semibold">{item.status}</span>
                  </div>

                  <button
                    onClick={() => handleToggleConnect(item.name)}
                    className={`btn-secondary py-1 px-3 rounded-lg text-[10px] gap-1 cursor-pointer ${isConnected ? 'hover:border-rose-500/20 text-rose-400' : 'hover:border-cyan-500/20 text-cyan-400'}`}
                  >
                    <Power size={10} />
                    {isConnected ? 'DISCONNECT' : 'CONNECT'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
