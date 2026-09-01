import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Search, 
  RefreshCw, 
  Shield, 
  UserPlus, 
  Trash2, 
  Archive, 
  Edit2, 
  CheckCircle, 
  AlertCircle,
  X,
  Lock,
  Layers
} from 'lucide-react';
import { 
  getTeams, 
  createTeam, 
  updateTeam, 
  archiveTeam, 
  getTeamMembers, 
  addTeamMember, 
  removeTeamMember 
} from '../../api/teams';

export default function UserTeams({ triggerNotification }) {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);

  // Form states
  const [teamName, setTeamName] = useState('');
  const [teamDesc, setTeamDesc] = useState('');
  const [memberUserId, setMemberUserId] = useState('');
  const [memberRole, setMemberRole] = useState('member');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchTeamsList = async () => {
    try {
      setLoading(true);
      const res = await getTeams({ status: statusFilter, search: search || undefined });
      setTeams(res.teams || []);
      if (selectedTeam) {
        const updated = (res.teams || []).find(t => t.id === selectedTeam.id);
        if (updated) setSelectedTeam(updated);
      }
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to load teams');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchMembersList = async (teamId) => {
    try {
      setLoadingMembers(true);
      const res = await getTeamMembers(teamId);
      setMembers(res.members || []);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to load team members');
      }
    } finally {
      setLoadingMembers(false);
    }
  };

  useEffect(() => {
    fetchTeamsList();
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchTeamsList();
  };

  const handleSelectTeam = (team) => {
    setSelectedTeam(team);
    fetchMembersList(team.id);
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!teamName.trim()) return;
    try {
      setIsSubmitting(true);
      const newTeam = await createTeam({ name: teamName.trim(), description: teamDesc.trim() || undefined });
      if (triggerNotification) {
        triggerNotification('Team Created', `Team '${newTeam.name}' initialized successfully.`);
      }
      setShowCreateModal(false);
      setTeamName('');
      setTeamDesc('');
      fetchTeamsList();
      handleSelectTeam(newTeam);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to create team');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateTeam = async (e) => {
    e.preventDefault();
    if (!selectedTeam || !teamName.trim()) return;
    try {
      setIsSubmitting(true);
      const updated = await updateTeam(selectedTeam.id, { name: teamName.trim(), description: teamDesc.trim() || undefined });
      if (triggerNotification) {
        triggerNotification('Team Updated', `Team details updated.`);
      }
      setShowEditModal(false);
      fetchTeamsList();
      setSelectedTeam(updated);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to update team');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleArchiveTeam = async (team) => {
    if (!window.confirm(`Are you sure you want to archive team '${team.name}'?`)) return;
    try {
      await archiveTeam(team.id);
      if (triggerNotification) {
        triggerNotification('Team Archived', `Team '${team.name}' is now archived.`);
      }
      fetchTeamsList();
      if (selectedTeam?.id === team.id) {
        setSelectedTeam(null);
        setMembers([]);
      }
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to archive team');
      }
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!selectedTeam || !memberUserId.trim()) return;
    try {
      setIsSubmitting(true);
      await addTeamMember(selectedTeam.id, { user_id: memberUserId.trim(), role: memberRole });
      if (triggerNotification) {
        triggerNotification('Member Added', `User invited to team.`);
      }
      setShowAddMemberModal(false);
      setMemberUserId('');
      setMemberRole('member');
      fetchMembersList(selectedTeam.id);
      fetchTeamsList();
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to add member');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveMember = async (userId, username) => {
    if (!selectedTeam) return;
    if (!window.confirm(`Remove '${username}' from team?`)) return;
    try {
      await removeTeamMember(selectedTeam.id, userId);
      if (triggerNotification) {
        triggerNotification('Member Removed', `User removed from team.`);
      }
      fetchMembersList(selectedTeam.id);
      fetchTeamsList();
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to remove member');
      }
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07080a] text-slate-100 overflow-hidden font-sans">
      {/* Header */}
      <div className="p-6 border-b border-[rgba(255,255,255,0.06)] bg-[#090b10] flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Users size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                Team Collaboration & Workspace Access
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono">PHASE 9.1</span>
              </h1>
              <p className="text-xs text-slate-400">Manage workspace-scoped teams, access boundaries, and shared collaboration roles.</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setTeamName('');
              setTeamDesc('');
              setShowCreateModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
          >
            <Plus size={14} /> Create Team
          </button>
          <button
            onClick={fetchTeamsList}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white border border-[rgba(255,255,255,0.06)] transition-all cursor-pointer"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Main Grid: Teams Directory & Detail Inspector */}
      <div className="flex-1 grid grid-cols-12 gap-6 p-6 overflow-hidden">
        {/* Left Column: Teams List (5 cols) */}
        <div className="col-span-5 flex flex-col bg-[#0b0e14] border border-[rgba(255,255,255,0.06)] rounded-xl overflow-hidden shadow-xl">
          {/* Filter Bar */}
          <div className="p-4 border-b border-[rgba(255,255,255,0.06)] flex items-center justify-between gap-3 bg-[#0d1017]">
            <form onSubmit={handleSearchSubmit} className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search teams..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-white/5 border border-[rgba(255,255,255,0.06)] rounded-lg py-1.5 pl-9 pr-3 text-xs text-slate-200 outline-none focus:border-indigo-500/50"
              />
            </form>
            <div className="flex items-center rounded-lg bg-white/5 p-0.5 border border-[rgba(255,255,255,0.06)]">
              <button
                onClick={() => setStatusFilter('active')}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${statusFilter === 'active' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Active
              </button>
              <button
                onClick={() => setStatusFilter('archived')}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${statusFilter === 'archived' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Archived
              </button>
            </div>
          </div>

          {/* Teams Scroll Container */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {loading ? (
              <div className="p-12 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                <RefreshCw size={18} className="animate-spin text-indigo-400" />
                Loading workspace teams...
              </div>
            ) : teams.length === 0 ? (
              <div className="p-12 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                <Layers size={24} className="text-slate-600" />
                No {statusFilter} teams found in this workspace.
              </div>
            ) : (
              teams.map((t) => {
                const isSelected = selectedTeam?.id === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => handleSelectTeam(t)}
                    className={`p-3.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${isSelected ? 'bg-indigo-600/10 border-indigo-500/40 text-slate-100 shadow-md' : 'bg-white/1 border-[rgba(255,255,255,0.04)] text-slate-300 hover:bg-white/3 hover:border-white/10'}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${isSelected ? 'bg-indigo-500 text-white' : 'bg-white/5 text-slate-400'}`}>
                        {t.name.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold text-xs text-slate-100">{t.name}</div>
                        <div className="text-[11px] text-slate-400 line-clamp-1">{t.description || 'No description provided'}</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/5 text-slate-400 flex items-center gap-1 font-mono">
                        <Users size={10} /> {t.member_count}
                      </span>
                      {t.status === 'archived' && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono uppercase">Archived</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Team Inspector & Membership (7 cols) */}
        <div className="col-span-7 flex flex-col bg-[#0b0e14] border border-[rgba(255,255,255,0.06)] rounded-xl overflow-hidden shadow-xl">
          {selectedTeam ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Team Top Header */}
              <div className="p-5 border-b border-[rgba(255,255,255,0.06)] bg-[#0d1017] flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-slate-100">{selectedTeam.name}</h2>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase ${selectedTeam.status === 'active' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'}`}>
                      {selectedTeam.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{selectedTeam.description || 'No description'}</p>
                </div>

                <div className="flex items-center gap-2">
                  {selectedTeam.status === 'active' && (
                    <>
                      <button
                        onClick={() => {
                          setTeamName(selectedTeam.name);
                          setTeamDesc(selectedTeam.description || '');
                          setShowEditModal(true);
                        }}
                        className="p-1.5 rounded-md bg-white/5 hover:bg-white/10 text-slate-300 border border-white/5 transition-all text-xs flex items-center gap-1.5 cursor-pointer"
                      >
                        <Edit2 size={12} /> Edit
                      </button>
                      <button
                        onClick={() => handleArchiveTeam(selectedTeam)}
                        className="p-1.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 transition-all text-xs flex items-center gap-1.5 cursor-pointer"
                      >
                        <Archive size={12} /> Archive
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Members Header */}
              <div className="px-5 py-3 border-b border-[rgba(255,255,255,0.04)] bg-[#0a0d12] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield size={14} className="text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200">Team Membership ({members.length})</span>
                </div>

                {selectedTeam.status === 'active' && (
                  <button
                    onClick={() => {
                      setMemberUserId('');
                      setMemberRole('member');
                      setShowAddMemberModal(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600/80 hover:bg-indigo-600 text-white text-[11px] font-semibold transition-all cursor-pointer"
                  >
                    <UserPlus size={12} /> Add Member
                  </button>
                )}
              </div>

              {/* Members Table */}
              <div className="flex-1 overflow-y-auto p-4">
                {loadingMembers ? (
                  <div className="p-8 text-center text-slate-500 text-xs">Loading membership records...</div>
                ) : members.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 text-xs">No active members in this team.</div>
                ) : (
                  <div className="space-y-2">
                    {members.map((m) => (
                      <div
                        key={m.id}
                        className="p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)] flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-slate-300">
                            {m.username.substring(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-semibold text-xs text-slate-100 flex items-center gap-2">
                              {m.username}
                              <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono uppercase ${m.role === 'owner' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-slate-700 text-slate-300'}`}>
                                {m.role}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-500">{m.email}</div>
                          </div>
                        </div>

                        {selectedTeam.status === 'active' && (
                          <button
                            onClick={() => handleRemoveMember(m.user_id, m.username)}
                            className="p-1.5 rounded-md bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-all cursor-pointer"
                            title="Remove Member"
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8">
              <Users size={36} className="text-slate-700 mb-3" />
              <div className="text-sm font-semibold text-slate-300">Select a Team</div>
              <p className="text-xs text-slate-500 mt-1 text-center max-w-sm">Choose a team from the left directory to view members, collaboration roles, and workspace access rules.</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Create Team */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#0f131a] border border-[rgba(255,255,255,0.1)] rounded-xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Users size={16} className="text-indigo-400" /> Create New Team
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white"><X size={16} /></button>
            </div>

            <form onSubmit={handleCreateTeam} className="mt-4 space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Team Name *</label>
                <input
                  type="text"
                  required
                  maxLength={100}
                  placeholder="e.g. Core Research Team"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  className="w-full bg-white/5 border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Description (Optional)</label>
                <textarea
                  rows={3}
                  maxLength={500}
                  placeholder="Brief description of the team's role in this workspace..."
                  value={teamDesc}
                  onChange={(e) => setTeamDesc(e.target.value)}
                  className="w-full bg-white/5 border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[rgba(255,255,255,0.06)]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating...' : 'Initialize Team'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit Team */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#0f131a] border border-[rgba(255,255,255,0.1)] rounded-xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Edit2 size={16} className="text-indigo-400" /> Edit Team
              </h3>
              <button onClick={() => setShowEditModal(false)} className="text-slate-400 hover:text-white"><X size={16} /></button>
            </div>

            <form onSubmit={handleUpdateTeam} className="mt-4 space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Team Name *</label>
                <input
                  type="text"
                  required
                  maxLength={100}
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  className="w-full bg-white/5 border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Description</label>
                <textarea
                  rows={3}
                  maxLength={500}
                  value={teamDesc}
                  onChange={(e) => setTeamDesc(e.target.value)}
                  className="w-full bg-white/5 border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[rgba(255,255,255,0.06)]">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Member */}
      {showAddMemberModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#0f131a] border border-[rgba(255,255,255,0.1)] rounded-xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <UserPlus size={16} className="text-indigo-400" /> Add Team Member
              </h3>
              <button onClick={() => setShowAddMemberModal(false)} className="text-slate-400 hover:text-white"><X size={16} /></button>
            </div>

            <form onSubmit={handleAddMember} className="mt-4 space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">User UUID *</label>
                <input
                  type="text"
                  required
                  placeholder="Paste workspace user ID (e.g. 550e8400-e29b-41d4-a716-446655440000)"
                  value={memberUserId}
                  onChange={(e) => setMemberUserId(e.target.value)}
                  className="w-full bg-white/5 border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500 font-mono"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">User must already be a member of this workspace.</span>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Team Role</label>
                <select
                  value={memberRole}
                  onChange={(e) => setMemberRole(e.target.value)}
                  className="w-full bg-[#141822] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                >
                  <option value="member">Member</option>
                  <option value="owner">Owner</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[rgba(255,255,255,0.06)]">
                <button
                  type="button"
                  onClick={() => setShowAddMemberModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {isSubmitting ? 'Adding...' : 'Add Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
