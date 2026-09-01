import React, { useState, useEffect } from 'react';
import { 
  Cpu, 
  Users, 
  Server, 
  Activity, 
  Settings, 
  Database, 
  Clock, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Workflow, 
  BrainCircuit, 
  ShieldAlert,
  ArrowUpRight,
  TrendingUp
} from 'lucide-react';
import { 
  getAdminOverview, 
  getAdminSystemHealth, 
  getAdminActivityFeed 
} from '../../api/admin';

export default function AdminDashboard() {
  const [timeWindow, setTimeWindow] = useState('24h');
  const [overview, setOverview] = useState(null);
  const [health, setHealth] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovData, healthData, actData] = await Promise.all([
        getAdminOverview(timeWindow),
        getAdminSystemHealth(),
        getAdminActivityFeed(15)
      ]);
      setOverview(ovData);
      setHealth(healthData);
      setActivity(actData.events || []);
    } catch (err) {
      setError(err?.message || 'Failed to fetch administrator data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeWindow]);

  const metrics = [
    { 
      label: 'System Status', 
      value: overview?.system_status || 'ONLINE', 
      detail: `Environment: ${health?.environment || 'Production'}`,
      icon: <Activity size={18} className="text-purple-400" />
    },
    { 
      label: 'Active Users', 
      value: (overview?.active_users ?? 0).toLocaleString(), 
      detail: `Total registered: ${(overview?.total_users ?? 0).toLocaleString()}`,
      icon: <Users size={18} className="text-cyan-400" />
    },
    { 
      label: 'Executions Volume', 
      value: (overview?.total_executions ?? 0).toLocaleString(), 
      detail: `Success rate: ${overview?.success_rate ?? 100}%`,
      icon: <BrainCircuit size={18} className="text-emerald-400" />
    },
    { 
      label: 'Avg Response Latency', 
      value: `${overview?.avg_latency_ms ?? 0} ms`, 
      detail: `Capabilities: ${overview?.active_capabilities ?? 0} active`,
      icon: <TrendingUp size={18} className="text-amber-400" />
    }
  ];

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Activity size={20} className="text-purple-400" />
            Enterprise Operations Center
          </h2>
          <p className="text-xs text-slate-500 mt-1">Live platform diagnostics, subsystem health matrix, execution volume, and audit stream.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex bg-white/5 border border-[rgba(255,255,255,0.06)] rounded-lg p-1 text-xs">
            {['1h', '24h', '7d', '30d'].map((w) => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                className={`px-3 py-1 rounded text-xs font-semibold cursor-pointer transition-all ${timeWindow === w ? 'bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30' : 'text-slate-400 hover:text-white'}`}
              >
                {w}
              </button>
            ))}
          </div>

          <button 
            onClick={fetchData}
            disabled={loading}
            className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white transition-all"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> SYNC_METRICS
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle size={14} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid Stats indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, idx) => (
          <div key={idx} className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">{m.label}</span>
              {m.icon}
            </div>
            <div className="text-2xl font-mono font-bold text-white mt-2">{m.value}</div>
            <span className="text-[10px] text-slate-400 mt-2 block font-mono">{m.detail}</span>
          </div>
        ))}
      </div>

      {/* Subsystem Health Diagnostic Grid */}
      <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col gap-4">
        <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-3">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Cpu size={14} className="text-purple-400" />
            Subsystem Health & Dependency Diagnostics
          </h4>
          <span className="text-[10px] font-mono text-slate-500">Live Heartbeat Ping</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {(health?.subsystems || []).map((sub, idx) => {
            const isOnline = sub.status === 'ONLINE';
            const isDegraded = sub.status === 'DEGRADED';
            return (
              <div key={idx} className="flex flex-col gap-2 p-3 rounded-lg bg-black/30 border border-[rgba(255,255,255,0.04)]">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-200">{sub.name}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${isOnline ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : (isDegraded ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20')}`}>
                    {sub.status}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 mt-1">
                  <span>Latency: {sub.latency_ms}ms</span>
                  <span>{Object.keys(sub.details || {}).length} attrs</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two Column Layout: Executions & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Operations Summary */}
        <div className="lg:col-span-1 glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col gap-4">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
            <Server size={14} className="text-cyan-400" />
            Resource Topology
          </h4>
          
          <div className="flex flex-col gap-3 text-xs">
            <div className="flex justify-between p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)]">
              <span className="text-slate-400">Total Workspaces</span>
              <span className="font-mono font-bold text-white">{overview?.total_workspaces ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)]">
              <span className="text-slate-400">Active Workflows</span>
              <span className="font-mono font-bold text-white">{overview?.active_workflows ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)]">
              <span className="text-slate-400">Registered MCP Daemons</span>
              <span className="font-mono font-bold text-white">{overview?.active_mcp_servers ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)]">
              <span className="text-slate-400">Platform Capabilities</span>
              <span className="font-mono font-bold text-white">{overview?.active_capabilities ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)]">
              <span className="text-slate-400">Security / System Alerts</span>
              <span className={`font-mono font-bold ${(overview?.alerts_count ?? 0) > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {overview?.alerts_count ?? 0}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Live Activity Stream */}
        <div className="lg:col-span-2 glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col gap-4">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
            <Clock size={14} className="text-purple-400" />
            Recent Administrative & Execution Activity
          </h4>
          
          <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1">
            {activity.length === 0 ? (
              <div className="text-xs text-slate-500 py-6 text-center">No recent activity events recorded.</div>
            ) : (
              activity.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center text-xs p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.03)] hover:border-purple-500/20 transition-all font-mono">
                  <div className="flex items-center gap-3">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
                    <span className="font-semibold text-slate-200">{item.summary}</span>
                  </div>
                  <div className="flex items-center gap-4 text-slate-500 text-[10px] shrink-0">
                    <span className="bg-white/5 px-2 py-0.5 rounded">{item.source_component}</span>
                    <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
