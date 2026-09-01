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
  RotateCcw,
  Edit2, 
  Mail,
  Clock,
  Crown,
  CheckCircle, 
  AlertCircle,
  X,
  Lock,
  Layers,
  Send,
  UserCheck
} from 'lucide-react';
import { 
  getTeams, 
  createTeam, 
  updateTeam, 
  archiveTeam, 
  restoreTeam,
  transferTeamOwnership,
  getTeamMembers, 
  getEligibleMembers,
  addTeamMember, 
  removeTeamMember,
  createTeamInvitation,
  getTeamInvitations,
  revokeTeamInvitation
} from '../../api/teams';

export default function UserTeams({ triggerNotification }) {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [activeTab, setActiveTab] = useState('members'); // 'members' | 'invitations'

  // Members & Invitations
  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [invitations, setInvitations] = useState([]);
  const [loadingInvitations, setLoadingInvitations] = useState(false);
  const [eligibleMembers, setEligibleMembers] = useState([]);
  const [loadingEligible, setLoadingEligible] = useState(false);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);

  // Form states
  const [teamName, setTeamName] = useState('');
  const [teamDesc, setTeamDesc] = useState('');
  const [selectedEligibleUserId, setSelectedEligibleUserId] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [transferTargetUserId, setTransferTargetUserId] = useState('');
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

  const fetchInvitationsList = async (teamId) => {
    try {
      setLoadingInvitations(true);
      const res = await getTeamInvitations(teamId);
      setInvitations(res.invitations || []);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to load invitations');
      }
    } finally {
      setLoadingInvitations(false);
    }
  };

  const fetchEligibleList = async (teamId) => {
    try {
      setLoadingEligible(true);
      const res = await getEligibleMembers(teamId);
      setEligibleMembers(res.members || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingEligible(false);
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
    fetchInvitationsList(team.id);
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
        triggerNotification('Team Archived', `Team '${team.name}' archived.`);
      }
      fetchTeamsList();
      setSelectedTeam(null);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to archive team');
      }
    }
  };

  const handleRestoreTeam = async (team) => {
    try {
      const restored = await restoreTeam(team.id);
      if (triggerNotification) {
        triggerNotification('Team Restored', `Team '${restored.name}' is now active.`);
      }
      fetchTeamsList();
      setSelectedTeam(restored);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to restore team');
      }
    }
  };

  const handleTransferOwnership = async (e) => {
    e.preventDefault();
    if (!selectedTeam || !transferTargetUserId) return;
    if (!window.confirm('Transferring ownership will demote you to member. Proceed?')) return;
    try {
      setIsSubmitting(true);
      const updated = await transferTeamOwnership(selectedTeam.id, transferTargetUserId);
      if (triggerNotification) {
        triggerNotification('Ownership Transferred', `Team ownership transferred successfully.`);
      }
      setShowTransferModal(false);
      setSelectedTeam(updated);
      fetchMembersList(selectedTeam.id);
      fetchTeamsList();
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to transfer ownership');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendInvite = async (e) => {
    e.preventDefault();
    if (!selectedTeam) return;
    try {
      setIsSubmitting(true);
      await createTeamInvitation(selectedTeam.id, {
        invited_user_id: selectedEligibleUserId || undefined,
        invited_email: !selectedEligibleUserId && inviteEmail.trim() ? inviteEmail.trim() : undefined,
        role: inviteRole
      });
      if (triggerNotification) {
        triggerNotification('Invitation Sent', `Team invitation sent successfully.`);
      }
      setShowInviteModal(false);
      setSelectedEligibleUserId('');
      setInviteEmail('');
      setInviteRole('member');
      fetchInvitationsList(selectedTeam.id);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to send invitation');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevokeInvite = async (invitationId) => {
    if (!window.confirm('Revoke this pending invitation?')) return;
    try {
      await revokeTeamInvitation(invitationId);
      if (triggerNotification) {
        triggerNotification('Invitation Revoked', `Invitation cancelled.`);
      }
      fetchInvitationsList(selectedTeam.id);
    } catch (err) {
      if (triggerNotification) {
        triggerNotification('Error', err.response?.data?.detail || 'Failed to revoke invitation');
      }
    }
  };

  const handleRemoveMember = async (userId, username, role) => {
    if (!selectedTeam) return;
    if (role === 'owner') {
      alert('Cannot remove team owner. Transfer ownership before removal.');
      return;
    }
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
                Team Collaboration & Membership Hub
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono">PHASE 9.2</span>
              </h1>
              <p className="text-xs text-slate-400">Manage workspace teams, invitations, ownership, and role assignments.</p>
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
                No {statusFilter} teams found.
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
                        <div className="font-semibold text-xs text-slate-100 flex items-center gap-2">
                          {t.name}
                          {t.owner_name && (
                            <span className="text-[10px] text-indigo-300 flex items-center gap-1 font-mono font-normal">
                              <Crown size={10} className="text-amber-400" /> {t.owner_name}
                            </span>
                          )}
                        </div>
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

        {/* Right Column: Team Inspector (7 cols) */}
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
                  {selectedTeam.status === 'active' ? (
                    <>
                      <button
                        onClick={() => {
                          setTransferTargetUserId('');
                          setShowTransferModal(true);
                        }}
                        className="p-1.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 transition-all text-xs flex items-center gap-1.5 cursor-pointer"
                        title="Transfer Ownership"
                      >
                        <Crown size={12} /> Transfer
                      </button>
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
                        className="p-1.5 rounded-md bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 transition-all text-xs flex items-center gap-1.5 cursor-pointer"
                      >
                        <Archive size={12} /> Archive
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleRestoreTeam(selectedTeam)}
                      className="p-1.5 rounded-md bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/20 transition-all text-xs flex items-center gap-1.5 cursor-pointer"
                    >
                      <RotateCcw size={12} /> Restore Team
                    </button>
                  )}
                </div>
              </div>

              {/* Navigation Tabs (Members / Invitations) */}
              <div className="px-5 py-2 border-b border-[rgba(255,255,255,0.04)] bg-[#0a0d12] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('members')}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${activeTab === 'members' ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    <Shield size={12} /> Active Members ({members.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('invitations')}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${activeTab === 'invitations' ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    <Mail size={12} /> Invitations ({invitations.length})
                  </button>
                </div>

                {selectedTeam.status === 'active' && (
                  <button
                    onClick={() => {
                      fetchEligibleList(selectedTeam.id);
                      setSelectedEligibleUserId('');
                      setInviteEmail('');
                      setInviteRole('member');
                      setShowInviteModal(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600/80 hover:bg-indigo-600 text-white text-[11px] font-semibold transition-all cursor-pointer"
                  >
                    <UserPlus size={12} /> Invite Member
                  </button>
                )}
              </div>

              {/* Tab Contents */}
              <div className="flex-1 overflow-y-auto p-4">
                {activeTab === 'members' ? (
                  loadingMembers ? (
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
                                {m.role === 'owner' ? (
                                  <span className="text-[9px] px-1.5 py-0.2 rounded font-mono uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                                    <Crown size={9} /> Owner
                                  </span>
                                ) : (
                                  <span className="text-[9px] px-1.5 py-0.2 rounded font-mono uppercase bg-slate-700 text-slate-300">
                                    Member
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-500">{m.email}</div>
                            </div>
                          </div>

                          {selectedTeam.status === 'active' && m.role !== 'owner' && (
                            <button
                              onClick={() => handleRemoveMember(m.user_id, m.username, m.role)}
                              className="p-1.5 rounded-md bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-all cursor-pointer"
                              title="Remove Member"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                ) : (
                  loadingInvitations ? (
                    <div className="p-8 text-center text-slate-500 text-xs">Loading team invitations...</div>
                  ) : invitations.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 text-xs">No pending invitations.</div>
                  ) : (
                    <div className="space-y-2">
                      {invitations.map((inv) => (
                        <div
                          key={inv.id}
                          className="p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)] flex items-center justify-between"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-indigo-950/40 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                              <Mail size={14} />
                            </div>
                            <div>
                              <div className="font-semibold text-xs text-slate-100 flex items-center gap-2">
                                {inv.invited_email || 'Direct User Invite'}
                                <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono uppercase ${inv.status === 'pending' ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-700 text-slate-300'}`}>
                                  {inv.status}
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                                <Clock size={10} /> Expires: {new Date(inv.expires_at).toLocaleDateString()}
                              </div>
                            </div>
                          </div>

                          {inv.status === 'pending' && selectedTeam.status === 'active' && (
                            <button
                              onClick={() => handleRevokeInvite(inv.id)}
                              className="p-1.5 rounded-md bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-all text-xs cursor-pointer"
                              title="Revoke Invitation"
                            >
                              Revoke
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8">
              <Users size={36} className="text-slate-700 mb-3" />
              <div className="text-sm font-semibold text-slate-300">Select a Team</div>
              <p className="text-xs text-slate-500 mt-1 text-center max-w-sm">Choose a team from the left directory to view members, invitations, and manage workspace collaboration.</p>
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

      {/* Modal: Invite Member */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#0f131a] border border-[rgba(255,255,255,0.1)] rounded-xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Mail size={16} className="text-indigo-400" /> Invite to {selectedTeam?.name}
              </h3>
              <button onClick={() => setShowInviteModal(false)} className="text-slate-400 hover:text-white"><X size={16} /></button>
            </div>

            <form onSubmit={handleSendInvite} className="mt-4 space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Select Workspace Member</label>
                <select
                  value={selectedEligibleUserId}
                  onChange={(e) => {
                    setSelectedEligibleUserId(e.target.value);
                    if (e.target.value) setInviteEmail('');
                  }}
                  className="w-full bg-[#141822] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                >
                  <option value="">-- Choose from Workspace Members --</option>
                  {eligibleMembers.map((em) => (
                    <option key={em.user_id} value={em.user_id}>
                      {em.username} ({em.email}) — Role: {em.workspace_role}
                    </option>
                  ))}
                </select>
              </div>

              {!selectedEligibleUserId && (
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Or Invite by Email</label>
                  <input
                    type="email"
                    placeholder="user@workspace.internal"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full bg-white/5 border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Assigned Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full bg-[#141822] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                >
                  <option value="member">Member</option>
                  <option value="owner">Owner</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[rgba(255,255,255,0.06)]">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || (!selectedEligibleUserId && !inviteEmail.trim())}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Send size={12} /> {isSubmitting ? 'Sending...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Transfer Ownership */}
      {showTransferModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#0f131a] border border-[rgba(255,255,255,0.1)] rounded-xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Crown size={16} className="text-amber-400" /> Transfer Team Ownership
              </h3>
              <button onClick={() => setShowTransferModal(false)} className="text-slate-400 hover:text-white"><X size={16} /></button>
            </div>

            <form onSubmit={handleTransferOwnership} className="mt-4 space-y-4">
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200">
                Warning: Transferring ownership will make the selected active member the new primary owner. You will remain as a regular member.
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">Select New Owner *</label>
                <select
                  required
                  value={transferTargetUserId}
                  onChange={(e) => setTransferTargetUserId(e.target.value)}
                  className="w-full bg-[#141822] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                >
                  <option value="">-- Choose an Active Member --</option>
                  {members.filter(m => m.role !== 'owner').map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.username} ({m.email})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[rgba(255,255,255,0.06)]">
                <button
                  type="button"
                  onClick={() => setShowTransferModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !transferTargetUserId}
                  className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {isSubmitting ? 'Transferring...' : 'Confirm Transfer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
