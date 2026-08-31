import React, { useState, useEffect } from 'react';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Zap,
  TrendingUp,
  BarChart3,
  Layers,
  Calendar,
  AlertCircle,
  RefreshCw,
  Search,
  Filter,
  ArrowUpRight,
  ShieldAlert,
  ChevronRight,
  GitBranch,
  Bot
} from 'lucide-react';
import {
  getWorkflowAnalyticsOverview,
  getWorkflowAnalyticsPerformance,
  getWorkflowAnalyticsNodes,
  getWorkflowAnalyticsFailures,
  getWorkflowAnalyticsComposition,
  getWorkflowAnalyticsSchedules,
  getWorkflowAnalyticsApprovals
} from '../../api/workflows';

export default function UserWorkflowAnalytics({ addLog, triggerNotification }) {
  const [timeWindow, setTimeWindow] = useState(7); // 1, 7, 30
  const [activeSubTab, setActiveSubTab] = useState('performance'); // 'performance' | 'nodes' | 'failures' | 'composition'
  const [loading, setLoading] = useState(true);

  // Analytics Data
  const [overview, setOverview] = useState(null);
  const [performance, setPerformance] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [failures, setFailures] = useState([]);
  const [composition, setComposition] = useState(null);
  const [schedules, setSchedules] = useState(null);
  const [approvals, setApprovals] = useState(null);

  // Search & Filter
  const [searchTerm, setSearchTerm] = useState('');
  const [healthFilter, setHealthFilter] = useState('all');

  const fetchAllAnalytics = async () => {
    try {
      setLoading(true);
      const [ovRes, perfRes, nodeRes, failRes, compRes, schedRes, appRes] = await Promise.all([
        getWorkflowAnalyticsOverview(timeWindow),
        getWorkflowAnalyticsPerformance({ limit: 100 }),
        getWorkflowAnalyticsNodes(undefined, 50),
        getWorkflowAnalyticsFailures(50),
        getWorkflowAnalyticsComposition(),
        getWorkflowAnalyticsSchedules(),
        getWorkflowAnalyticsApprovals()
      ]);

      setOverview(ovRes);
      setPerformance(perfRes.items || []);
      setNodes(nodeRes.items || []);
      setFailures(failRes.items || []);
      setComposition(compRes);
      setSchedules(schedRes);
      setApprovals(appRes);
    } catch (err) {
      console.error('Failed to load workflow analytics:', err);
      if (addLog) addLog('Analytics', 'Failed to fetch telemetry.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllAnalytics();
  }, [timeWindow]);

  const filteredPerformance = performance.filter((p) => {
    const matchSearch = p.workflow_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchHealth = healthFilter === 'all' || p.health.toLowerCase() === healthFilter.toLowerCase();
    return matchSearch && matchHealth;
  });

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Activity className="w-6 h-6 text-indigo-400" />
            Workflow Observability & Analytics
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time execution telemetry, duration percentiles, bottleneck classification, and failure analytics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Time Window Switcher */}
          <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs">
            {[
              { label: '24 Hours', val: 1 },
              { label: '7 Days', val: 7 },
              { label: '30 Days', val: 30 }
            ].map((tw) => (
              <button
                key={tw.val}
                onClick={() => setTimeWindow(tw.val)}
                className={`px-3 py-1.5 rounded-lg font-medium transition ${
                  timeWindow === tw.val
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tw.label}
              </button>
            ))}
          </div>

          <button
            onClick={fetchAllAnalytics}
            disabled={loading}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Refresh Analytics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      {overview && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Executions</span>
            <div className="text-2xl font-bold text-slate-100">{overview.total_executions}</div>
            <div className="text-[10px] text-slate-500 flex items-center gap-1">
              <span>{overview.completed_executions} completed</span> •{' '}
              <span className="text-rose-400">{overview.failed_executions} failed</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Success Rate</span>
            <div className="text-2xl font-bold text-emerald-400">{overview.success_rate}%</div>
            <div className="text-[10px] text-slate-500">
              Failure rate: <strong className="text-rose-400">{overview.failure_rate}%</strong>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Avg Duration</span>
            <div className="text-2xl font-bold text-indigo-300">{overview.avg_duration_seconds}s</div>
            <div className="text-[10px] text-slate-500">
              Median: {overview.median_duration_seconds}s • p95: {overview.p95_duration_seconds}s
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Active Workflows</span>
            <div className="text-2xl font-bold text-slate-100">{overview.active_workflows}</div>
            <div className="text-[10px] text-slate-500">
              {overview.total_workflows} total ({overview.paused_workflows} paused)
            </div>
          </div>
        </div>
      )}

      {/* Execution Distribution & Daily Activity Bar */}
      {overview && (
        <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <BarChart3 className="w-4 h-4 text-indigo-400" /> Status Distribution
            </span>
            <span className="text-slate-500 font-mono text-[11px]">{overview.total_executions} total runs</span>
          </div>

          {/* Progress Stack Bar */}
          <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden flex">
            {overview.completed_executions > 0 && (
              <div
                style={{ width: `${(overview.completed_executions / (overview.total_executions || 1)) * 100}%` }}
                className="bg-emerald-500 transition-all"
                title={`Completed: ${overview.completed_executions}`}
              />
            )}
            {overview.failed_executions > 0 && (
              <div
                style={{ width: `${(overview.failed_executions / (overview.total_executions || 1)) * 100}%` }}
                className="bg-rose-500 transition-all"
                title={`Failed: ${overview.failed_executions}`}
              />
            )}
            {overview.running_executions > 0 && (
              <div
                style={{ width: `${(overview.running_executions / (overview.total_executions || 1)) * 100}%` }}
                className="bg-indigo-500 animate-pulse transition-all"
                title={`Running: ${overview.running_executions}`}
              />
            )}
            {overview.waiting_executions > 0 && (
              <div
                style={{ width: `${(overview.waiting_executions / (overview.total_executions || 1)) * 100}%` }}
                className="bg-amber-500 transition-all"
                title={`Waiting: ${overview.waiting_executions}`}
              />
            )}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-400 pt-1">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Completed ({overview.completed_executions})
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Failed ({overview.failed_executions})
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" /> Running ({overview.running_executions})
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Waiting Approval ({overview.waiting_executions})
            </span>
          </div>
        </div>
      )}

      {/* Sub-Tabs Navigation */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2 text-xs">
          {[
            { id: 'performance', label: 'Workflow Performance', icon: TrendingUp },
            { id: 'nodes', label: 'Node Bottlenecks', icon: Clock },
            { id: 'failures', label: 'Failure Clusters', icon: ShieldAlert },
            { id: 'composition', label: 'Composition & Telemetry', icon: Layers }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition ${
                  activeSubTab === tab.id
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Icon className="w-4 h-4" /> {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* SUB-TAB 1: WORKFLOW PERFORMANCE */}
      {activeSubTab === 'performance' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search workflows..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Health:</span>
              <select
                value={healthFilter}
                onChange={(e) => setHealthFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="healthy">Healthy</option>
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-900/60">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="p-3.5">Workflow Name</th>
                  <th className="p-3.5">Total Runs</th>
                  <th className="p-3.5">Success Rate</th>
                  <th className="p-3.5">Avg Duration</th>
                  <th className="p-3.5">Failures</th>
                  <th className="p-3.5">Health</th>
                  <th className="p-3.5">Latest Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPerformance.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">
                      No matching workflow metrics found.
                    </td>
                  </tr>
                ) : (
                  filteredPerformance.map((wf) => (
                    <tr key={wf.workflow_id} className="hover:bg-slate-800/30 transition">
                      <td className="p-3.5 font-semibold text-slate-200">{wf.workflow_name}</td>
                      <td className="p-3.5 font-mono text-slate-300">{wf.total_runs}</td>
                      <td className="p-3.5 font-mono font-semibold text-emerald-400">{wf.success_rate}%</td>
                      <td className="p-3.5 font-mono text-indigo-300">{wf.avg_duration_seconds}s</td>
                      <td className="p-3.5 font-mono text-rose-400">{wf.failed_runs}</td>
                      <td className="p-3.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            wf.health === 'HEALTHY'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : wf.health === 'WARNING'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {wf.health}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-400 font-mono text-[11px]">{wf.latest_status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: NODE BOTTLENECKS */}
      {activeSubTab === 'nodes' && (
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-900/60">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="p-3.5">Node Key</th>
                  <th className="p-3.5">Workflow</th>
                  <th className="p-3.5">Executions</th>
                  <th className="p-3.5">Avg Duration</th>
                  <th className="p-3.5">Max Duration</th>
                  <th className="p-3.5">Failure Rate</th>
                  <th className="p-3.5">Bottleneck Class</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {nodes.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">
                      No node execution telemetry recorded.
                    </td>
                  </tr>
                ) : (
                  nodes.map((n, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30 transition">
                      <td className="p-3.5 font-mono font-semibold text-slate-200">{n.node_key}</td>
                      <td className="p-3.5 text-slate-400">{n.workflow_name}</td>
                      <td className="p-3.5 font-mono text-slate-300">{n.total_executions}</td>
                      <td className="p-3.5 font-mono text-indigo-300">{n.avg_duration_seconds}s</td>
                      <td className="p-3.5 font-mono text-slate-400">{n.max_duration_seconds}s</td>
                      <td className="p-3.5 font-mono text-rose-400">{n.failure_rate}%</td>
                      <td className="p-3.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            n.bottleneck_category === 'SLOW'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : n.bottleneck_category === 'HIGH_FAILURE'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {n.bottleneck_category}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: FAILURE CLUSTERS */}
      {activeSubTab === 'failures' && (
        <div className="space-y-3">
          {failures.length === 0 ? (
            <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-500" />
              <h4 className="text-sm font-semibold text-slate-300">Clean Execution Log</h4>
              <p className="text-xs text-slate-500">No node failures recorded in active workspace.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {failures.map((f, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-2xl bg-rose-950/20 border border-rose-900/30 flex flex-col md:flex-row md:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-200">{f.workflow_name}</span>
                      <span className="font-mono text-[11px] text-rose-400 font-semibold">[{f.node_key}]</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300">
                        {f.failure_count} occurrences
                      </span>
                    </div>
                    <p className="text-xs font-mono text-slate-300 break-all">{f.error_summary}</p>
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono shrink-0">
                    Latest: {f.latest_failed_at ? new Date(f.latest_failed_at).toLocaleString() : 'N/A'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 4: COMPOSITION & TELEMETRY */}
      {activeSubTab === 'composition' && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-2">
            <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Bot className="w-4 h-4 text-indigo-400" /> Sub-Workflow Invocations
            </h4>
            <div className="text-2xl font-bold text-slate-100">{composition?.total_sub_workflow_invocations || 0}</div>
            <p className="text-[11px] text-slate-500">
              Max execution nesting depth: {composition?.max_supported_nesting_depth || 3} levels
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-2">
            <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <GitBranch className="w-4 h-4 text-cyan-400" /> Parallel Fan-Outs & Merges
            </h4>
            <div className="text-2xl font-bold text-slate-100">
              {composition?.total_parallel_fanouts || 0} fan-outs / {composition?.total_merge_fanins || 0} merges
            </div>
            <p className="text-[11px] text-slate-500">Bounded concurrency with deterministic merge</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-2">
            <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-emerald-400" /> Governance & Schedules
            </h4>
            <div className="text-2xl font-bold text-slate-100">
              {schedules?.active_schedules || 0} active schedules
            </div>
            <p className="text-[11px] text-slate-500">
              {approvals?.pending_approvals || 0} pending approval requests
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
