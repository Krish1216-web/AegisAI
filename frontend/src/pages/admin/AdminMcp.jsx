import React, { useState } from 'react';
import { Server, Power, Activity, ShieldCheck, RefreshCcw, Plus, Lock } from 'lucide-react';

export default function AdminMcp({ addLog }) {
  const [servers, setServers] = useState([
    { id: 'file', name: 'File System Daemon', cmd: 'npx -y @modelcontextprotocol/server-filesystem', status: 'active', latency: '2ms', requests: 1420, errors: 0, sync: '12s ago' },
    { id: 'browser', name: 'Secure Browser Crawler', cmd: 'npx -y @modelcontextprotocol/server-playwright', status: 'active', latency: '124ms', requests: 382, errors: 4, sync: '45s ago' },
    { id: 'db', name: 'SQL Knowledge Store', cmd: 'python -m mcp_sqlite_server', status: 'inactive', latency: '---', requests: 0, errors: 0, sync: '---' },
    { id: 'github', name: 'GitHub Code Integration', cmd: 'npx -y @modelcontextprotocol/server-github', status: 'active', latency: '82ms', requests: 124, errors: 2, sync: '2m ago' }
  ]);

  const handleToggleServer = (serverId, name) => {
    setServers(prev => prev.map(s => {
      if (s.id === serverId) {
        const nextStatus = s.status === 'active' ? 'inactive' : 'active';
        addLog('SYS', `MCP Server [${name}] has been toggled to: ${nextStatus.toUpperCase()}`, 'info');
        return { ...s, status: nextStatus, latency: nextStatus === 'inactive' ? '---' : '15ms' };
      }
      return s;
    }));
  };

  const handleRunHealthCheck = (name) => {
    addLog('SYS', `Running diagnostic checks on server: ${name}...`, 'info');
    alert(`Handshake diagnostics success for daemon: ${name}. Connection stable.`);
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Header title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Server size={20} className="text-purple-400" />
            Model Context Protocol Registry
          </h2>
          <p className="text-xs text-slate-500 mt-1">Configure external tool integrations, audit daemon subprocesses, and test API pings.</p>
        </div>
        <button 
          onClick={() => alert('Add new MCP registry schema...')}
          className="btn-primary text-xs flex items-center gap-2 cursor-pointer shadow-lg shadow-purple-500/10 border-none"
        >
          <Plus size={14} /> REGISTER_SERVER
        </button>
      </div>

      {/* Grid Server Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {servers.map((s) => (
          <div key={s.id} className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.04)] flex flex-col gap-3 hover:border-purple-500/20 transition-all">
            
            {/* Header */}
            <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.04)] pb-2">
              <div className="flex items-center gap-2.5">
                <span className={`w-2 h-2 rounded-full ${s.status === 'active' ? 'bg-green-400 animate-pulse' : 'bg-rose-500'}`}></span>
                <span className="font-bold text-white text-sm">{s.name}</span>
              </div>
              <span className="text-[9px] text-slate-500 font-mono">Sync: {s.sync}</span>
            </div>

            {/* Config Command */}
            <div className="p-2 rounded bg-black/40 border border-[rgba(255,255,255,0.04)] font-mono text-[9px] text-slate-400 truncate">
              CMD: <code>{s.cmd}</code>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 text-xs font-mono">
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] text-slate-500 uppercase">Latency</span>
                <span className="text-slate-300">{s.latency}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] text-slate-500 uppercase">Requests</span>
                <span className="text-slate-300">{s.requests}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] text-slate-500 uppercase">Errors</span>
                <span className={s.errors > 0 ? 'text-rose-400' : 'text-slate-300'}>{s.errors}</span>
              </div>
            </div>

            {/* Controls */}
            <div className="flex justify-between items-center border-t border-[rgba(255,255,255,0.03)] pt-3 mt-auto">
              <button
                onClick={() => handleToggleServer(s.id, s.name)}
                className={`p-1.5 rounded-lg border text-xs flex items-center gap-1.5 cursor-pointer transition-all ${s.status === 'active' ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}
              >
                <Power size={12} />
                {s.status === 'active' ? 'DISABLE' : 'ENABLE'}
              </button>
              
              <div className="flex gap-2">
                <button
                  onClick={() => handleRunHealthCheck(s.name)}
                  className="p-1.5 rounded bg-white/2 hover:bg-white/5 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white cursor-pointer text-[10px] flex items-center gap-1.5 font-mono"
                  title="Run handshakes health verification"
                >
                  <RefreshCcw size={10} /> DIAG_CHECK
                </button>
              </div>
            </div>

          </div>
        ))}
      </div>

    </div>
  );
}
