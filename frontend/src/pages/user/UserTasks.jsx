import React, { useState, useEffect } from 'react';
import { ListTodo, CheckCircle, Clock, AlertCircle, Play, Sparkles, ChevronRight, RefreshCw, ChevronLeft, Calendar, FileText, Database, ShieldAlert, Cpu } from 'lucide-react';
import { getExecutionHistory, getExecutionDetails } from '../../api/agent';

export default function UserTasks({ triggerNotification }) {
  const [executions, setExecutions] = useState([]);
  const [selectedExec, setSelectedExec] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  
  // Query Filters & Pagination
  const [statusFilter, setStatusFilter] = useState('');
  const [limit] = useState(10);
  const [offset, setOffset] = useState(0);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState(null);

  // Fetch list of executions
  const fetchExecutions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getExecutionHistory(limit, offset, statusFilter || undefined);
      setExecutions(data);
    } catch (e) {
      console.error(e);
      setError(e.message || 'Failed to fetch execution records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchExecutions();
  }, [offset, statusFilter]);

  const handleRowClick = async (executionId) => {
    setIsLoadingDetail(true);
    setShowDetailModal(true);
    try {
      const details = await getExecutionDetails(executionId);
      setSelectedExec(details);
    } catch (e) {
      console.error(e);
      triggerNotification('Detail Fetch Failed', e.message || 'Could not load execution parameters.');
      setShowDetailModal(false);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleStatusFilterChange = (newStatus) => {
    setStatusFilter(newStatus);
    setOffset(0);
  };

  const getStatusBadgeClass = (status) => {
    switch (String(status).toUpperCase()) {
      case 'COMPLETED':
      case 'SUCCESS':
        return 'badge-green';
      case 'FAILED':
        return 'badge-danger';
      case 'RUNNING':
      case 'EXECUTING_CORE':
        return 'badge-cyan animate-pulse';
      case 'WAITING_FOR_CONFIRMATION':
      case 'REQUIRES_CONFIRMATION':
        return 'badge-yellow';
      default:
        return 'badge-cyan';
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300 relative h-full">
      {/* Page Header */}
      <div className="flex justify-between items-center shrink-0 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <ListTodo size={20} className="text-cyan-400" />
            Active Execution Queue
          </h2>
          <p className="text-xs text-slate-500 mt-1">Audit, monitor, and inspect multi-agent executions, status transitions, and final results.</p>
        </div>
        <button
          onClick={fetchExecutions}
          disabled={isLoading}
          className="btn-secondary py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center gap-2 cursor-pointer border-cyan-500/10 hover:border-cyan-500/20 text-cyan-400"
        >
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} /> REFRESH_QUEUE
        </button>
      </div>

      {/* Filters Toolbar */}
      <div className="flex gap-2 shrink-0">
        {[
          { label: 'ALL RUNS', value: '' },
          { label: 'COMPLETED', value: 'COMPLETED' },
          { label: 'RUNNING', value: 'RUNNING' },
          { label: 'FAILED', value: 'FAILED' }
        ].map((btn) => (
          <button
            key={btn.value}
            onClick={() => handleStatusFilterChange(btn.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${statusFilter === btn.value ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'bg-white/2 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white'}`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Main Table Content */}
      <div className="flex-1 glass-panel overflow-hidden flex flex-col min-h-[300px]">
        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin"></div>
            <span className="text-xs text-slate-500 font-mono">LOADING EXECUTION RUNS...</span>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-rose-400">
            <AlertCircle size={24} />
            <span className="text-xs font-mono">{error}</span>
          </div>
        ) : executions.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-500">
            <ListTodo size={32} className="opacity-40" />
            <span className="text-xs">No execution runs found. Send a prompt in AI Workspace to generate logs.</span>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)] bg-white/1 text-slate-400 uppercase tracking-wider text-[10px] font-bold">
                  <th className="p-4">Execution ID</th>
                  <th className="p-4">Prompt Trigger</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Latency</th>
                  <th className="p-4">Confidence</th>
                  <th className="p-4">Timestamp</th>
                  <th className="p-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
                {executions.map((exec) => (
                  <tr
                    key={exec.execution_id}
                    onClick={() => handleRowClick(exec.execution_id)}
                    className="hover:bg-white/2 cursor-pointer transition-all border-b border-[rgba(255,255,255,0.02)]"
                  >
                    <td className="p-4 font-mono text-cyan-400 text-[11px]">{exec.execution_id.slice(0, 8)}...</td>
                    <td className="p-4 max-w-xs truncate text-slate-200 font-medium">
                      {exec.meta_data?.original_prompt || 'Standard multi-agent execution pipeline'}
                    </td>
                    <td className="p-4">
                      <span className={`badge ${getStatusBadgeClass(exec.status)}`}>
                        {exec.status}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-slate-400">{exec.total_execution_time ? `${exec.total_execution_time.toFixed(2)}s` : '—'}</td>
                    <td className="p-4 font-mono text-slate-400">{exec.response_confidence ? `${(exec.response_confidence * 100).toFixed(0)}%` : '—'}</td>
                    <td className="p-4 text-slate-500 font-mono">
                      {new Date(exec.started_at).toLocaleString()}
                    </td>
                    <td className="p-4 text-right">
                      <ChevronRight size={14} className="text-slate-600 group-hover:text-white inline" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Toolbar */}
        <div className="shrink-0 p-4 border-t border-[rgba(255,255,255,0.06)] bg-black/20 flex justify-between items-center">
          <span className="text-[10px] text-slate-500 font-mono">
            Showing records {offset + 1} - {offset + executions.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setOffset(prev => Math.max(0, prev - limit))}
              disabled={offset === 0}
              className="btn-secondary py-1 px-3 rounded text-xs flex items-center gap-1.5 disabled:opacity-30 cursor-pointer"
            >
              <ChevronLeft size={12} /> Prev
            </button>
            <button
              onClick={() => setOffset(prev => prev + limit)}
              disabled={executions.length < limit}
              className="btn-secondary py-1 px-3 rounded text-xs flex items-center gap-1.5 disabled:opacity-30 cursor-pointer"
            >
              Next <ChevronRight size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* Execution Details Modal Overlay */}
      {showDetailModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col bg-[#0b0e14] border border-cyan-500/25">
            {/* Modal Header */}
            <div className="p-5 border-b border-[rgba(255,255,255,0.06)] bg-white/1 flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                  <Terminal size={14} className="text-cyan-400" />
                  Run Parameters: {selectedExec?.execution_id || 'Fetch details...'}
                </h3>
                <span className="text-[10px] text-slate-500 block mt-1">
                  Started at {selectedExec ? new Date(selectedExec.started_at).toLocaleString() : '—'}
                </span>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="btn-secondary py-1.5 px-3 rounded-lg text-xs"
              >
                Close
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-6">
              {isLoadingDetail ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12">
                  <div className="w-6 h-6 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin"></div>
                  <span className="text-[10px] text-slate-500 font-mono">LOADING COGNITIVE CHECKS...</span>
                </div>
              ) : selectedExec ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* Left Column: Final Answer & Summary */}
                  <div className="lg:col-span-2 flex flex-col gap-4">
                    <div className="glass-panel p-4 bg-white/1 border-[rgba(255,255,255,0.04)]">
                      <h4 className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-2 flex items-center gap-1.5">
                        <FileText size={12} className="text-cyan-400" /> Original Instruction Prompt
                      </h4>
                      <p className="text-xs text-slate-200 leading-normal bg-black/30 p-3 rounded font-medium border border-white/5">
                        {selectedExec.meta_data?.original_prompt || 'Standard multi-agent execution pipeline'}
                      </p>
                    </div>

                    <div className="glass-panel p-4 bg-white/1 border-[rgba(255,255,255,0.04)] flex flex-col gap-2">
                      <h4 className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-2 flex items-center gap-1.5">
                        <CheckCircle size={12} className="text-green-400" /> Sanitized Response Output
                      </h4>
                      <div className="text-xs text-slate-300 leading-relaxed bg-black/40 p-4 rounded font-mono border border-white/5 whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                        {selectedExec.final_response || 'No response returned.'}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Node execution lists */}
                  <div className="lg:col-span-1 flex flex-col gap-4">
                    
                    {/* Performance metrics */}
                    <div className="glass-panel p-4 bg-white/1 border-[rgba(255,255,255,0.04)] flex flex-col gap-3">
                      <h4 className="text-[10px] text-slate-500 uppercase tracking-wider font-bold border-b border-white/5 pb-2 flex items-center gap-1.5">
                        <Database size={12} className="text-purple-400" /> Run Performance
                      </h4>
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-500">Latency:</span>
                        <span className="text-white">{selectedExec.total_execution_time ? `${selectedExec.total_execution_time.toFixed(2)}s` : '—'}</span>
                      </div>
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-500">Confidence:</span>
                        <span className="text-white">{selectedExec.response_confidence ? `${(selectedExec.response_confidence * 100).toFixed(0)}%` : '—'}</span>
                      </div>
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-500">Critic Quality:</span>
                        <span className="text-cyan-400">{selectedExec.critic_score ? `${(selectedExec.critic_score * 100).toFixed(0)}/100` : '—'}</span>
                      </div>
                    </div>

                    {/* Agent steps */}
                    <div className="glass-panel p-4 bg-white/1 border-[rgba(255,255,255,0.04)] flex flex-col gap-3">
                      <h4 className="text-[10px] text-slate-500 uppercase tracking-wider font-bold border-b border-white/5 pb-2 flex items-center gap-1.5">
                        <Cpu size={12} className="text-purple-400" /> Node Agent Log Execution
                      </h4>
                      <div className="flex flex-col gap-3 max-h-[220px] overflow-y-auto pr-1">
                        {selectedExec.agent_executions?.map((ae) => (
                          <div key={ae.agent_type} className="flex justify-between items-start text-[11px] border-b border-white/2 pb-2">
                            <div className="flex flex-col gap-0.5">
                              <span className="font-semibold text-slate-300 font-mono">{ae.agent_type.replace('Agent', '')}</span>
                              <span className="text-[9px] text-slate-500 font-mono">Retries: {ae.retry_count} • Latency: {ae.duration ? `${ae.duration.toFixed(2)}s` : '—'}</span>
                            </div>
                            <span className={`badge text-[9px] scale-90 ${getStatusBadgeClass(ae.status)}`}>
                              {ae.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                  </div>

                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
