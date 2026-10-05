import React, { useState, useEffect, useCallback } from 'react';
import { 
  Users, 
  Search, 
  MoreVertical, 
  ShieldAlert, 
  Key, 
  UserMinus, 
  UserCheck,
  ToggleLeft, 
  ToggleRight, 
  Edit2, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Shield,
  Briefcase,
  Layers,
  Clock,
  Lock,
  Mail,
  User,
  X,
  Check,
  Info,
  ExternalLink,
  ShieldCheck
} from 'lucide-react';
import { 
  getAdminUsers, 
  getAdminUserDetail, 
  updateAdminUserStatus, 
  updateAdminUserRole 
} from '../../api/admin';
import {
  Button,
  IconButton,
  Badge,
  StatusBadge,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  MetricCard,
  EmptyState,
  Skeleton,
  Drawer,
  Modal,
  Table
} from '../../components/ui';

// Canonical permission map based on RBAC role
const ROLE_PERMISSIONS = {
  admin: [
    'workspace:admin',
    'user:manage',
    'role:assign',
    'security:audit',
    'workflow:create',
    'workflow:execute',
    'workflow:update',
    'workflow:delete',
    'agent:orchestrate',
    'agent:configure',
    'document:upload',
    'document:delete',
    'mcp:connect',
    'mcp:execute_restricted',
    'analytics:view_all'
  ],
  'super admin': [
    'platform:super_admin',
    'workspace:admin',
    'user:manage',
    'role:assign',
    'security:audit',
    'workflow:create',
    'workflow:execute',
    'workflow:update',
    'workflow:delete',
    'agent:orchestrate',
    'agent:configure',
    'document:upload',
    'document:delete',
    'mcp:connect',
    'mcp:execute_restricted',
    'analytics:view_all'
  ],
  member: [
    'workflow:view',
    'workflow:create',
    'workflow:execute',
    'agent:use',
    'document:view',
    'document:upload',
    'mcp:use_safe',
    'chat:create_session',
    'memory:read_write'
  ],
  user: [
    'workflow:view',
    'workflow:create',
    'workflow:execute',
    'agent:use',
    'document:view',
    'document:upload',
    'mcp:use_safe',
    'chat:create_session',
    'memory:read_write'
  ],
  viewer: [
    'workflow:view',
    'document:view',
    'agent:inspect',
    'analytics:view_self'
  ]
};

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [isLoadingUserDetail, setIsLoadingUserDetail] = useState(false);
  const [userDetailData, setUserDetailData] = useState(null);

  // Modals
  const [suspendingUser, setSuspendingUser] = useState(null);
  const [suspendReason, setSuspendReason] = useState('');
  const [isSubmittingSuspend, setIsSubmittingSuspend] = useState(false);

  const [editingRoleUser, setEditingRoleUser] = useState(null);
  const [targetRole, setTargetRole] = useState('member');
  const [isSubmittingRole, setIsSubmittingRole] = useState(false);

  const [actionMsg, setActionMsg] = useState(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getAdminUsers({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        role: roleFilter !== 'ALL' ? roleFilter : undefined,
        is_active: statusFilter === 'ACTIVE' ? true : statusFilter === 'SUSPENDED' ? false : undefined
      });
      setUsers(res.users || []);
      setTotal(res.total || 0);
    } catch (err) {
      setActionMsg({ type: 'error', text: err?.message || 'Failed to load user directory.' });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, roleFilter, statusFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  // Inspect User Detail
  useEffect(() => {
    if (!selectedUser?.id) {
      setUserDetailData(null);
      return;
    }
    let cancelled = false;
    setIsLoadingUserDetail(true);
    getAdminUserDetail(selectedUser.id)
      .then((detail) => {
        if (!cancelled) setUserDetailData(detail);
      })
      .catch((err) => {
        if (!cancelled) {
          console.warn('Could not load user details:', err);
          setUserDetailData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoadingUserDetail(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedUser?.id]);

  // Confirm Suspend / Reactivate User
  const handleConfirmStatusToggle = async () => {
    if (!suspendingUser) return;
    const nextStatus = !suspendingUser.is_active;
    if (!nextStatus && !suspendReason.trim()) {
      setActionMsg({ type: 'error', text: 'Mandatory reason is required to suspend an enterprise user account.' });
      return;
    }

    setIsSubmittingSuspend(true);
    try {
      await updateAdminUserStatus(
        suspendingUser.id, 
        nextStatus, 
        nextStatus ? 'Reactivated by workspace admin' : suspendReason.trim()
      );
      setActionMsg({ 
        type: 'success', 
        text: `User ${suspendingUser.username} successfully ${nextStatus ? 'reactivated' : 'suspended'}.` 
      });
      setSuspendingUser(null);
      setSuspendReason('');
      fetchUsers();
      if (selectedUser?.id === suspendingUser.id) {
        handleInspectUser(suspendingUser);
      }
    } catch (err) {
      setActionMsg({ type: 'error', text: err?.message || 'Failed to update user status.' });
    } finally {
      setIsSubmittingSuspend(false);
    }
  };

  // Confirm Role Assignment
  const handleConfirmRoleChange = async () => {
    if (!editingRoleUser) return;
    setIsSubmittingRole(true);
    try {
      await updateAdminUserRole(editingRoleUser.id, targetRole);
      setActionMsg({ type: 'success', text: `User ${editingRoleUser.username} role updated to ${targetRole}.` });
      setEditingRoleUser(null);
      fetchUsers();
      if (selectedUser?.id === editingRoleUser.id) {
        handleInspectUser(editingRoleUser);
      }
    } catch (err) {
      setActionMsg({ type: 'error', text: err?.message || 'Failed to update user role.' });
    } finally {
      setIsSubmittingRole(false);
    }
  };

  // KPI Summary
  const userStats = {
    total,
    active: users.filter(u => u.is_active).length,
    suspended: users.filter(u => !u.is_active).length,
    admins: users.filter(u => u.role === 'admin' || u.role === 'super admin').length
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-100 font-sans pb-12">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-lg shadow-purple-500/10">
            <Users size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
              Identity & Access Governance
              <Badge variant="purple">RBAC Control</Badge>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Enterprise directory, tenant partition memberships, effective permissions, and immutable suspension controls.
            </p>
          </div>
        </div>

        <Button 
          variant="secondary"
          size="sm"
          onClick={fetchUsers}
          disabled={loading}
          className="flex items-center gap-2 text-xs self-start sm:self-auto"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin text-purple-400' : ''} />
          {loading ? 'Refreshing...' : 'Refresh Directory'}
        </Button>
      </div>

      {actionMsg && (
        <div className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-3 ${
          actionMsg.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' 
            : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
        }`}>
          <div className="flex items-center gap-2">
            {actionMsg.type === 'success' ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
            <span>{actionMsg.text}</span>
          </div>
          <IconButton variant="ghost" size="xs" onClick={() => setActionMsg(null)} aria-label="Dismiss">
            <X size={13} />
          </IconButton>
        </div>
      )}

      {/* 2. Top KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Total Registered Users"
          value={userStats.total}
          subtitle="Enterprise Identity Directory"
          trend="Authoritative State"
          icon={<Users size={18} className="text-purple-400" />}
        />
        <MetricCard
          title="Active Identities"
          value={userStats.active}
          subtitle="Authenticated Session Allowed"
          trend="Session Validated"
          icon={<UserCheck size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Suspended Accounts"
          value={userStats.suspended}
          subtitle="Access Gated / Denied"
          trend="Audit Locked"
          icon={<UserMinus size={18} className="text-amber-400" />}
        />
        <MetricCard
          title="Privileged Admins"
          value={userStats.admins}
          subtitle="Platform & Workspace Operators"
          trend="RBAC Scope Gated"
          icon={<ShieldCheck size={18} className="text-cyan-400" />}
        />
      </div>

      {/* 3. Search & Filter Bar */}
      <Card className="p-3.5 space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search users by name, username, or email..."
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-1.5 pl-9 pr-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={roleFilter}
              onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
              className="bg-[#0d1117] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500/50"
            >
              <option value="ALL">All Roles</option>
              <option value="admin">Admin</option>
              <option value="member">Member</option>
              <option value="user">User</option>
              <option value="viewer">Viewer</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="bg-[#0d1117] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500/50"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active Only</option>
              <option value="SUSPENDED">Suspended Only</option>
            </select>

            <Button type="submit" variant="primary" size="sm" className="bg-purple-600 hover:bg-purple-500 text-white text-xs">
              Search
            </Button>
          </div>
        </form>
      </Card>

      {/* 4. Users Table */}
      <Card className="overflow-hidden border-white/[0.08] bg-[#0d1017]/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-white/[0.03] border-b border-white/[0.06] text-[11px] uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-3 px-4 font-semibold">User Identity</th>
                <th className="py-3 px-4 font-semibold">Email</th>
                <th className="py-3 px-4 font-semibold">Role</th>
                <th className="py-3 px-4 font-semibold">Workspaces</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Last Active</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {loading ? (
                [1, 2, 3, 4, 5].map((i) => (
                  <tr key={i}>
                    <td colSpan={7} className="py-3 px-4">
                      <Skeleton className="h-6 w-full rounded bg-white/[0.02]" />
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                    No enterprise users match the specified search query or filters.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr 
                    key={u.id}
                    onClick={() => setSelectedUser(u)}
                    className="hover:bg-white/[0.02] transition cursor-pointer"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-purple-500/15 border border-purple-500/30 flex items-center justify-center font-bold text-[11px] text-purple-300 shrink-0">
                          {u.username ? u.username.slice(0, 2).toUpperCase() : 'U'}
                        </div>
                        <div>
                          <span className="font-bold text-white block">{u.username}</span>
                          <span className="font-mono text-[10px] text-slate-500">{u.id.slice(0, 8)}...</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">{u.email}</td>
                    <td className="py-3 px-4">
                      <Badge variant={u.role === 'admin' || u.role === 'super admin' ? 'purple' : 'cyan'} size="xs">
                        {u.role}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px]">{u.workspaces_count || u.workspaces?.length || 1}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={u.is_active ? 'ACTIVE' : 'SUSPENDED'} label={u.is_active ? 'Active' : 'Suspended'} size="xs" />
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {u.last_activity ? new Date(u.last_activity).toLocaleDateString() : 'Recent'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedUser(u);
                          }}
                          className="text-cyan-300 hover:text-white text-xs py-0.5 px-2"
                        >
                          Inspect User
                        </Button>
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingRoleUser(u);
                            setTargetRole(u.role || 'member');
                          }}
                          className="text-purple-300 hover:text-white text-xs py-0.5 px-2"
                          title="Change Role"
                        >
                          Role
                        </Button>
                        <Button
                          variant={u.is_active ? 'danger' : 'secondary'}
                          size="xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSuspendingUser(u);
                            setSuspendReason('');
                          }}
                          className="text-xs py-0.5 px-2"
                        >
                          {u.is_active ? 'Suspend' : 'Reactivate'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="p-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-400">
          <span>Showing {users.length} of {total} users</span>
          <div className="flex items-center gap-2">
            <IconButton
              variant="ghost"
              size="xs"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              aria-label="Previous Page"
            >
              <ChevronLeft size={14} />
            </IconButton>
            <span className="font-mono text-white">Page {page} of {totalPages}</span>
            <IconButton
              variant="ghost"
              size="xs"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              aria-label="Next Page"
            >
              <ChevronRight size={14} />
            </IconButton>
          </div>
        </div>
      </Card>

      {/* 5. User Inspector Drawer */}
      <Drawer
        isOpen={Boolean(selectedUser)}
        onClose={() => setSelectedUser(null)}
        title="User Governance Inspector"
        description="Comprehensive identity details, workspace memberships, and effective permissions."
        size="md"
      >
        {selectedUser && (
          <div className="space-y-5 text-xs text-slate-300">
            {/* Identity Card */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/40 flex items-center justify-center font-bold text-white">
                    {selectedUser.username ? selectedUser.username.slice(0, 2).toUpperCase() : 'U'}
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">{selectedUser.username}</h3>
                    <span className="text-[11px] text-slate-400">{selectedUser.email}</span>
                  </div>
                </div>
                <StatusBadge status={selectedUser.is_active ? 'ACTIVE' : 'SUSPENDED'} label={selectedUser.is_active ? 'Active' : 'Suspended'} />
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/[0.04] text-[11px]">
                <div>
                  <span className="text-slate-500 block">User ID:</span>
                  <span className="font-mono text-slate-300 truncate block">{selectedUser.id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Assigned Role:</span>
                  <Badge variant="purple" className="mt-0.5">{selectedUser.role}</Badge>
                </div>
              </div>
            </div>

            {/* Effective Permissions Explainer */}
            <div className="space-y-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider block">
                Effective Permissions (Derived from {selectedUser.role})
              </span>
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] max-h-48 overflow-y-auto space-y-1">
                {(ROLE_PERMISSIONS[selectedUser.role] || ROLE_PERMISSIONS.member).map((perm, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-[11px] font-mono text-emerald-300">
                    <Check size={12} className="text-emerald-400 shrink-0" />
                    <span>{perm}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Workspace Memberships */}
            <div className="space-y-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider block">
                Workspace Partition Memberships
              </span>
              <div className="space-y-1.5">
                {(selectedUser.workspaces || [
                  { workspace_id: 'ws-prod-01', workspace_name: 'Primary Enterprise Workspace', role: selectedUser.role }
                ]).map((ws, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-black/30 border border-white/[0.04] flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-white">{ws.workspace_name}</span>
                    <Badge variant="cyan" size="xs">{ws.role || 'Member'}</Badge>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Audit Logs */}
            {userDetailData?.recent_audit_logs && userDetailData.recent_audit_logs.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-white/[0.04]">
                <span className="text-xs font-bold text-white uppercase tracking-wider block">
                  Recent User Audit Activity
                </span>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {userDetailData.recent_audit_logs.map((log, idx) => (
                    <div key={idx} className="p-2 rounded bg-white/[0.02] border border-white/[0.04] flex items-center justify-between text-[10px] font-mono">
                      <span className="text-purple-300 font-semibold">{log.action}</span>
                      <span className="text-slate-500">{new Date(log.created_at).toLocaleTimeString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons in Drawer */}
            <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between">
              <Button
                variant={selectedUser.is_active ? 'danger' : 'secondary'}
                size="sm"
                onClick={() => {
                  setSuspendingUser(selectedUser);
                  setSuspendReason('');
                }}
              >
                {selectedUser.is_active ? 'Suspend User' : 'Reactivate User'}
              </Button>

              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditingRoleUser(selectedUser);
                  setTargetRole(selectedUser.role || 'member');
                }}
                className="bg-purple-600 hover:bg-purple-500 text-white"
              >
                Assign Role
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* 6. Suspend / Reactivate Confirmation Modal */}
      <Modal
        isOpen={Boolean(suspendingUser)}
        onClose={() => setSuspendingUser(null)}
        title={suspendingUser?.is_active ? 'Suspend Enterprise User' : 'Reactivate Enterprise User'}
        description={
          suspendingUser?.is_active
            ? 'Suspending this user will immediately revoke all active sessions, token grants, and execution capabilities.'
            : 'Reactivating this user will restore their authorized access to workspace resources.'
        }
        size="md"
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 rounded-lg bg-black/40 border border-white/[0.05]">
            <span className="text-slate-400 block">Target Identity:</span>
            <span className="font-bold text-white">{suspendingUser?.username} ({suspendingUser?.email})</span>
          </div>

          {suspendingUser?.is_active && (
            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1 block">
                Mandatory Suspension Reason <span className="text-rose-400">*</span>
              </label>
              <textarea
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                rows={3}
                placeholder="Enter mandatory administrative rationale for compliance audit logging..."
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-2.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-rose-500/50"
              />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.06]">
            <Button variant="secondary" size="sm" onClick={() => setSuspendingUser(null)}>
              Cancel
            </Button>
            <Button
              variant={suspendingUser?.is_active ? 'danger' : 'primary'}
              size="sm"
              disabled={isSubmittingSuspend || (suspendingUser?.is_active && !suspendReason.trim())}
              onClick={handleConfirmStatusToggle}
              className={!suspendingUser?.is_active ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : ''}
            >
              {isSubmittingSuspend ? 'Updating...' : suspendingUser?.is_active ? 'Confirm Suspension' : 'Confirm Reactivation'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* 7. Change Role Modal */}
      <Modal
        isOpen={Boolean(editingRoleUser)}
        onClose={() => setEditingRoleUser(null)}
        title="Assign Enterprise Role"
        description="Update RBAC authorization tier. Role privileges take effect immediately on next request validation."
        size="md"
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 rounded-lg bg-black/40 border border-white/[0.05]">
            <span className="text-slate-400 block">Target User:</span>
            <span className="font-bold text-white">{editingRoleUser?.username} ({editingRoleUser?.email})</span>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Selected Role</label>
            <select
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-purple-500/50"
            >
              <option value="admin">Admin (Full Administrative & Governance Access)</option>
              <option value="member">Member (Create & Execute Workflows, Documents, Agents)</option>
              <option value="user">User (Standard Operational Access)</option>
              <option value="viewer">Viewer (Read-Only Inspection Access)</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.06]">
            <Button variant="secondary" size="sm" onClick={() => setEditingRoleUser(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={isSubmittingRole}
              onClick={handleConfirmRoleChange}
              className="bg-purple-600 hover:bg-purple-500 text-white"
            >
              {isSubmittingRole ? 'Assigning...' : 'Save Role Assignment'}
            </Button>
          </div>
        </div>
      </Modal>

    </div>
  );
}
