import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Users,
  Folder,
  MessageSquare,
  Bell,
  Activity,
  Award,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Flame,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import {
  getCollaborationOverview,
  getTeamAnalytics,
  getProjectAnalytics,
  getActivityAnalytics,
  getTopContributors
} from '../../api/collaborationAnalytics';

export default function UserCollaborationAnalytics() {
  const [timeWindow, setTimeWindow] = useState('7d');
  const [overview, setOverview] = useState(null);
  const [teams, setTeams] = useState([]);
  const [projects, setProjects] = useState([]);
  const [activitySeries, setActivitySeries] = useState([]);
  const [contributors, setContributors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadAllAnalytics();
  }, [timeWindow]);

  const loadAllAnalytics = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const [ov, tm, pr, act, top] = await Promise.all([
        getCollaborationOverview(timeWindow),
        getTeamAnalytics({ page_size: 10 }),
        getProjectAnalytics({ page_size: 10 }),
        getActivityAnalytics(timeWindow),
        getTopContributors(5)
      ]);
      setOverview(ov);
      setTeams(tm.teams || []);
      setProjects(pr.projects || []);
      setActivitySeries(act.series || []);
      setContributors(top.contributors || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load collaboration analytics');
    } finally {
      setLoading(false);
    }
  };

  const getHealthBadge = (health) => {
    if (health === 'HEALTHY') {
      return (
        <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded-full">
          <CheckCircle2 className="w-3 h-3" /> Healthy
        </span>
      );
    }
    if (health === 'MODERATE') {
      return (
        <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-400 bg-amber-950/60 border border-amber-800 px-2 py-0.5 rounded-full">
          <AlertTriangle className="w-3 h-3" /> Moderate
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-400 bg-rose-950/60 border border-rose-800 px-2 py-0.5 rounded-full">
        Low
      </span>
    );
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 text-white">
      {/* Header & Window Selector */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-gray-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-900/40 border border-indigo-700/50 rounded-xl">
            <TrendingUp className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Collaboration Analytics</h1>
            <p className="text-xs text-gray-400">Team engagement, project throughput, and activity intelligence</p>
          </div>
        </div>

        {/* Time Window Selector */}
        <div className="flex items-center bg-gray-900 border border-gray-800 rounded-xl p-1 gap-1">
          {['24h', '7d', '30d', '90d'].map((w) => (
            <button
              key={w}
              onClick={() => setTimeWindow(w)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                timeWindow === w
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {w.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {errorMsg && (
        <div className="bg-red-950/60 border border-red-800 text-red-300 text-xs px-3 py-2 rounded-lg">
          {errorMsg}
        </div>
      )}

      {/* Overview KPI Grid */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-850/80 border border-gray-800 rounded-2xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-gray-400">
              <span>Active Collaborators</span>
              <Users className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="flex items-baseline justify-between">
              <h3 className="text-2xl font-bold text-white">{overview.active_users}</h3>
              <span className="text-xs text-gray-500">of {overview.total_members} members</span>
            </div>
            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-gray-800/80">
              <span className="text-gray-400">Engagement</span>
              <span className="font-semibold text-indigo-300">{(overview.engagement_rate * 100).toFixed(1)}%</span>
            </div>
          </div>

          <div className="bg-gray-850/80 border border-gray-800 rounded-2xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-gray-400">
              <span>Collaboration Health</span>
              <Flame className="w-4 h-4 text-amber-400" />
            </div>
            <div className="flex items-center justify-between">
              {getHealthBadge(overview.health_status)}
              <span className="text-xs text-gray-500">{overview.active_projects} active projects</span>
            </div>
            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-gray-800/80">
              <span className="text-gray-400">Active Teams</span>
              <span className="font-semibold text-cyan-300">{overview.active_teams}</span>
            </div>
          </div>

          <div className="bg-gray-850/80 border border-gray-800 rounded-2xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-gray-400">
              <span>Discussions & Mentions</span>
              <MessageSquare className="w-4 h-4 text-purple-400" />
            </div>
            <div className="flex items-baseline justify-between">
              <h3 className="text-2xl font-bold text-white">{overview.total_comments}</h3>
              <span className="text-xs text-purple-300 font-semibold">{overview.total_mentions} mentions</span>
            </div>
            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-gray-800/80">
              <span className="text-gray-400">Replies Volume</span>
              <span className="font-semibold text-gray-300">{overview.total_replies}</span>
            </div>
          </div>

          <div className="bg-gray-850/80 border border-gray-800 rounded-2xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-gray-400">
              <span>Activity Events</span>
              <Activity className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex items-baseline justify-between">
              <h3 className="text-2xl font-bold text-white">{overview.total_activities}</h3>
              <div className={`flex items-center text-xs font-semibold ${overview.activity_growth.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {overview.activity_growth.delta >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {(overview.activity_growth.growth_rate * 100).toFixed(0)}%
              </div>
            </div>
            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-gray-800/80">
              <span className="text-gray-400">Notifications Read</span>
              <span className="font-semibold text-gray-300">{overview.notifications_read} / {overview.notifications_generated}</span>
            </div>
          </div>
        </div>
      )}

      {/* Activity Timeline Bar Chart */}
      <div className="bg-gray-850/70 border border-gray-800 rounded-2xl p-5 space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Calendar className="w-4 h-4 text-indigo-400" />
            Activity Volume Time Series ({timeWindow.toUpperCase()})
          </h3>
          <span className="text-xs text-gray-500">Aggregated collaboration actions</span>
        </div>

        <div className="h-40 flex items-end gap-2 pt-6 pb-2 border-b border-gray-800/80 overflow-x-auto">
          {activitySeries.map((pt) => {
            const maxVal = Math.max(...activitySeries.map(s => s.count), 1);
            const heightPct = Math.max(10, Math.round((pt.count / maxVal) * 100));
            return (
              <div key={pt.date} className="flex-1 flex flex-col items-center gap-1.5 min-w-[32px] group">
                <span className="text-[10px] text-gray-400 opacity-0 group-hover:opacity-100 transition">{pt.count}</span>
                <div
                  style={{ height: `${heightPct}%` }}
                  className="w-full bg-gradient-to-t from-indigo-700 to-indigo-500 rounded-t-md hover:from-indigo-600 hover:to-indigo-400 transition"
                />
                <span className="text-[9px] text-gray-500 truncate w-full text-center">{pt.date.slice(5)}</span>
              </div>
            );
          })}
          {activitySeries.length === 0 && (
            <div className="w-full text-center text-gray-500 text-xs py-10">No activity recorded in this period.</div>
          )}
        </div>
      </div>

      {/* Leaderboard & Projects Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Contributors */}
        <div className="bg-gray-850/70 border border-gray-800 rounded-2xl p-5 space-y-4">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Award className="w-4 h-4 text-amber-400" />
            Top Contributors
          </h3>
          <div className="divide-y divide-gray-800/60">
            {contributors.map((c, i) => (
              <div key={c.user_id} className="py-2.5 flex justify-between items-center text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-bold text-gray-500 w-4">#{i + 1}</span>
                  <div>
                    <span className="font-medium text-white">{c.username}</span>
                    <span className="text-[10px] text-gray-500 block">{c.comment_count} comments</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="font-bold text-indigo-400">{c.activity_count}</span>
                  <span className="text-[10px] text-gray-500 block">actions</span>
                </div>
              </div>
            ))}
            {contributors.length === 0 && (
              <div className="text-center py-6 text-gray-500 text-xs">No active contributors found.</div>
            )}
          </div>
        </div>

        {/* Project Throughput */}
        <div className="bg-gray-850/70 border border-gray-800 rounded-2xl p-5 space-y-4">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Folder className="w-4 h-4 text-purple-400" />
            Project Collaboration
          </h3>
          <div className="divide-y divide-gray-800/60">
            {projects.map((p) => (
              <div key={p.project_id} className="py-2.5 flex justify-between items-center text-xs">
                <div>
                  <span className="font-medium text-white">{p.project_name}</span>
                  <span className="text-[10px] text-gray-500 block">{p.member_count} members • {p.resource_count} resources</span>
                </div>
                <div className="text-right">
                  <span className="font-semibold text-purple-300">{p.comment_count} comments</span>
                  <span className="text-[10px] text-gray-500 block">{(p.engagement_rate * 100).toFixed(0)}% engagement</span>
                </div>
              </div>
            ))}
            {projects.length === 0 && (
              <div className="text-center py-6 text-gray-500 text-xs">No active projects found.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
