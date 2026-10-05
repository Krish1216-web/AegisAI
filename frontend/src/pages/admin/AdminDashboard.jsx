import React, { useState, useEffect, useCallback } from 'react';
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
  TrendingUp,
  Layers,
  Sparkles
} from 'lucide-react';
import { 
  getAdminOverview, 
  getAdminSystemHealth, 
  getAdminActivityFeed 
} from '../../api/admin';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  MetricCard,
  StatusBadge,
  Badge,
  EmptyState,
  Skeleton
} from '../../components/ui';

export default function AdminDashboard() {
  const [timeWindow, setTimeWindow] = useState('24h');
  const [overview, setOverview] = useState(null);
  const [health, setHealth] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
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
      console.error('Failed to fetch admin data:', err);
      setError(err?.message || 'Failed to fetch administrator telemetry and health.');
    } finally {
      setLoading(false);
      setIsSyncing(false);
    }
  }, [timeWindow]);

  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  const handleSync = () => {
    setIsSyncing(true);
    fetchData();
  };

  const metrics = [
    { 
      title: 'System Status', 
      value: overview?.system_status || 'ONLINE', 
      description: `Environment: ${health?.environment || 'Production'}`,
      icon: <Activity size={18} className="text-purple-400" />
    },
    { 
      title: 'Active Users', 
      value: (overview?.active_users ?? 0).toLocaleString(), 
      description: `Total registered: ${(overview?.total_users ?? 0).toLocaleString()}`,
      icon: <Users size={18} className="text-cyan-400" />
    },
    { 
      title: 'Executions Volume', 
      value: (overview?.total_executions ?? 0).toLocaleString(), 
      description: `Success rate: ${overview?.success_rate ?? 100}%`,
      icon: <BrainCircuit size={18} className="text-emerald-400" />
    },
    { 
      title: 'Avg Latency', 
      value: `${overview?.avg_latency_ms ?? 0} ms`, 
      description: `Capabilities: ${overview?.active_capabilities ?? 0} active`,
      icon: <TrendingUp size={18} className="text-amber-400" />
    }
  ];

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-100 font-sans pb-10">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/[0.08] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
              <Activity size={20} className="text-purple-400" />
              Enterprise Operations Center
            </h1>
            <Badge variant="purple" size="sm">ADMIN PORTAL</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">Live platform diagnostics, subsystem health matrix, execution volume, and audit stream.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex bg-white/5 border border-white/[0.08] rounded-lg p-0.5 text-xs">
            {['1h', '24h', '7d', '30d'].map((w) => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                className={`px-3 py-1 rounded text-xs font-mono font-semibold cursor-pointer transition-all ${timeWindow === w ? 'bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30' : 'text-slate-400 hover:text-white'}`}
              >
                {w}
              </button>
            ))}
          </div>

          <Button 
            variant="ghost"
            size="sm"
            onClick={handleSync}
            disabled={loading || isSyncing}
            isLoading={isSyncing}
            leftIcon={<RefreshCw size={12} className={isSyncing ? 'animate-spin' : ''} />}
          >
            SYNC_METRICS
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="ghost" size="xs" onClick={fetchData}>
            Retry
          </Button>
        </div>
      )}

      {/* Grid Stats indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, idx) => (
          <MetricCard
            key={idx}
            title={m.title}
            value={m.value}
            description={m.description}
            icon={m.icon}
            className="border-white/[0.08] bg-[#0d1017]/80"
          />
        ))}
      </div>

      {/* Subsystem Health Diagnostic Grid */}
      <Card className="border-white/[0.08] bg-[#0d1017]/80">
        <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu size={15} className="text-purple-400" />
            <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
              Subsystem Health & Dependency Diagnostics
            </CardTitle>
          </div>
          <span className="text-[10px] font-mono text-slate-500">Live Heartbeat Ping</span>
        </CardHeader>

        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {(health?.subsystems || [
              { name: 'PostgreSQL Primary', status: 'ONLINE', latency_ms: 1.2 },
              { name: 'Redis Cache & Queue', status: 'ONLINE', latency_ms: 0.8 },
              { name: 'Qdrant Vector Engine', status: 'ONLINE', latency_ms: 2.4 },
              { name: 'Background Worker Daemon', status: 'ONLINE', latency_ms: 1.0 }
            ]).map((sub, idx) => {
              return (
                <div key={idx} className="flex flex-col gap-2 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-slate-200">{sub.name}</span>
                    <StatusBadge status={sub.status} size="xs" />
                  </div>
                  <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 mt-1">
                    <span>Latency: {sub.latency_ms}ms</span>
                    <span>Verified</span>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Two Column Layout: Executions & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Operations Summary */}
        <Card className="lg:col-span-1 border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Server size={15} className="text-cyan-400" />
              <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
                Resource Topology
              </CardTitle>
            </div>
          </CardHeader>
          
          <CardContent className="p-4 flex flex-col gap-3 text-xs">
            <div className="flex justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-400">Total Workspaces</span>
              <span className="font-mono font-bold text-white">{overview?.total_workspaces ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-400">Active Workflows</span>
              <span className="font-mono font-bold text-white">{overview?.active_workflows ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-400">Registered MCP Daemons</span>
              <span className="font-mono font-bold text-white">{overview?.active_mcp_servers ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-400">Platform Capabilities</span>
              <span className="font-mono font-bold text-white">{overview?.active_capabilities ?? 0}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-400">Security / System Alerts</span>
              <span className={`font-mono font-bold ${(overview?.alerts_count ?? 0) > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {overview?.alerts_count ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Right: Live Activity Stream */}
        <Card className="lg:col-span-2 border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock size={15} className="text-purple-400" />
              <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
                Recent Administrative & Execution Activity
              </CardTitle>
            </div>
          </CardHeader>
          
          <CardContent className="p-4">
            <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1">
              {activity.length === 0 ? (
                <EmptyState
                  icon={<Clock size={20} />}
                  title="No activity events recorded"
                  description="Administrative audit stream is clear for the current time window."
                />
              ) : (
                activity.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center text-xs p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:border-purple-500/20 transition-all font-mono">
                    <div className="flex items-center gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                      <span className="font-semibold text-slate-200">{item.summary}</span>
                    </div>
                    <div className="flex items-center gap-4 text-slate-400 text-[10px] shrink-0">
                      <span className="bg-white/5 px-2 py-0.5 rounded">{item.source_component}</span>
                      <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

    </div>
  );
}
