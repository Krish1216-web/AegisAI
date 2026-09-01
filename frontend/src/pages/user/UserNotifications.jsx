import React, { useState, useEffect } from 'react';
import { Bell, Check, CheckCheck, Settings, Filter, Mail, MessageSquare, Users, Folder, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  getNotifications,
  getUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
  getNotificationPreferences,
  updateNotificationPreference
} from '../../api/notifications';

export default function UserNotifications() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filterStatus, setFilterStatus] = useState('all');
  const [loading, setLoading] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const [preferences, setPreferences] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadData();
  }, [filterStatus]);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await getNotifications({
        status: filterStatus === 'unread' ? 'unread' : undefined,
        page_size: 50
      });
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await markNotificationRead(id);
      loadData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update notification');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      loadData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to mark all as read');
    }
  };

  const openPreferences = async () => {
    try {
      const res = await getNotificationPreferences();
      setPreferences(res.preferences || []);
      setShowPreferences(true);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load preferences');
    }
  };

  const togglePref = async (type, channel) => {
    const target = preferences.find(p => p.notification_type === type);
    if (!target) return;
    const updated = {
      notification_type: type,
      [channel]: !target[channel]
    };
    try {
      const res = await updateNotificationPreference(updated);
      setPreferences(res.preferences || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update preference');
    }
  };

  const getIcon = (type) => {
    if (type.includes('MENTION') || type.includes('COMMENT')) return <MessageSquare className="w-4 h-4 text-indigo-400" />;
    if (type.includes('TEAM')) return <Users className="w-4 h-4 text-cyan-400" />;
    return <Folder className="w-4 h-4 text-purple-400" />;
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 text-white">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-gray-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-900/40 border border-indigo-700/50 rounded-xl">
            <Bell className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Notifications Center</h1>
            <p className="text-xs text-gray-400">Manage real-time alerts, collaboration mentions, and preferences</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleMarkAllRead}
            disabled={unreadCount === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-xs font-medium rounded-lg transition"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            Mark All Read
          </button>
          <button
            onClick={openPreferences}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-medium rounded-lg transition"
          >
            <Settings className="w-3.5 h-3.5" />
            Preferences
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-red-950/60 border border-red-800 text-red-300 text-xs px-3 py-2 rounded-lg">
          {errorMsg}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilterStatus('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            filterStatus === 'all' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilterStatus('unread')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
            filterStatus === 'unread' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          Unread
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* Notification List */}
      <div className="space-y-3">
        {notifications.map((n) => (
          <div
            key={n.id}
            className={`p-4 rounded-xl border transition flex items-start justify-between gap-4 ${
              n.status === 'unread'
                ? 'bg-gray-850/80 border-indigo-500/40 shadow-sm shadow-indigo-950/20'
                : 'bg-gray-900/60 border-gray-800 text-gray-400'
            }`}
          >
            <div className="flex items-start gap-3.5">
              <div className="p-2 bg-gray-800 rounded-lg shrink-0 mt-0.5">
                {getIcon(n.type)}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className={`text-xs font-semibold ${n.status === 'unread' ? 'text-white' : 'text-gray-300'}`}>
                    {n.title}
                  </h4>
                  <span className="text-[10px] text-gray-500">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-gray-300">{n.body}</p>
                {n.actor_name && (
                  <span className="text-[10px] text-gray-500 block">From: {n.actor_name}</span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {n.project_id && (
                <button
                  onClick={() => navigate('/user/teams')}
                  className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 px-2 py-1 bg-indigo-950/40 rounded transition"
                >
                  View
                  <ArrowRight className="w-3 h-3" />
                </button>
              )}
              {n.status === 'unread' && (
                <button
                  onClick={() => handleMarkRead(n.id)}
                  className="p-1.5 text-gray-400 hover:text-white rounded bg-gray-800 hover:bg-gray-700"
                  title="Mark as Read"
                >
                  <Check className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        ))}

        {notifications.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-500 text-xs">
            No notifications found.
          </div>
        )}
      </div>

      {/* Preferences Modal */}
      {showPreferences && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-lg w-full p-6 space-y-5">
            <div className="flex justify-between items-center border-b border-gray-800 pb-3">
              <h3 className="text-sm font-bold flex items-center gap-2">
                <Settings className="w-4 h-4 text-indigo-400" />
                Notification Preferences
              </h3>
              <button
                onClick={() => setShowPreferences(false)}
                className="text-gray-400 hover:text-white text-xs px-2 py-1"
              >
                Close
              </button>
            </div>

            <div className="space-y-3 divide-y divide-gray-800/60 max-h-80 overflow-y-auto pr-1">
              {preferences.map((p) => (
                <div key={p.notification_type} className="pt-3 flex justify-between items-center text-xs">
                  <div>
                    <p className="font-semibold text-white uppercase">{p.notification_type}</p>
                    <span className="text-[10px] text-gray-500">In-App and Email alerts</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-1.5 cursor-pointer text-gray-300">
                      <input
                        type="checkbox"
                        checked={p.in_app_enabled}
                        onChange={() => togglePref(p.notification_type, 'in_app_enabled')}
                        className="rounded bg-gray-800 border-gray-700 text-indigo-600 focus:ring-0"
                      />
                      In-App
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer text-gray-300">
                      <input
                        type="checkbox"
                        checked={p.email_enabled}
                        onChange={() => togglePref(p.notification_type, 'email_enabled')}
                        className="rounded bg-gray-800 border-gray-700 text-indigo-600 focus:ring-0"
                      />
                      Email
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
