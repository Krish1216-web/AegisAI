import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  BarChart3,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Zap,
  Shield,
  Layers,
  Brain,
  FileText,
  RefreshCw,
  Search,
  Filter,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';

import {
  getPlatformOverviewMetrics,
  getPlatformCapabilityAnalytics,
  getPlatformLifecycleMetrics,
  getPlatformFailureAnalytics,
  getPlatformIntelligenceAnalytics,
  getPlatformProvenanceAnalytics,
  getPlatformBottleneckAnalytics,
  getPlatformAlerts
} from '../../api/platform';

export default function PlatformAnalyticsDashboard({ triggerNotification }) {
  const [timeWindow, setTimeWindow] = useState('24h');
  const [activeSection, setActiveSection] = useState('overview');
  const [isLoading, setIsLoading] = useState(true);

  // Analytics Data States
  const [overview, setOverview] = useState(null);
  const [capabilities, setCapabilities] = useState([]);
  const [lifecycle, setLifecycle] = useState(null);
  const [failures, setFailures] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [provenance, setProvenance] = useState(null);
  const [bottlenecks, setBottlenecks] = useState([]);
  const [alerts, setAlerts] = useState([]);

  // Capability Filters
  const [capSearch, setCapSearch] = useState('');
  const [capTypeFilter, setCapTypeFilter] = useState('all');

  const loadAllAnalytics = useCallback(async () => {
    try {
      setIsLoading(true);
      const [
        overviewRes,
        capRes,
        lifecycleRes,
        failureRes,
        intelRes,
        provRes,
        bottleneckRes,
        alertRes
      ] = await Promise.all([
        getPlatformOverviewMetrics(timeWindow),
        getPlatformCapabilityAnalytics(timeWindow),
        getPlatformLifecycleMetrics(timeWindow),
        getPlatformFailureAnalytics(timeWindow),
        getPlatformIntelligenceAnalytics(timeWindow),
        getPlatformProvenanceAnalytics(timeWindow),
        getPlatformBottleneckAnalytics(timeWindow),
        getPlatformAlerts(timeWindow)
      ]);

      setOverview(overviewRes);
      setCapabilities(capRes.items || []);
      setLifecycle(lifecycleRes);
      setFailures(failureRes);
      setIntelligence(intelRes);
      setProvenance(provRes);
      setBottlenecks(bottleneckRes.bottlenecks || []);
      setAlerts(alertRes.alerts || []);
    } catch (err) {
      console.error('Failed to load platform analytics:', err);
      if (triggerNotification) {
        triggerNotification('Analytics Error', 'Failed to retrieve observability metrics.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [timeWindow, triggerNotification]);

  useEffect(() => {
    loadAllAnalytics();
  }, [loadAllAnalytics]);

  const filteredCaps = capabilities.filter(c => {
    const matchesSearch = c.capability_id.toLowerCase().includes(capSearch.toLowerCase()) ||
                          c.capability_type.toLowerCase().includes(capSearch.toLowerCase());
    const matchesType = capTypeFilter === 'all' || c.capability_type.toLowerCase() === capTypeFilter.toLowerCase();
    return matchesSearch && matchesType;
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Top Header & Window Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-cyan-400" />
            Platform Observability & Telemetry
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time unified execution metrics, latency percentiles, failure clustering, and capability health.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Time Window Buttons */}
          <div className="flex items-center bg-black/40 border border-slate-700/60 rounded-lg p-1">
            {['1h', '24h', '7d', '30d'].map((w) => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                  timeWindow === w
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {w.toUpperCase()}
              </button>
            ))}
          </div>

          <button
            onClick={loadAllAnalytics}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-medium text-slate-200 rounded-lg transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-4 rounded-xl backdrop-blur-md">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Executions</span>
          <div className="text-2xl font-bold text-slate-100 mt-1.5">
            {overview ? overview.total_executions.toLocaleString() : '0'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">In window ({timeWindow})</span>
        </div>

        <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-4 rounded-xl backdrop-blur-md">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Success Rate</span>
          <div className="text-2xl font-bold text-emerald-400 mt-1.5">
            {overview ? `${overview.success_rate}%` : '0%'}
          </div>
          <span className="text-[10px] text-emerald-500/80 mt-1 block">
            {overview ? `${overview.successful_executions} completed` : '0'}
          </span>
        </div>

        <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-4 rounded-xl backdrop-blur-md">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Median Latency (P50)</span>
          <div className="text-2xl font-bold text-cyan-400 mt-1.5">
            {overview ? `${overview.median_duration_ms}ms` : '0ms'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Average: {overview ? `${overview.avg_duration_ms}ms` : '0ms'}</span>
        </div>

        <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-4 rounded-xl backdrop-blur-md">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">P95 Latency</span>
          <div className="text-2xl font-bold text-purple-400 mt-1.5">
            {overview ? `${overview.p95_duration_ms}ms` : '0ms'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">P99: {overview ? `${overview.p99_duration_ms}ms` : '0ms'}</span>
        </div>

        <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-4 rounded-xl backdrop-blur-md">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Failure Rate</span>
          <div className={`text-2xl font-bold mt-1.5 ${overview && overview.failure_rate > 10 ? 'text-rose-400' : 'text-slate-200'}`}>
            {overview ? `${overview.failure_rate}%` : '0%'}
          </div>
          <span className="text-[10px] text-rose-500/80 mt-1 block">
            {overview ? `${overview.failed_executions} failed` : '0'}
          </span>
        </div>

        <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-4 rounded-xl backdrop-blur-md">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Active Concurrency</span>
          <div className="text-2xl font-bold text-amber-400 mt-1.5">
            {overview ? overview.active_executions : 0}
          </div>
          <span className="text-[10px] text-amber-500/80 mt-1 block">Live executions</span>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-[rgba(255,255,255,0.08)] pb-2 overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview & Trends', icon: TrendingUp },
          { id: 'capabilities', label: 'Capability Performance', icon: Layers },
          { id: 'lifecycle', label: 'Lifecycle & Bottlenecks', icon: Clock },
          { id: 'intelligence', label: 'Intelligence & Decisions', icon: Brain },
          { id: 'provenance', label: 'Provenance & Evidence', icon: FileText },
          { id: 'failures', label: 'Failures & Alerts', icon: AlertTriangle }
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                activeSection === tab.id
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Active Section Views */}
      {activeSection === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Execution Trends Chart */}
          <div className="lg:col-span-2 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              Execution Volume Over Time
            </h3>
            <div className="h-64 w-full">
              {overview && overview.executions_over_time && overview.executions_over_time.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={overview.executions_over_time}>
                    <defs>
                      <linearGradient id="compGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                      </linearGradient>
                      <linearGradient id="failGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="timestamp" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Area type="monotone" dataKey="completed" stroke="#10b981" fillOpacity={1} fill="url(#compGrad)" name="Completed" />
                    <Area type="monotone" dataKey="failed" stroke="#ef4444" fillOpacity={1} fill="url(#failGrad)" name="Failed" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">
                  No execution telemetry in selected window
                </div>
              )}
            </div>
          </div>

          {/* Executions by Capability */}
          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              Executions by Capability
            </h3>
            <div className="flex flex-col gap-3 mt-1 overflow-y-auto max-h-64">
              {overview && Object.entries(overview.executions_per_capability || {}).length > 0 ? (
                Object.entries(overview.executions_per_capability).map(([capId, cnt]) => {
                  const pct = Math.round((cnt / (overview.total_executions || 1)) * 100);
                  return (
                    <div key={capId} className="flex flex-col gap-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-mono text-slate-300 truncate">{capId}</span>
                        <span className="text-slate-400 font-semibold">{cnt} ({pct}%)</span>
                      </div>
                      <div className="w-full bg-slate-800/80 rounded-full h-1.5">
                        <div className="bg-cyan-500 h-1.5 rounded-full" style={{ width: `${pct}%` }}></div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-slate-500 text-center py-8">No capability requests recorded</div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeSection === 'capabilities' && (
        <div className="flex flex-col gap-4 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md">
          {/* Table Header / Filters */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={capSearch}
                onChange={(e) => setCapSearch(e.target.value)}
                placeholder="Search capabilities..."
                className="w-full pl-9 pr-3 py-1.5 bg-black/40 border border-slate-700/60 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={capTypeFilter}
                onChange={(e) => setCapTypeFilter(e.target.value)}
                className="bg-black/40 border border-slate-700/60 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
              >
                <option value="all">All Types</option>
                <option value="rag">RAG</option>
                <option value="knowledge_graph">Knowledge Graph</option>
                <option value="mcp">MCP</option>
                <option value="agent">Agent</option>
                <option value="workflow">Workflow</option>
                <option value="intelligence">Intelligence</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto border border-slate-800 rounded-lg">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/60 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Capability ID</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3 text-right">Executions</th>
                  <th className="px-4 py-3 text-right">Success Rate</th>
                  <th className="px-4 py-3 text-right">P50 Latency</th>
                  <th className="px-4 py-3 text-right">P95 Latency</th>
                  <th className="px-4 py-3 text-center">Health</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredCaps.length > 0 ? (
                  filteredCaps.map((cap) => (
                    <tr key={cap.capability_id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-semibold text-cyan-300">{cap.capability_id}</td>
                      <td className="px-4 py-3">
                        <span className="font-sans px-2 py-0.5 bg-slate-800 text-slate-300 text-[10px] rounded">
                          {cap.capability_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-slate-200">{cap.execution_count}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={cap.success_rate >= 90 ? 'text-emerald-400' : cap.success_rate >= 70 ? 'text-amber-400' : 'text-rose-400'}>
                          {cap.success_rate}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-slate-300">{cap.median_latency_ms}ms</td>
                      <td className="px-4 py-3 text-right text-purple-300">{cap.p95_latency_ms}ms</td>
                      <td className="px-4 py-3 text-center font-sans">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          cap.health === 'HEALTHY'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : cap.health === 'WARNING'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : cap.health === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : 'bg-slate-700/40 text-slate-400 border border-slate-600'
                        }`}>
                          {cap.health}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500 font-sans">
                      No capabilities found matching criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeSection === 'lifecycle' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Stage Durations */}
          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              Lifecycle Stage Latencies
            </h3>
            <div className="flex flex-col gap-3 mt-2">
              {lifecycle && Object.entries(lifecycle.stage_durations_ms || {}).map(([stage, dur]) => (
                <div key={stage} className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-300">{stage}</span>
                    <span className="font-mono text-cyan-300">{dur}ms avg</span>
                  </div>
                  <div className="w-full bg-slate-800/80 rounded-full h-2">
                    <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full" style={{ width: `${Math.min((dur / 1000) * 100, 100)}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bottlenecks */}
          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              Active Bottlenecks & Recommendations
            </h3>
            <div className="flex flex-col gap-3 overflow-y-auto max-h-72">
              {bottlenecks.length > 0 ? (
                bottlenecks.map((b, idx) => (
                  <div key={idx} className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs text-amber-300 font-semibold">{b.capability_id}</span>
                      <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] rounded font-semibold">
                        {b.classification}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 font-sans">{b.recommendation}</p>
                    <div className="flex items-center gap-4 text-[11px] text-slate-400 mt-1">
                      <span>Avg: {b.avg_duration_ms}ms</span>
                      <span>P95: {b.p95_duration_ms}ms</span>
                      <span>Failure: {b.failure_rate}%</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-slate-500">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-2 opacity-80" />
                  No operational bottlenecks detected in the platform.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeSection === 'intelligence' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Brain className="w-4 h-4 text-cyan-400" />
              Intelligence Confidence Score
            </h3>
            <div className="flex flex-col items-center justify-center py-6">
              <div className="text-4xl font-extrabold text-cyan-400 font-mono">
                {intelligence ? Math.round(intelligence.avg_confidence * 100) : 85}%
              </div>
              <span className="text-xs text-slate-400 mt-2 font-medium">Average Plan Confidence</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs border-t border-slate-800 pt-3">
              <div className="flex justify-between text-slate-300">
                <span>High:</span>
                <span className="text-emerald-400 font-semibold">{intelligence ? intelligence.high_confidence_count : 0}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Medium:</span>
                <span className="text-amber-400 font-semibold">{intelligence ? intelligence.medium_confidence_count : 0}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Low:</span>
                <span className="text-rose-400 font-semibold">{intelligence ? intelligence.low_confidence_count : 0}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Insufficient:</span>
                <span className="text-rose-500 font-semibold">{intelligence ? intelligence.insufficient_confidence_count : 0}</span>
              </div>
            </div>
          </div>

          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              Execution Modes
            </h3>
            <div className="flex flex-col gap-3 mt-2">
              {intelligence && Object.entries(intelligence.execution_mode_distribution || {}).map(([mode, count]) => (
                <div key={mode} className="flex items-center justify-between p-3 bg-slate-900/50 border border-slate-800 rounded-lg">
                  <span className="text-xs font-semibold uppercase text-slate-300">{mode}</span>
                  <span className="font-mono text-xs font-bold text-cyan-300">{count} runs</span>
                </div>
              ))}
              {intelligence && Object.keys(intelligence.execution_mode_distribution || {}).length === 0 && (
                <div className="text-xs text-slate-500 text-center py-8">No intelligent executions recorded</div>
              )}
            </div>
          </div>

          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Adaptive Telemetry
            </h3>
            <div className="flex flex-col gap-2.5 text-xs text-slate-300">
              <div className="flex justify-between p-2.5 bg-slate-900/40 border border-slate-800 rounded">
                <span>Fallbacks Triggered:</span>
                <span className="font-mono font-bold text-amber-300">{intelligence ? intelligence.fallback_count : 0}</span>
              </div>
              <div className="flex justify-between p-2.5 bg-slate-900/40 border border-slate-800 rounded">
                <span>Search Broadenings:</span>
                <span className="font-mono font-bold text-cyan-300">{intelligence ? intelligence.retrieve_more_count : 0}</span>
              </div>
              <div className="flex justify-between p-2.5 bg-slate-900/40 border border-slate-800 rounded">
                <span>Contradictions Detected:</span>
                <span className="font-mono font-bold text-rose-400">{intelligence ? intelligence.contradiction_count : 0}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeSection === 'provenance' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              Evidence Source Distribution
            </h3>
            <div className="flex flex-col gap-3 mt-1">
              {provenance && Object.entries(provenance.source_distribution || {}).map(([src, count]) => (
                <div key={src} className="flex justify-between items-center p-2.5 bg-slate-900/50 border border-slate-800 rounded-lg text-xs">
                  <span className="font-mono text-slate-300">{src}</span>
                  <span className="font-bold text-cyan-400">{count} items</span>
                </div>
              ))}
              {provenance && Object.keys(provenance.source_distribution || {}).length === 0 && (
                <div className="text-xs text-slate-500 text-center py-8">No evidence items collected</div>
              )}
            </div>
          </div>

          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              Trust Level Distribution
            </h3>
            <div className="flex flex-col gap-3 mt-1">
              {provenance && Object.entries(provenance.trust_distribution || {}).map(([trust, count]) => (
                <div key={trust} className="flex justify-between items-center p-2.5 bg-slate-900/50 border border-slate-800 rounded-lg text-xs">
                  <span className="font-mono text-slate-300">{trust}</span>
                  <span className="font-bold text-purple-300">{count} citations</span>
                </div>
              ))}
              {provenance && Object.keys(provenance.trust_distribution || {}).length === 0 && (
                <div className="text-xs text-slate-500 text-center py-8">No citations in window</div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeSection === 'failures' && (
        <div className="flex flex-col gap-6">
          {/* Active Alerts */}
          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Platform Alerts ({alerts.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {alerts.length > 0 ? (
                alerts.map((alt) => (
                  <div key={alt.alert_id} className="p-3.5 bg-slate-900/70 border border-slate-800 rounded-lg flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200">{alt.title}</span>
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                        alt.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      }`}>
                        {alt.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{alt.description}</p>
                  </div>
                ))
              ) : (
                <div className="col-span-2 text-center py-6 text-xs text-slate-500">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto mb-1.5 opacity-80" />
                  All platform systems operate within acceptable thresholds. No alerts active.
                </div>
              )}
            </div>
          </div>

          {/* Sanitized Failure Clustering */}
          <div className="bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-5 rounded-xl backdrop-blur-md flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <XCircle className="w-4 h-4 text-rose-400" />
              Sanitized Error Occurrences
            </h3>
            <div className="overflow-x-auto border border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/60 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-2.5">Category</th>
                    <th className="px-4 py-2.5">Capability</th>
                    <th className="px-4 py-2.5">Sanitized Message</th>
                    <th className="px-4 py-2.5 text-right">Occurrences</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {failures && failures.recent_failures && failures.recent_failures.length > 0 ? (
                    failures.recent_failures.map((f, i) => (
                      <tr key={i} className="hover:bg-slate-800/30">
                        <td className="px-4 py-2.5">
                          <span className="px-2 py-0.5 bg-rose-500/10 text-rose-300 border border-rose-500/30 rounded text-[10px] font-sans">
                            {f.category}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-cyan-300">{f.capability_id}</td>
                        <td className="px-4 py-2.5 font-sans text-slate-300 truncate max-w-md">{f.normalized_message}</td>
                        <td className="px-4 py-2.5 text-right text-slate-200">{f.occurrences}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-slate-500 font-sans">
                        No failures recorded in selected window.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
