import React, { useState, useEffect } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer
} from 'recharts';
import { 
  BarChart2, 
  Activity, 
  Clock, 
  AlertTriangle, 
  Cpu, 
  CheckCircle2, 
  RefreshCw, 
  Zap, 
  BrainCircuit, 
  ShieldAlert,
  Server,
  Layers
} from 'lucide-react';
import { 
  getPlatformOverviewMetrics, 
  getPlatformCapabilityAnalytics, 
  getPlatformFailureAnalytics, 
  getPlatformIntelligenceAnalytics 
} from '../../api/platform';
import { 
  MetricCard, 
  Badge, 
  StatusBadge, 
  Card, 
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  EmptyState,
  Button
} from '../../components/ui';

export default function AdminAnalytics() {
  const [timeWindow, setTimeWindow] = useState('24h');
  const [overview, setOverview] = useState(null);
  const [capabilities, setCapabilities] = useState(null);
  const [failures, setFailures] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovData, capData, failData, intelData] = await Promise.all([
        getPlatformOverviewMetrics(timeWindow),
        getPlatformCapabilityAnalytics(timeWindow),
        getPlatformFailureAnalytics(timeWindow),
        getPlatformIntelligenceAnalytics(timeWindow)
      ]);
      setOverview(ovData);
      setCapabilities(capData);
      setFailures(failData);
      setIntelligence(intelData);
    } catch (err) {
      console.error('Failed to load platform analytics:', err);
      setError('Failed to fetch platform telemetry data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeWindow]);

  const capChartData = (capabilities?.capabilities || []).map(c => ({
    name: c.name || c.capability_name || 'Capability',
    executions: c.total_executions || 0,
    latency: c.avg_duration_ms || 0,
    success_rate: typeof c.success_rate === 'number' ? c.success_rate : 100,
    failures: c.failed_executions || 0
  }));

  const failureChartData = (failures?.failures || []).map(f => ({
    category: f.failure_category || f.category || 'Uncategorized',
    count: f.occurrence_count || f.count || 0
  }));

  const totalFailures = failureChartData.reduce((acc, curr) => acc + curr.count, 0);

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300 font-sans pb-12">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
              <BarChart2 size={20} className="text-purple-400" />
              Platform Telemetry & Performance Analytics
            </h2>
            <Badge variant="purple" size="xs">PROD TELEMETRY</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time execution latency percentiles, capability health distribution, intelligence planning confidence, and failure root cause analysis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-slate-900/80 border border-slate-700/50 rounded-lg p-1 text-xs" role="group" aria-label="Select Time Window">
            {['1h', '24h', '7d', '30d'].map((w) => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                className={`px-3 py-1 rounded text-xs font-semibold cursor-pointer transition-all ${
                  timeWindow === w 
                    ? 'bg-purple-600/30 text-purple-300 font-bold border border-purple-500/40 shadow-sm' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {w}
              </button>
            ))}
          </div>

          <button 
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 text-xs font-mono bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 px-3 py-2 rounded-lg text-slate-300 hover:text-white transition-colors cursor-pointer"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin text-purple-400' : ''} /> 
            REFRESH
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/40 flex items-center justify-between text-rose-300 text-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-rose-400" />
            <span>{error}</span>
          </div>
          <button onClick={fetchData} className="px-3 py-1 bg-rose-600/30 hover:bg-rose-600/50 text-xs font-semibold rounded text-white cursor-pointer">
            Retry
          </button>
        </div>
      )}

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Executions"
          value={(overview?.total_executions ?? 0).toLocaleString()}
          icon={<Zap size={18} className="text-cyan-400" />}
          trend={{
            direction: 'up',
            value: `${overview?.success_rate ?? 100}% success`
          }}
          description={`Time window: ${timeWindow}`}
        />

        <MetricCard
          title="Average Latency"
          value={`${overview?.avg_duration_ms ?? 0} ms`}
          icon={<Clock size={18} className="text-purple-400" />}
          trend={{
            direction: 'neutral',
            value: `P95: ${overview?.p95_duration_ms ?? 0} ms`
          }}
          description="End-to-end task time"
        />

        <MetricCard
          title="Execution Failures"
          value={(overview?.failed_executions ?? 0).toLocaleString()}
          icon={<AlertTriangle size={18} className="text-rose-400" />}
          trend={{
            direction: (overview?.failed_executions ?? 0) > 0 ? 'down' : 'neutral',
            value: `${overview?.denied_executions ?? 0} security denials`
          }}
          description="Exceptions & timeouts"
        />

        <MetricCard
          title="Intelligence Confidence"
          value={`${((intelligence?.avg_confidence ?? 1.0) * 100).toFixed(1)}%`}
          icon={<BrainCircuit size={18} className="text-emerald-400" />}
          trend={{
            direction: 'up',
            value: `${intelligence?.avg_adaptive_attempts ?? 1} avg steps`
          }}
          description="Planning accuracy"
        />
      </div>

      {/* Primary Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Capability Execution Chart */}
        <div className="glass-panel p-5 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider font-mono">
              <Activity size={15} className="text-cyan-400" />
              Capability Execution Volume
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              {capChartData.length} capabilities tracked
            </span>
          </div>

          <div className="h-64 w-full text-[11px] font-mono">
            {capChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-500">
                No execution data recorded for window: {timeWindow}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={capChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#0f172a', 
                      borderColor: '#334155', 
                      borderRadius: '8px', 
                      color: '#f8fafc',
                      fontSize: '12px'
                    }} 
                  />
                  <Bar dataKey="executions" fill="#00f0ff" radius={[4, 4, 0, 0]} name="Executions" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
          
          <div className="text-[11px] text-slate-400 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60 flex items-center justify-between">
            <span>Aggregated capability invocation volume over {timeWindow}.</span>
            <span className="text-cyan-400 font-mono font-medium">Auto-refreshes on window change</span>
          </div>
        </div>

        {/* Failure Root-Cause Breakdown */}
        <div className="glass-panel p-5 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider font-mono">
              <ShieldAlert size={15} className="text-rose-400" />
              Failure Root-Cause Distribution
            </div>
            <span className="text-[11px] text-rose-400/90 font-mono">
              {totalFailures} total errors
            </span>
          </div>

          <div className="h-64 w-full text-[11px] font-mono">
            {failureChartData.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-emerald-400/90 gap-2">
                <CheckCircle2 size={28} className="text-emerald-400" />
                <span className="text-xs font-medium">Zero platform failures recorded for this timeframe.</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={failureChartData} layout="vertical" margin={{ top: 10, right: 20, left: 40, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="category" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#0f172a', 
                      borderColor: '#334155', 
                      borderRadius: '8px', 
                      color: '#f8fafc',
                      fontSize: '12px'
                    }} 
                  />
                  <Bar dataKey="count" fill="#ff0055" radius={[0, 4, 4, 0]} name="Failures" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="text-[11px] text-slate-400 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60 flex items-center justify-between">
            <span>Root-cause categorization for timeouts, tool errors, and authorization blocks.</span>
            <span className="text-rose-400 font-mono font-medium">SOC monitored</span>
          </div>
        </div>

      </div>

      {/* Detailed Capability Table */}
      <div className="glass-panel p-5 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider font-mono">
            <Layers size={15} className="text-purple-400" />
            Capability Performance & Reliability Matrix
          </div>
          <Badge variant="cyan" size="xs">LIVE TELEMETRY</Badge>
        </div>

        {capChartData.length === 0 ? (
          <EmptyState
            title="No Capability Data"
            description={`No execution metrics found for the selected time range (${timeWindow}).`}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Capability Name</th>
                  <th className="py-3 px-4 text-right">Executions</th>
                  <th className="py-3 px-4 text-right">Avg Duration</th>
                  <th className="py-3 px-4 text-center">Success Rate</th>
                  <th className="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {capChartData.map((cap, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-white flex items-center gap-2">
                      <Server size={13} className="text-slate-500" />
                      {cap.name}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-cyan-300">
                      {cap.executions.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-300">
                      {cap.latency} ms
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        cap.success_rate >= 95 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        cap.success_rate >= 80 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}>
                        {cap.success_rate}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <StatusBadge status={cap.success_rate >= 90 ? 'healthy' : 'warning'} size="xs" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
