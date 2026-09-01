import React, { useState } from 'react';
import { 
  History, 
  Search, 
  Eye
} from 'lucide-react';

const STATUS_BADGE_MAP = {
  completed: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  failed: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  waiting: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  cancelled: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
  executing: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
  denied: 'bg-rose-500/10 text-rose-300 border-rose-500/30'
};

export default function PlatformExecutionHistory({
  history = [],
  onSelectExecution,
  selectedExecutionId,
  onRerunExecution
}) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = history.filter(item => {
    const matchesSearch = 
      item.execution_id.toLowerCase().includes(search.toLowerCase()) ||
      item.capability_id.toLowerCase().includes(search.toLowerCase());

    const matchesStatus = statusFilter === 'all' || item.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex flex-col gap-6 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-6 rounded-xl backdrop-blur-md">
      {/* Header & Filters */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <div>
          <h4 className="text-sm font-bold text-slate-100 uppercase tracking-wide flex items-center gap-2">
            <History size={16} className="text-cyan-400" />
            <span>Platform Execution History ({history.length})</span>
          </h4>
          <span className="text-xs text-slate-400 mt-0.5 block">
            Recent capability execution records and audit telemetry
          </span>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          {/* Search */}
          <div className="relative flex-1 md:w-48">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search history..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-black/40 border border-slate-700/60 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-black/40 border border-slate-700/60 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="waiting">Waiting</option>
            <option value="cancelled">Cancelled</option>
            <option value="denied">Denied</option>
          </select>
        </div>
      </div>

      {/* History Table */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 bg-black/20 border border-dashed border-slate-800 rounded-xl text-center">
          <History size={32} className="text-slate-600 mb-2" />
          <h4 className="text-sm font-semibold text-slate-300">No Execution History Found</h4>
          <p className="text-xs text-slate-500 mt-1">Executions completed during this session will appear here.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Execution ID</th>
                <th className="py-2.5 px-3">Capability</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3">Started</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.03)] font-mono">
              {filtered.map(item => {
                const isSelected = selectedExecutionId === item.execution_id;
                const statusKey = item.status?.toLowerCase() || 'completed';
                const badgeClass = STATUS_BADGE_MAP[statusKey] || STATUS_BADGE_MAP.completed;

                return (
                  <tr
                    key={item.execution_id}
                    onClick={() => onSelectExecution(item)}
                    className={`hover:bg-cyan-500/5 transition-colors cursor-pointer ${
                      isSelected ? 'bg-cyan-500/10 text-cyan-300 font-semibold' : 'text-slate-300'
                    }`}
                  >
                    <td className="py-2.5 px-3 truncate max-w-[140px] text-cyan-400">
                      {item.execution_id}
                    </td>
                    <td className="py-2.5 px-3 text-slate-200 font-sans">
                      {item.capability_id}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${badgeClass}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {item.duration_ms}ms
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 font-sans text-[11px]">
                      {new Date(item.started_at).toLocaleTimeString()}
                    </td>
                    <td className="py-2.5 px-3 text-right font-sans">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectExecution(item);
                          }}
                          className="p-1 rounded hover:bg-white/10 text-slate-300 transition-all"
                          title="Inspect Execution"
                        >
                          <Eye size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
