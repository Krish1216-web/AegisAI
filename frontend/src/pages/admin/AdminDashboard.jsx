import React from 'react';
import { Cpu, Users, Server, Activity, Settings, Database, Clock, RefreshCw } from 'lucide-react';

export default function AdminDashboard() {
  const metrics = [
    { label: 'System Health', value: '99.98%', detail: 'Uptime: 142h', status: 'normal' },
    { label: 'Total active users', value: '1,420', detail: '+124 this week', status: 'normal' },
    { label: 'MCP tool calls', value: '42,500', detail: 'Succeed: 99.8%', status: 'normal' },
    { label: 'Avg Latency', value: '14ms', detail: 'LLM Response', status: 'normal' }
  ];

  const gauges = [
    { label: 'CPU Usage', value: 42, color: 'bg-cyan-500' },
    { label: 'GPU Core Load', value: 78, color: 'bg-purple-500' },
    { label: 'RAM Allocated', value: 64, color: 'bg-emerald-500' },
    { label: 'SSD Storage', value: 24, color: 'bg-yellow-500' }
  ];

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Page Header */}
      <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Activity size={20} className="text-purple-400" />
            AegisAI Admin Operations Center
          </h2>
          <p className="text-xs text-slate-500 mt-1">Real-time enterprise metrics, system analytics, and security telemetry.</p>
        </div>
        <button 
          onClick={() => window.location.reload()}
          className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono"
        >
          <RefreshCw size={12} /> SYNC_METRICS
        </button>
      </div>

      {/* Grid Stats indicators */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {metrics.map((m, idx) => (
          <div key={idx} className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.04)]">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">{m.label}</span>
            <div className="text-xl font-mono font-bold text-white mt-1">{m.value}</div>
            <span className="text-[10px] text-slate-500 mt-1 block">{m.detail}</span>
          </div>
        ))}
      </div>

      {/* Server Telemetry Progress Gauges */}
      <div className="glass-panel p-5 bg-[#090b10ab] border-purple-500/10 flex flex-col gap-4">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Cpu size={14} className="text-purple-400" />
          Hardware Core Diagnostics
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {gauges.map((g, idx) => (
            <div key={idx} className="flex flex-col gap-2 p-3 rounded-lg bg-black/20 border border-[rgba(255,255,255,0.02)]">
              <div className="flex justify-between text-xs font-semibold text-slate-400">
                <span>{g.label}</span>
                <span className="font-mono">{g.value}%</span>
              </div>
              {/* Telemetry slider indicator */}
              <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                <div className={`h-full ${g.color} transition-all`} style={{ width: `${g.value}%` }}></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Audit Logs Ticker Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Active systems status */}
        <div className="lg:col-span-2 glass-panel p-5 bg-[#090b10ab] flex flex-col gap-4">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
            <Server size={14} className="text-cyan-400 animate-pulse" />
            Active MCP Daemon status
          </h4>
          <div className="flex flex-col gap-2">
            {[
              { name: 'Local File System Integration', status: 'Active', port: 'STDIO', latency: '2ms' },
              { name: 'Tavily Search API gateway', status: 'Active', port: 'STDIO/ENV', latency: '14ms' },
              { name: 'SQL Database Memory Server', status: 'Inactive', port: 'PORT_DISCON', latency: '---' }
            ].map((node, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)] font-mono">
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${node.status === 'Active' ? 'bg-green-400 animate-pulse' : 'bg-rose-500'}`}></span>
                  <span className="font-semibold text-slate-300">{node.name}</span>
                </div>
                <div className="flex items-center gap-4 text-slate-500">
                  <span>{node.port}</span>
                  <span>{node.latency}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Database memory metrics side */}
        <div className="glass-panel p-5 bg-[#090b10ab] flex flex-col gap-4">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
            <Database size={14} className="text-emerald-400" />
            Database Allocations
          </h4>
          
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1 text-xs">
              <span className="text-slate-500">Vector Storage:</span>
              <strong className="text-white font-mono">34.2 MB / 500 MB max</strong>
            </div>
            <div className="flex flex-col gap-1 text-xs">
              <span className="text-slate-500">SQLite Graph memory:</span>
              <strong className="text-white font-mono">1,420 relations indexed</strong>
            </div>
            <div className="flex flex-col gap-1 text-xs">
              <span className="text-slate-500">Active LLM API keys:</span>
              <strong className="text-white font-mono">Gemini_Key_Active ✓</strong>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
