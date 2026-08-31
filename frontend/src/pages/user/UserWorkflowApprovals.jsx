import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  UserCheck,
  FileText,
  ChevronRight,
  Filter,
  Check,
  X
} from 'lucide-react';
import {
  getWorkflowApprovals,
  approveWorkflowApproval,
  rejectWorkflowApproval
} from '../../api/workflows';

export default function UserWorkflowApprovals({ addLog, triggerNotification }) {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [selectedApproval, setSelectedApproval] = useState(null);

  // Decision Modal
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [targetApproval, setTargetApproval] = useState(null);
  const [decisionReason, setDecisionReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const res = await getWorkflowApprovals({
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit: 50
      });
      setApprovals(res.approvals || []);
    } catch (err) {
      console.error('Failed to fetch approvals:', err);
      if (addLog) addLog('Approvals', 'Failed to fetch approval requests.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, [statusFilter]);

  const handleApprove = async () => {
    if (!targetApproval) return;
    try {
      setIsSubmitting(true);
      await approveWorkflowApproval(targetApproval.id, decisionReason || undefined);
      if (triggerNotification) triggerNotification('Approval Granted', 'Workflow execution has resumed.', 'success');
      setShowApproveModal(false);
      setDecisionReason('');
      setTargetApproval(null);
      fetchApprovals();
    } catch (err) {
      console.error('Approve failed:', err);
      if (triggerNotification) triggerNotification('Approval Failed', err?.message || 'Error recording approval.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!targetApproval) return;
    try {
      setIsSubmitting(true);
      await rejectWorkflowApproval(targetApproval.id, decisionReason || 'Rejected by approver');
      if (triggerNotification) triggerNotification('Execution Rejected', 'Workflow execution has been terminated.', 'info');
      setShowRejectModal(false);
      setDecisionReason('');
      setTargetApproval(null);
      fetchApprovals();
    } catch (err) {
      console.error('Reject failed:', err);
      if (triggerNotification) triggerNotification('Rejection Failed', err?.message || 'Error recording rejection.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5 animate-pulse">
            <Clock className="w-3 h-3" /> Pending Review
          </span>
        );
      case 'approved':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
            <CheckCircle2 className="w-3 h-3" /> Approved
          </span>
        );
      case 'rejected':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1.5">
            <XCircle className="w-3 h-3" /> Rejected
          </span>
        );
      case 'expired':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20 flex items-center gap-1.5">
            <Clock className="w-3 h-3" /> Expired
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-indigo-400" />
            Human Governance & Approval Center
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Review and govern pending workflow execution gates with tenant-isolated authorization.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Status Tabs */}
          <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs">
            {['pending', 'approved', 'rejected', 'all'].map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={`px-3 py-1.5 rounded-lg font-medium capitalize transition ${
                  statusFilter === tab
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <button
            onClick={fetchApprovals}
            disabled={loading}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Refresh Approvals"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Approvals List */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-sm">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
          Loading approval requests...
        </div>
      ) : approvals.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center space-y-2">
          <ShieldCheck className="w-8 h-8 mx-auto text-slate-600" />
          <h4 className="text-sm font-semibold text-slate-300">No Approvals Found</h4>
          <p className="text-xs text-slate-500">
            There are currently no {statusFilter !== 'all' ? statusFilter : ''} approval requests for this workspace.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {approvals.map((app) => (
            <div
              key={app.id}
              className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 hover:border-slate-700 transition space-y-4"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-sm font-bold text-slate-100">{app.title}</h3>
                    {getStatusBadge(app.status)}
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-400">
                      Node: {app.node_key}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-2">{app.message}</p>
                </div>

                {/* Actions */}
                {app.status === 'pending' && (
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => {
                        setTargetApproval(app);
                        setDecisionReason('');
                        setShowApproveModal(true);
                      }}
                      className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-lg shadow-emerald-900/20"
                    >
                      <Check className="w-3.5 h-3.5" /> Approve
                    </button>
                    <button
                      onClick={() => {
                        setTargetApproval(app);
                        setDecisionReason('');
                        setShowRejectModal(true);
                      }}
                      className="px-3.5 py-1.5 rounded-xl bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/30 text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      <X className="w-3.5 h-3.5" /> Reject
                    </button>
                  </div>
                )}
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/60 text-[11px]">
                <div>
                  <span className="text-slate-500 block">Policy:</span>
                  <span className="text-slate-300 font-medium capitalize font-mono">
                    {app.policy.replace('_', ' ')}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Assigned Roles:</span>
                  <span className="text-indigo-300 font-medium">
                    {app.assigned_roles?.join(', ') || 'Any Admin'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Requested At:</span>
                  <span className="text-slate-300">
                    {new Date(app.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Expires At:</span>
                  <span className="text-slate-300">
                    {app.expires_at ? new Date(app.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Never'}
                  </span>
                </div>
              </div>

              {/* Decision History if present */}
              {app.decision_history?.length > 0 && (
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/50 space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                    Audit Decision Trail
                  </span>
                  <div className="space-y-1">
                    {app.decision_history.map((dh, idx) => (
                      <div key={idx} className="flex items-center justify-between text-[11px]">
                        <span className="text-slate-300">
                          <strong className="text-slate-200">{dh.username || 'Approver'}</strong>: {dh.decision} - <span className="text-slate-400 italic">"{dh.reason}"</span>
                        </span>
                        <span className="text-slate-500 font-mono text-[10px]">
                          {new Date(dh.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* APPROVE MODAL */}
      {showApproveModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              Approve Workflow Gate
            </h3>
            <p className="text-xs text-slate-400">
              You are authorizing execution of <strong className="text-slate-200">{targetApproval?.title}</strong>. This will resume workflow execution.
            </p>
            <div>
              <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                Approval Comments (Optional)
              </label>
              <textarea
                placeholder="Reason or comments for approval..."
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowApproveModal(false)}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition flex items-center gap-1.5"
              >
                {isSubmitting ? 'Approving...' : 'Confirm Approval'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REJECT MODAL */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <XCircle className="w-5 h-5 text-rose-400" />
              Reject Workflow Execution
            </h3>
            <p className="text-xs text-slate-400">
              Rejecting will immediately terminate execution <strong className="text-slate-200">{targetApproval?.title}</strong> and mark downstream nodes as skipped/failed.
            </p>
            <div>
              <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                Rejection Reason (Required)
              </label>
              <textarea
                placeholder="Explain why this step is rejected..."
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                rows={3}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 focus:outline-none focus:border-rose-500"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowRejectModal(false)}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={isSubmitting || !decisionReason.trim()}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition flex items-center gap-1.5"
              >
                {isSubmitting ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
