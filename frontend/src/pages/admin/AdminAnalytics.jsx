import React, { useState, useEffect } from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  BarChart, 
  Bar 
} from 'recharts';
import { TrendingUp, BarChart2, Database, RefreshCw, AlertTriangle, Cpu, CheckCircle } from 'lucide-react';
import { 
  getPlatformOverviewMetrics, 
  getPlatformCapabilityAnalytics, 
  getPlatformFailureAnalytics, 
  getPlatformIntelligenceAnalytics 
} from '../../api/platform';

export default function AdminAnalytics() {
  const [timeWindow, setTimeWindow] = useState('24h');
  const [overview, setOverview] = useState(null);
  const [capabilities, setCapabilities] = useState(null);
  const [failures, setFailures] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeWindow]);

  const capChartData = (capabilities?.capabilities || []).map(c => ({
    name: c.name,
    executions: c.total_executions,
    latency: c.avg_duration_ms,
    success_rate: c.success_rate
  }));

  const failureChartData = (failures?.failures || []).map(f => ({
    category: f.failure_category,
    count: f.occurrence_count
  }));

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300 font-sans">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <BarChart2 size={20} className="text-purple-400" />
            System Performance & Telemetry Analytics
          </h2>
          <p className="text-xs text-slate-500 mt-1">Execution latency trends, capability failure ratios, and intelligence planning distribution.</p>
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
            className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> REFRESH
          </button>
        </div>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Total Executions</span>
          <div className="text-2xl font-mono font-bold text-white mt-1">{(overview?.total_executions ?? 0).toLocaleString()}</div>
          <span className="text-[10px] text-slate-400 mt-1 block">Success rate: {overview?.success_rate ?? 100}%</span>
        </div>

        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Average Latency</span>
          <div className="text-2xl font-mono font-bold text-cyan-400 mt-1">{overview?.avg_duration_ms ?? 0} ms</div>
          <span className="text-[10px] text-slate-400 mt-1 block">P95: {overview?.p95_duration_ms ?? 0} ms</span>
        </div>

        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Failed Executions</span>
          <div className="text-2xl font-mono font-bold text-rose-400 mt-1">{(overview?.failed_executions ?? 0).toLocaleString()}</div>
          <span className="text-[10px] text-slate-400 mt-1 block">Denials: {overview?.denied_executions ?? 0}</span>
        </div>

        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Intelligence Confidence</span>
          <div className="text-2xl font-mono font-bold text-purple-400 mt-1">{((intelligence?.avg_confidence ?? 1.0) * 100).toFixed(1)}%</div>
          <span className="text-[10px] text-slate-400 mt-1 block">Avg adaptive attempts: {intelligence?.avg_adaptive_attempts ?? 1}</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Capability Execution Chart */}
        <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl h-80 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-[rgba(255,255,255,0.04)] font-mono">
            <TrendingUp size={14} className="text-cyan-400" />
            Capability Execution Breakdown
          </div>
          <div className="flex-1 w-full text-[10px] font-mono">
            {capChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-500">No execution data recorded.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={capChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.02)" />
                  <XAxis dataKey="name" stroke="#57657d" />
                  <YAxis stroke="#57657d" />
                  <Tooltip contentStyle={{ backgroundColor: '#0d1017', borderColor: 'rgba(255,255,255,0.06)', borderRadius: '8px' }} />
                  <Bar dataKey="executions" fill="#00f0ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Failure Breakdown Chart */}
        <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl h-80 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-[rgba(255,255,255,0.04)] font-mono">
            <AlertTriangle size={14} className="text-rose-400" />
            Failure Category Distribution
          </div>
          <div className="flex-1 w-full text-[10px] font-mono">
            {failureChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-emerald-400/80">Zero platform failures reported for this timeframe.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={failureChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.02)" />
                  <XAxis dataKey="category" stroke="#57657d" />
                  <YAxis stroke="#57657d" />
                  <Tooltip contentStyle={{ backgroundColor: '#0d1017', borderColor: 'rgba(255,255,255,0.06)', borderRadius: '8px' }} />
                  <Bar dataKey="count" fill="#ff0055" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
