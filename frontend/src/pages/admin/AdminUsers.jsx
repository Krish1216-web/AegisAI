import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  MoreVertical, 
  ShieldAlert, 
  Key, 
  UserMinus, 
  ToggleLeft, 
  ToggleRight, 
  Edit2, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Shield
} from 'lucide-react';
import { 
  getAdminUsers, 
  getAdminUserDetail, 
  updateAdminUserStatus, 
  updateAdminUserRole 
} from '../../api/admin';

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState(undefined);
  const [statusFilter, setStatusFilter] = useState(undefined);
  
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [editingRoleUserId, setEditingRoleUserId] = useState(null);
  const [targetRole, setTargetRole] = useState('member');
  const [actionMsg, setActionMsg] = useState(null);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await getAdminUsers({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        role: roleFilter,
        is_active: statusFilter
      });
      setUsers(res.users);
      setTotal(res.total);
    } catch (err) {
      setActionMsg({ type: 'error', text: err?.message || 'Failed to load users.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, roleFilter, statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleToggleStatus = async (user) => {
    const nextStatus = !user.is_active;
    try {
      await updateAdminUserStatus(user.id, nextStatus, nextStatus ? 'Reactivated by admin' : 'Suspended by admin');
      setActionMsg({ type: 'success', text: `User ${user.username} status updated to ${nextStatus ? 'ACTIVE' : 'SUSPENDED'}.` });
      fetchUsers();
    } catch (err) {
      setActionMsg({ type: 'error', text: err?.message || 'Failed to update user status.' });
    }
  };

  const handleSaveRole = async (userId) => {
    try {
      await updateAdminUserRole(userId, targetRole);
      setActionMsg({ type: 'success', text: `Role updated to ${targetRole}.` });
      setEditingRoleUserId(null);
      fetchUsers();
    } catch (err) {
      setActionMsg({ type: 'error', text: err?.message || 'Failed to update user role.' });
    }
  };

  const handleInspectUser = async (userId) => {
    try {
      const detail = await getAdminUserDetail(userId);
      setSelectedUser(detail);
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Failed to retrieve detailed user profile.' });
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Users size={20} className="text-purple-400" />
            User Operations Control
          </h2>
          <p className="text-xs text-slate-500 mt-1">Audit active profiles, change authorization roles, activate/suspend accounts, and inspect workspace memberships.</p>
        </div>

        <button 
          onClick={fetchUsers}
          className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> REFRESH
        </button>
      </div>

      {actionMsg && (
        <div className={`p-4 rounded-lg text-xs flex items-center gap-2 ${actionMsg.type === 'success' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'}`}>
          {actionMsg.type === 'success' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* Filter and Search actions */}
      <div className="flex flex-col md:flex-row gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search profiles by handle or email..."
            className="bg-white/5 border border-[rgba(255,255,255,0.06)] rounded-lg py-2 pl-9 pr-4 text-xs text-white w-full outline-none focus:border-purple-500/50 transition-all font-mono"
          />
        </form>
        
        <div className="flex gap-2">
          <select 
            value={roleFilter || ''} 
            onChange={(e) => { setRoleFilter(e.target.value || undefined); setPage(1); }}
            className="bg-slate-900 border border-[rgba(255,255,255,0.06)] rounded-lg px-3 py-1.5 text-xs text-slate-300 outline-none"
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="owner">Owner</option>
            <option value="member">Member</option>
            <option value="viewer">Viewer</option>
          </select>

          <select 
            value={statusFilter === undefined ? '' : String(statusFilter)} 
            onChange={(e) => { 
              setStatusFilter(e.target.value === '' ? undefined : e.target.value === 'true'); 
              setPage(1); 
            }}
            className="bg-slate-900 border border-[rgba(255,255,255,0.06)] rounded-lg px-3 py-1.5 text-xs text-slate-300 outline-none"
          >
            <option value="">All Statuses</option>
            <option value="true">Active</option>
            <option value="false">Suspended</option>
          </select>
        </div>
      </div>

      {/* Advanced data table */}
      <div className="glass-panel overflow-hidden border border-[rgba(255,255,255,0.06)] bg-[#090b10ab] rounded-xl">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-900/60 border-b border-[rgba(255,255,255,0.06)] text-slate-400 font-bold uppercase tracking-wider font-mono text-[10px]">
              <th className="p-4">Profile Handle & Email</th>
              <th className="p-4">Authorization Role</th>
              <th className="p-4">Account Status</th>
              <th className="p-4">Workspaces</th>
              <th className="p-4">Created Date</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[rgba(255,255,255,0.03)] font-mono">
            {users.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-500">
                  {loading ? 'Fetching users from AegisAI database...' : 'No users found matching query filters.'}
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="hover:bg-white/2 transition-all">
                  <td className="p-4 flex flex-col gap-0.5">
                    <button 
                      onClick={() => handleInspectUser(u.id)}
                      className="font-bold text-white hover:text-purple-400 text-left transition-colors cursor-pointer"
                    >
                      {u.username}
                    </button>
                    <span className="text-[10px] text-slate-500">{u.email}</span>
                  </td>
                  
                  <td className="p-4">
                    {editingRoleUserId === u.id ? (
                      <div className="flex items-center gap-2">
                        <select 
                          value={targetRole} 
                          onChange={(e) => setTargetRole(e.target.value)}
                          className="bg-slate-900 border border-purple-500/50 rounded px-2 py-1 text-[10px] text-white"
                        >
                          <option value="admin">admin</option>
                          <option value="owner">owner</option>
                          <option value="member">member</option>
                          <option value="viewer">viewer</option>
                        </select>
                        <button 
                          onClick={() => handleSaveRole(u.id)}
                          className="px-2 py-1 rounded bg-purple-500 text-black font-bold text-[10px]"
                        >
                          Save
                        </button>
                        <button 
                          onClick={() => setEditingRoleUserId(null)}
                          className="px-2 py-1 rounded bg-white/5 text-slate-400 text-[10px]"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${u.role === 'admin' || u.role === 'super admin' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : (u.role === 'owner' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20')}`}>
                          {u.role}
                        </span>
                        <button 
                          onClick={() => { setEditingRoleUserId(u.id); setTargetRole(u.role); }}
                          className="text-slate-500 hover:text-white p-1 rounded"
                          title="Modify Role"
                        >
                          <Edit2 size={10} />
                        </button>
                      </div>
                    )}
                  </td>
                  
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${u.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                      {u.is_active ? 'ACTIVE' : 'SUSPENDED'}
                    </span>
                  </td>

                  <td className="p-4 text-slate-400">
                    {u.workspaces_count} workspace{u.workspaces_count !== 1 ? 's' : ''}
                  </td>

                  <td className="p-4 text-slate-500 text-[10px]">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>

                  <td className="p-4 text-right">
                    <button 
                      onClick={() => handleToggleStatus(u)}
                      className={`px-3 py-1 rounded text-[10px] font-bold transition-all cursor-pointer ${u.is_active ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'}`}
                    >
                      {u.is_active ? 'SUSPEND' : 'ACTIVATE'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination Footer */}
        <div className="flex justify-between items-center p-4 border-t border-[rgba(255,255,255,0.06)] bg-slate-900/40 text-xs">
          <span className="text-slate-500 text-[10px] font-mono">
            Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total} users
          </span>
          <div className="flex items-center gap-2">
            <button 
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
              className="p-1.5 rounded bg-white/5 border border-[rgba(255,255,255,0.06)] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs font-mono text-slate-300">Page {page} of {totalPages}</span>
            <button 
              disabled={page >= totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              className="p-1.5 rounded bg-white/5 border border-[rgba(255,255,255,0.06)] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* User Detail Inspection Modal */}
      {selectedUser && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-2xl bg-[#0d1017] border border-purple-500/30 p-6 rounded-xl flex flex-col gap-4 animate-scale-in max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Shield size={16} className="text-purple-400" />
                Profile Dossier: {selectedUser.username}
              </h3>
              <button onClick={() => setSelectedUser(null)} className="text-slate-400 hover:text-white text-xs">✕ Close</button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3 bg-white/2 rounded-lg border border-[rgba(255,255,255,0.04)]">
                <span className="text-slate-500 block text-[10px]">Email Address</span>
                <span className="text-white font-bold">{selectedUser.email}</span>
              </div>
              <div className="p-3 bg-white/2 rounded-lg border border-[rgba(255,255,255,0.04)]">
                <span className="text-slate-500 block text-[10px]">Role / Status</span>
                <span className="text-purple-400 font-bold">{selectedUser.role}</span> | <span className={selectedUser.is_active ? 'text-emerald-400' : 'text-rose-400'}>{selectedUser.is_active ? 'ACTIVE' : 'SUSPENDED'}</span>
              </div>
            </div>

            {/* Workspace Memberships */}
            <div className="flex flex-col gap-2">
              <h4 className="text-[10px] uppercase font-bold text-slate-400 font-mono">Workspace Memberships ({selectedUser.workspaces.length})</h4>
              <div className="flex flex-col gap-1 text-xs font-mono">
                {selectedUser.workspaces.map((ws, i) => (
                  <div key={i} className="flex justify-between p-2 bg-white/2 rounded border border-[rgba(255,255,255,0.03)]">
                    <span className="text-slate-200">{ws.workspace_name}</span>
                    <span className="text-purple-400">{ws.role}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Audit Logs */}
            <div className="flex flex-col gap-2">
              <h4 className="text-[10px] uppercase font-bold text-slate-400 font-mono">Recent User Audit Trails</h4>
              <div className="flex flex-col gap-1 text-xs font-mono max-h-40 overflow-y-auto">
                {selectedUser.recent_audit_logs.length === 0 ? (
                  <span className="text-slate-500 text-[10px]">No recent audit trails.</span>
                ) : (
                  selectedUser.recent_audit_logs.map((l, i) => (
                    <div key={i} className="flex justify-between p-2 bg-white/2 rounded text-[10px]">
                      <span className="text-slate-300 font-bold">{l.action}</span>
                      <span className="text-slate-500">{new Date(l.created_at).toLocaleTimeString()}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
