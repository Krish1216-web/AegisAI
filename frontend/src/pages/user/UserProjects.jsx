import React, { useState, useEffect } from 'react';
import { 
  FolderKanban, 
  Plus, 
  Search, 
  Users, 
  FileText, 
  Workflow, 
  Bot, 
  Trash2, 
  Archive, 
  RotateCcw, 
  Crown, 
  Link as LinkIcon, 
  Unlink, 
  Shield, 
  CheckCircle, 
  AlertCircle 
} from 'lucide-react';
import { 
  getProjects, 
  createProject, 
  updateProject, 
  archiveProject, 
  restoreProject, 
  transferProjectOwnership,
  getProjectMembers,
  addProjectMember,
  updateProjectMemberRole,
  removeProjectMember,
  getProjectResources,
  linkProjectResource,
  unlinkProjectResource
} from '../../api/projects';
import { getWorkspaceMembers } from '../../api/workspaces';
import { realtimeClient } from '../../api/realtime';
import CommentsPanel from '../../components/collaboration/CommentsPanel';
import { getProjectActivity } from '../../api/comments';

export default function UserProjects() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [activeTab, setActiveTab] = useState('resources');
  const [members, setMembers] = useState([]);
  const [resources, setResources] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [rtStatus, setRtStatus] = useState('disconnected');

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [showLinkResourceModal, setShowLinkResourceModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);

  // Form states
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [memberRole, setMemberRole] = useState('viewer');
  const [resourceType, setResourceType] = useState('document');
  const [resourceId, setResourceId] = useState('');
  const [transferTargetId, setTransferTargetId] = useState('');
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    loadProjects();
    const token = localStorage.getItem('token');
    if (token) realtimeClient.connect(token);
    const unsubStatus = realtimeClient.onStatusChange(setRtStatus);
    return () => unsubStatus();
  }, [statusFilter]);

  useEffect(() => {
    if (selectedProject) {
      if (activeTab === 'members') loadMembers(selectedProject.id);
      if (activeTab === 'resources') loadResources(selectedProject.id);
      if (activeTab === 'activity') getProjectActivity(selectedProject.id).then(r => setActivities(r.activities || []));
      const pChannel = `project:${selectedProject.id}`;
      const handler = (evt) => {
        if (evt.channel === pChannel || evt.scope === 'project') {
          loadMembers(selectedProject.id);
          loadResources(selectedProject.id);
        }
      };
      realtimeClient.subscribe(pChannel, handler);
      return () => realtimeClient.unsubscribe(pChannel, handler);
    }
  }, [selectedProject, activeTab]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await getProjects({ status: statusFilter, search });
      setProjects(res.projects || []);
      if (res.projects?.length > 0 && !selectedProject) {
        setSelectedProject(res.projects[0]);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async (pId) => {
    try {
      const res = await getProjectMembers(pId);
      setMembers(res.members || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load project members');
    }
  };

  const loadResources = async (pId) => {
    try {
      const res = await getProjectResources(pId);
      setResources(res.resources || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load project resources');
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    try {
      setErrorMsg(null);
      const created = await createProject({ name: newProjectName, description: newProjectDesc });
      setShowCreateModal(false);
      setNewProjectName('');
      setNewProjectDesc('');
      setSuccessMsg(`Project '${created.name}' created!`);
      loadProjects();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to create project');
    }
  };

  const handleArchive = async (pId) => {
    try {
      await archiveProject(pId);
      setSuccessMsg('Project archived.');
      loadProjects();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to archive project');
    }
  };

  const handleRestore = async (pId) => {
    try {
      await restoreProject(pId);
      setSuccessMsg('Project restored.');
      loadProjects();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to restore project');
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!selectedProject || !selectedUserId) return;
    try {
      await addProjectMember(selectedProject.id, selectedUserId, memberRole);
      setShowAddMemberModal(false);
      setSelectedUserId('');
      setSuccessMsg('Member added to project.');
      loadMembers(selectedProject.id);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to add member');
    }
  };

  const handleLinkResource = async (e) => {
    e.preventDefault();
    if (!selectedProject || !resourceId) return;
    try {
      await linkProjectResource(selectedProject.id, resourceType, resourceId);
      setShowLinkResourceModal(false);
      setResourceId('');
      setSuccessMsg('Resource linked to project.');
      loadResources(selectedProject.id);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to link resource');
    }
  };

  const handleUnlink = async (rType, rId) => {
    if (!selectedProject) return;
    try {
      await unlinkProjectResource(selectedProject.id, rType, rId);
      setSuccessMsg('Resource unlinked.');
      loadResources(selectedProject.id);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to unlink resource');
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2 text-white">
            <FolderKanban className="w-7 h-7 text-indigo-400" />
            Shared Projects & Resources
          </h1>
          <p className="text-sm text-gray-400 flex items-center gap-2">
            Collaborate on shared documents, workflows, and agents.
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
              rtStatus === 'connected' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
              rtStatus === 'connecting' || rtStatus === 'reconnecting' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
              'bg-gray-800 text-gray-400'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                rtStatus === 'connected' ? 'bg-emerald-400' :
                rtStatus === 'connecting' || rtStatus === 'reconnecting' ? 'bg-amber-400 animate-pulse' :
                'bg-gray-500'
              }`}></span>
              {rtStatus === 'connected' ? 'Realtime Connected' : rtStatus === 'reconnecting' ? 'Reconnecting' : 'Realtime Offline'}
            </span>
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-medium transition"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {errorMsg && (
        <div className="bg-red-950/60 border border-red-800 text-red-300 px-4 py-3 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />
          {errorMsg}
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-950/60 border border-emerald-800 text-emerald-300 px-4 py-3 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          {successMsg}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left: Project List */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search projects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadProjects()}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-gray-300"
            >
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          <div className="space-y-2">
            {projects.map((p) => (
              <div
                key={p.id}
                onClick={() => setSelectedProject(p)}
                className={`p-3 rounded-lg cursor-pointer transition border ${
                  selectedProject?.id === p.id
                    ? 'bg-indigo-950/40 border-indigo-500'
                    : 'bg-gray-850 hover:bg-gray-800 border-gray-800'
                }`}
              >
                <div className="flex justify-between items-start">
                  <h3 className="font-semibold text-white">{p.name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${p.status === 'active' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-gray-800 text-gray-400'}`}>
                    {p.status}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1 line-clamp-1">{p.description || 'No description'}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                  <span>{p.member_count} members</span>
                  <span>{p.resource_count} resources</span>
                </div>
              </div>
            ))}
            {projects.length === 0 && !loading && (
              <div className="text-center py-8 text-gray-500 text-sm">No projects found.</div>
            )}
          </div>
        </div>

        {/* Right: Project Details & Tabs */}
        <div className="md:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-6">
          {selectedProject ? (
            <>
              <div className="flex justify-between items-start border-b border-gray-800 pb-4">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    {selectedProject.name}
                    {selectedProject.status === 'archived' && (
                      <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">Archived</span>
                    )}
                  </h2>
                  <p className="text-sm text-gray-400 mt-1">{selectedProject.description || 'No description provided.'}</p>
                  <p className="text-xs text-gray-500 mt-1">Owner: {selectedProject.owner_name || 'System'}</p>
                </div>
                <div className="flex gap-2">
                  {selectedProject.status === 'active' ? (
                    <button
                      onClick={() => handleArchive(selectedProject.id)}
                      className="text-xs flex items-center gap-1 bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded-lg border border-gray-700 transition"
                    >
                      <Archive className="w-3.5 h-3.5" />
                      Archive
                    </button>
                  ) : (
                    <button
                      onClick={() => handleRestore(selectedProject.id)}
                      className="text-xs flex items-center gap-1 bg-indigo-900/60 hover:bg-indigo-800 text-indigo-300 px-3 py-1.5 rounded-lg border border-indigo-700 transition"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Restore
                    </button>
                  )}
                </div>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-gray-800">
                <button
                  onClick={() => setActiveTab('resources')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === 'resources'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Linked Resources ({resources.length})
                </button>
                <button
                  onClick={() => setActiveTab('members')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === 'members'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Project Members ({members.length})
                </button>
                <button
                  onClick={() => setActiveTab('comments')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === 'comments'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Comments
                </button>
                <button
                  onClick={() => setActiveTab('activity')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === 'activity'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Activity
                </button>
              </div>

              {/* Resources Tab Content */}
              {activeTab === 'resources' && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-300">Shared in Project</span>
                    <button
                      onClick={() => setShowLinkResourceModal(true)}
                      className="text-xs flex items-center gap-1 bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg transition"
                    >
                      <LinkIcon className="w-3.5 h-3.5" />
                      Link Resource
                    </button>
                  </div>
                  <div className="divide-y divide-gray-800">
                    {resources.map((r) => (
                      <div key={r.id} className="py-3 flex justify-between items-center">
                        <div className="flex items-center gap-3">
                          {r.resource_type === 'document' && <FileText className="w-5 h-5 text-blue-400" />}
                          {r.resource_type === 'workflow' && <Workflow className="w-5 h-5 text-purple-400" />}
                          {r.resource_type === 'agent' && <Bot className="w-5 h-5 text-emerald-400" />}
                          <div>
                            <p className="text-sm font-medium text-white">{r.resource_name || r.resource_id}</p>
                            <p className="text-xs text-gray-500 uppercase">{r.resource_type}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleUnlink(r.resource_type, r.resource_id)}
                          className="text-gray-500 hover:text-red-400 p-1 rounded transition"
                          title="Unlink resource"
                        >
                          <Unlink className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                    {resources.length === 0 && (
                      <div className="text-center py-6 text-gray-500 text-sm">No resources linked to this project.</div>
                    )}
                  </div>
                </div>
              )}

              {/* Comments Tab Content */}
              {activeTab === 'comments' && (
                <CommentsPanel projectId={selectedProject.id} />
              )}

              {/* Activity Tab Content */}
              {activeTab === 'activity' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-gray-300">Project Activity Timeline</h3>
                  <div className="divide-y divide-gray-800">
                    {activities.map((a) => (
                      <div key={a.id} className="py-2.5 flex justify-between items-center text-xs">
                        <div>
                          <p className="font-medium text-white">{a.description}</p>
                          <span className="text-[10px] text-gray-500 uppercase">{a.activity_type}</span>
                        </div>
                        <span className="text-gray-500 text-[10px]">{new Date(a.created_at).toLocaleString()}</span>
                      </div>
                    ))}
                    {activities.length === 0 && (
                      <div className="text-center py-6 text-gray-500 text-xs">No activity recorded yet.</div>
                    )}
                  </div>
                </div>
              )}

              {/* Members Tab Content */}
              {activeTab === 'members' && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-300">Project Collaborators</span>
                    <button
                      onClick={async () => {
                        setShowAddMemberModal(true);
                      }}
                      className="text-xs flex items-center gap-1 bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg transition"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Member
                    </button>
                  </div>
                  <div className="divide-y divide-gray-800">
                    {members.map((m) => (
                      <div key={m.id} className="py-3 flex justify-between items-center">
                        <div>
                          <p className="text-sm font-medium text-white flex items-center gap-2">
                            {m.username}
                            {m.role === 'owner' && <Crown className="w-3.5 h-3.5 text-amber-400" />}
                          </p>
                          <p className="text-xs text-gray-500">{m.email}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded border border-gray-700 uppercase">
                            {m.role}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-16 text-gray-500">Select or create a project to get started.</div>
          )}
        </div>
      </div>

      {/* Modal: Create Project */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full space-y-4">
            <h3 className="text-lg font-bold text-white">Create New Project</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Description</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  rows={3}
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Link Resource */}
      {showLinkResourceModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full space-y-4">
            <h3 className="text-lg font-bold text-white">Link Resource to Project</h3>
            <form onSubmit={handleLinkResource} className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Resource Type</label>
                <select
                  value={resourceType}
                  onChange={(e) => setResourceType(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                >
                  <option value="document">Document</option>
                  <option value="workflow">Workflow</option>
                  <option value="agent">Agent</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Resource ID</label>
                <input
                  type="text"
                  required
                  placeholder="UUID / Resource Identifier"
                  value={resourceId}
                  onChange={(e) => setResourceId(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLinkResourceModal(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium"
                >
                  Link
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
