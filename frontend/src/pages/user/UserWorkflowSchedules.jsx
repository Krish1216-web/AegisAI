import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Clock,
  Play,
  Pause,
  Trash2,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Globe,
  Settings,
  ChevronRight,
  Layers,
  X
} from 'lucide-react';
import {
  getWorkflowSchedules,
  getWorkflows,
  createWorkflowSchedule,
  updateWorkflowSchedule,
  deleteWorkflowSchedule,
  pauseWorkflowSchedule,
  resumeWorkflowSchedule,
  triggerWorkflowSchedule
} from '../../api/workflows';

const COMMON_TIMEZONES = [
  'UTC',
  'Asia/Kolkata',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Australia/Sydney'
];

const CRON_PRESETS = [
  { label: 'Every 5 minutes', cron: '*/5 * * * *' },
  { label: 'Every 15 minutes', cron: '*/15 * * * *' },
  { label: 'Every hour (top of hour)', cron: '0 * * * *' },
  { label: 'Daily at 9:00 AM', cron: '0 9 * * *' },
  { label: 'Daily at Midnight', cron: '0 0 * * *' },
  { label: 'Weekdays at 9:00 AM (Mon-Fri)', cron: '0 9 * * 1-5' },
  { label: 'Weekly on Monday at 9:00 AM', cron: '0 9 * * 1' },
  { label: 'Monthly on 1st at Midnight', cron: '0 0 1 * *' }
];

export default function UserWorkflowSchedules({ addLog, triggerNotification }) {
  const [schedules, setSchedules] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  // Create Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [targetWorkflowId, setTargetWorkflowId] = useState('');
  const [schedName, setSchedName] = useState('');
  const [schedDesc, setSchedDesc] = useState('');
  const [schedType, setSchedType] = useState('cron'); // 'cron' | 'one_time'
  const [cronExpr, setCronExpr] = useState('0 9 * * *');
  const [runAt, setRunAt] = useState('');
  const [timezone, setTimezone] = useState('UTC');
  const [concurrencyPolicy, setConcurrencyPolicy] = useState('skip');
  const [misfirePolicy, setMisfirePolicy] = useState('run_once');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const [schedRes, wfRes] = await Promise.all([
        getWorkflowSchedules({
          status: statusFilter === 'all' ? undefined : statusFilter,
          limit: 50
        }),
        getWorkflows({ limit: 100 })
      ]);
      setSchedules(schedRes.schedules || []);
      setWorkflows(wfRes.workflows || []);
      if (wfRes.workflows?.length > 0 && !targetWorkflowId) {
        setTargetWorkflowId(wfRes.workflows[0].id);
      }
    } catch (err) {
      console.error('Failed to load schedules:', err);
      if (addLog) addLog('Scheduler', 'Failed to fetch schedules.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedules();
  }, [statusFilter]);

  const handleCreateSchedule = async () => {
    if (!schedName.trim() || !targetWorkflowId) {
      alert('Please provide a schedule name and select a workflow.');
      return;
    }
    try {
      setIsSubmitting(true);
      await createWorkflowSchedule({
        workflow_id: targetWorkflowId,
        name: schedName.trim(),
        description: schedDesc.trim() || undefined,
        schedule_type: schedType,
        cron_expression: schedType === 'cron' ? cronExpr.trim() : undefined,
        run_at: schedType === 'one_time' ? (runAt ? new Date(runAt).toISOString() : undefined) : undefined,
        timezone,
        concurrency_policy: concurrencyPolicy,
        misfire_policy: misfirePolicy,
        is_enabled: true
      });
      if (triggerNotification) triggerNotification('Schedule Created', 'Workflow schedule registered successfully.', 'success');
      setShowCreateModal(false);
      setSchedName('');
      setSchedDesc('');
      fetchSchedules();
    } catch (err) {
      console.error('Failed to create schedule:', err);
      if (triggerNotification) triggerNotification('Schedule Error', err?.message || 'Error creating schedule.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTogglePauseResume = async (sched) => {
    try {
      if (sched.status === 'active') {
        await pauseWorkflowSchedule(sched.id);
        if (triggerNotification) triggerNotification('Schedule Paused', `Paused ${sched.name}`);
      } else {
        await resumeWorkflowSchedule(sched.id);
        if (triggerNotification) triggerNotification('Schedule Resumed', `Resumed ${sched.name}`, 'success');
      }
      fetchSchedules();
    } catch (err) {
      console.error('Toggle error:', err);
    }
  };

  const handleTriggerManual = async (sched) => {
    try {
      await triggerWorkflowSchedule(sched.id);
      if (triggerNotification) triggerNotification('Trigger Dispatched', `Triggered execution for ${sched.name}`, 'success');
      fetchSchedules();
    } catch (err) {
      console.error('Manual trigger failed:', err);
      if (triggerNotification) triggerNotification('Trigger Failed', err?.message || 'Error triggering execution.', 'error');
    }
  };

  const handleDelete = async (schedId) => {
    if (!window.confirm('Are you sure you want to delete this schedule?')) return;
    try {
      await deleteWorkflowSchedule(schedId);
      if (triggerNotification) triggerNotification('Schedule Deleted', 'Schedule removed.');
      fetchSchedules();
    } catch (err) {
      console.error('Delete schedule error:', err);
    }
  };

  const getWorkflowName = (wId) => {
    const found = workflows.find((w) => w.id === wId);
    return found ? found.name : 'Unknown Workflow';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Calendar className="w-6 h-6 text-indigo-400" />
            Workflow Scheduling & Automation
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure automated cron recurrence, one-time triggers, and timezone-aware recurring execution.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs">
            {['all', 'active', 'paused', 'completed'].map((tab) => (
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
            onClick={fetchSchedules}
            disabled={loading}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Refresh Schedules"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition"
          >
            <Plus className="w-4 h-4" /> New Schedule
          </button>
        </div>
      </div>

      {/* Schedules List */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-sm">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
          Loading workflow schedules...
        </div>
      ) : schedules.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center space-y-2">
          <Calendar className="w-8 h-8 mx-auto text-slate-600" />
          <h4 className="text-sm font-semibold text-slate-300">No Schedules Configured</h4>
          <p className="text-xs text-slate-500">
            Create a recurring cron schedule or one-time future trigger to automate your workflows.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {schedules.map((sched) => (
            <div
              key={sched.id}
              className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 hover:border-slate-700 transition space-y-4"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-sm font-bold text-slate-100">{sched.name}</h3>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1 ${
                        sched.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : sched.status === 'paused'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      <Clock className="w-3 h-3" /> {sched.status}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-indigo-950/60 text-indigo-400 border border-indigo-800/40">
                      {sched.schedule_type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Workflow: <strong className="text-slate-200">{getWorkflowName(sched.workflow_id)}</strong> (v{sched.workflow_version})
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleTriggerManual(sched)}
                    className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                    title="Trigger Run Now"
                  >
                    <Play className="w-4 h-4 text-emerald-400" />
                  </button>
                  <button
                    onClick={() => handleTogglePauseResume(sched)}
                    className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                    title={sched.status === 'active' ? 'Pause Schedule' : 'Resume Schedule'}
                  >
                    {sched.status === 'active' ? (
                      <Pause className="w-4 h-4 text-amber-400" />
                    ) : (
                      <Play className="w-4 h-4 text-indigo-400" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(sched.id)}
                    className="p-2 rounded-xl bg-slate-800 hover:bg-rose-900/30 text-slate-400 hover:text-rose-400 transition"
                    title="Delete Schedule"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/60 text-[11px]">
                <div>
                  <span className="text-slate-500 block">Recurrence:</span>
                  <span className="text-indigo-300 font-mono font-medium">
                    {sched.schedule_type === 'cron' ? sched.cron_expression : 'One-time Execution'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Timezone:</span>
                  <span className="text-slate-300 font-mono">{sched.timezone}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Next Run:</span>
                  <span className="text-emerald-400 font-medium font-mono">
                    {sched.next_run_at ? new Date(sched.next_run_at).toLocaleString() : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Total Runs:</span>
                  <span className="text-slate-300">
                    {sched.total_runs} runs ({sched.failure_count} failures)
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CREATE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-indigo-400" />
                Configure Workflow Schedule
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 font-semibold block mb-1">Target Workflow</label>
                <select
                  value={targetWorkflowId}
                  onChange={(e) => setTargetWorkflowId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  {workflows.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name} (v{w.version})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-400 font-semibold block mb-1">Schedule Name</label>
                <input
                  type="text"
                  placeholder="e.g. Daily Data Sync"
                  value={schedName}
                  onChange={(e) => setSchedName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Schedule Type</label>
                  <select
                    value={schedType}
                    onChange={(e) => setSchedType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="cron">Recurring Cron</option>
                    <option value="one_time">One-time / Delayed</option>
                  </select>
                </div>

                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Timezone (IANA)</label>
                  <select
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    {COMMON_TIMEZONES.map((tz) => (
                      <option key={tz} value={tz}>
                        {tz}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {schedType === 'cron' ? (
                <div className="space-y-2">
                  <label className="text-slate-400 font-semibold block">Cron Expression</label>
                  <input
                    type="text"
                    placeholder="0 9 * * *"
                    value={cronExpr}
                    onChange={(e) => setCronExpr(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 font-mono text-indigo-300 focus:outline-none focus:border-indigo-500"
                  />

                  {/* Preset Buttons */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {CRON_PRESETS.map((p, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setCronExpr(p.cron)}
                        className={`px-2 py-1 rounded-lg text-[10px] font-mono transition ${
                          cronExpr === p.cron
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-950 hover:bg-slate-800 text-slate-400 border border-slate-800'
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Execution Time (run_at)</label>
                  <input
                    type="datetime-local"
                    value={runAt}
                    onChange={(e) => setRunAt(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Concurrency Policy</label>
                  <select
                    value={concurrencyPolicy}
                    onChange={(e) => setConcurrencyPolicy(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="skip">Skip (Drop if previous running)</option>
                    <option value="allow">Allow (Run concurrent)</option>
                  </select>
                </div>

                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Misfire Policy</label>
                  <select
                    value={misfirePolicy}
                    onChange={(e) => setMisfirePolicy(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="run_once">Run Once (Catch-up)</option>
                    <option value="skip">Skip</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowCreateModal(false)}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSchedule}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-1.5"
              >
                {isSubmitting ? 'Creating...' : 'Save Schedule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
