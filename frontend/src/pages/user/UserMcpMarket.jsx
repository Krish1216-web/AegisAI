import React, { useState, useEffect } from 'react';
import { 
  Server, 
  Search, 
  RefreshCw, 
  Plus, 
  Trash2, 
  Play, 
  CheckCircle, 
  AlertCircle, 
  Sliders, 
  Wrench, 
  FileCode, 
  MessageSquare, 
  X, 
  Power, 
  ExternalLink,
  ShieldCheck,
  ChevronRight,
  Code
} from 'lucide-react';
import {
  listMCPServers,
  registerMCPServer,
  updateMCPServer,
  deleteMCPServer,
  discoverServerCapabilities,
  listServerCapabilities,
  enableMCPServer,
  disableMCPServer
} from '../../api/mcp';

export default function UserMcpMarket({ triggerNotification }) {
  const [servers, setServers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  
  // Registration Modal State
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [name, setName] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [transport, setTransport] = useState('sse');
  const [authType, setAuthType] = useState('none');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Capabilities View Modal State
  const [showCapabilitiesModal, setShowCapabilitiesModal] = useState(false);
  const [selectedServer, setSelectedServer] = useState(null);
  const [capabilities, setCapabilities] = useState([]);
  const [activeTab, setActiveTab] = useState('tool');
  const [isLoadingCaps, setIsLoadingCaps] = useState(false);
  const [selectedCap, setSelectedCap] = useState(null);

  // Discovering State per server ID
  const [discoveringIds, setDiscoveringIds] = useState(new Set());

  const fetchServers = async () => {
    setIsLoading(true);
    try {
      const data = await listMCPServers();
      setServers(data.servers || []);
    } catch (err) {
      console.error('Failed to load MCP servers:', err);
      triggerNotification?.('Error', 'Failed to load MCP servers from server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    setFormError('');
    if (!name.trim() || !serverUrl.trim()) {
      setFormError('Server name and connection URL are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      await registerMCPServer({
        name: name.trim(),
        server_url: serverUrl.trim(),
        transport,
        authentication_type: authType,
        description: description.trim() || undefined
      });
      triggerNotification?.('Success', `Registered MCP server '${name}'`);
      setShowRegisterModal(false);
      setName('');
      setServerUrl('');
      setDescription('');
      fetchServers();
    } catch (err) {
      setFormError(err.message || 'Failed to register server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleEnable = async (server) => {
    try {
      if (server.enabled) {
        await disableMCPServer(server.id);
        triggerNotification?.('Server Disabled', `Disabled '${server.name}'`);
      } else {
        await enableMCPServer(server.id);
        triggerNotification?.('Server Enabled', `Enabled '${server.name}'`);
      }
      fetchServers();
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to toggle server state.');
    }
  };

  const handleDelete = async (server) => {
    if (!window.confirm(`Are you sure you want to delete MCP server '${server.name}'?`)) return;
    try {
      await deleteMCPServer(server.id);
      triggerNotification?.('Deleted', `Removed MCP server '${server.name}'`);
      fetchServers();
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to delete server.');
    }
  };

  const handleDiscover = async (server) => {
    setDiscoveringIds(prev => new Set(prev).add(server.id));
    try {
      const res = await discoverServerCapabilities(server.id);
      triggerNotification?.(
        'Discovery Completed', 
        `Discovered ${res.total_tools} tools, ${res.total_resources} resources, ${res.total_prompts} prompts for '${server.name}'`
      );
      fetchServers();
    } catch (err) {
      triggerNotification?.('Discovery Failed', err.message || 'Failed to discover capabilities.');
    } finally {
      setDiscoveringIds(prev => {
        const next = new Set(prev);
        next.delete(server.id);
        return next;
      });
    }
  };

  const handleViewCapabilities = async (server) => {
    setSelectedServer(server);
    setShowCapabilitiesModal(true);
    setIsLoadingCaps(true);
    setSelectedCap(null);
    try {
      const res = await listServerCapabilities(server.id);
      setCapabilities(res.capabilities || []);
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to load capabilities.');
    } finally {
      setIsLoadingCaps(false);
    }
  };

  const filtered = servers.filter(item => 
    item.name.toLowerCase().includes(search.toLowerCase()) || 
    item.server_url.toLowerCase().includes(search.toLowerCase()) ||
    item.transport.toLowerCase().includes(search.toLowerCase())
  );

  const toolsList = capabilities.filter(c => c.capability_type === 'tool');
  const resourcesList = capabilities.filter(c => c.capability_type === 'resource');
  const promptsList = capabilities.filter(c => c.capability_type === 'prompt');

  return (
    <div className="flex flex-col gap-6 animate-fade-in p-2">
      
      {/* Top Header & Actions */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <Server className="w-5 h-5 text-indigo-400" />
            Model Context Protocol (MCP) Registry
          </h2>
          <p className="text-xs text-slate-400 mt-1">Register external tool servers, discover dynamic capabilities, and expand agent tooling safely.</p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search MCP servers..."
              className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition-all"
            />
          </div>

          <button
            onClick={() => setShowRegisterModal(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition shadow-sm shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Add MCP Server</span>
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Registered Servers', value: servers.length.toString(), color: 'text-white' },
          { label: 'Active Servers', value: servers.filter(s => s.status === 'active' && s.enabled).length.toString(), color: 'text-emerald-400' },
          { label: 'SSE / HTTP Links', value: servers.filter(s => s.transport !== 'stdio').length.toString(), color: 'text-indigo-400' },
          { label: 'Discovered Capabilities', value: servers.reduce((acc, s) => acc + (s.capabilities_count || 0), 0).toString(), color: 'text-purple-400' }
        ].map((stat, idx) => (
          <div key={idx} className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col gap-1 backdrop-blur-sm">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">{stat.label}</span>
            <span className={`text-2xl font-bold font-mono mt-1 ${stat.color}`}>{stat.value}</span>
          </div>
        ))}
      </div>

      {/* Server Cards Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
          <span>Loading MCP server registry...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
          <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
            <Server className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">No MCP Servers Registered</h3>
          <p className="text-xs text-slate-400 max-w-sm mt-1">Register an MCP server (such as GitHub, PostgreSQL, or local stdio daemons) to enable capability discovery.</p>
          <button
            onClick={() => setShowRegisterModal(true)}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Register First Server</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((server) => {
            const isDiscovering = discoveringIds.has(server.id);
            const statusBg = 
              server.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              server.status === 'error' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
              server.status === 'disabled' || !server.enabled ? 'bg-slate-800 text-slate-400 border-slate-700' :
              'bg-amber-500/10 text-amber-400 border-amber-500/20';

            return (
              <div 
                key={server.id} 
                className={`bg-slate-900/80 border rounded-2xl p-5 flex flex-col justify-between transition-all ${
                  server.enabled ? 'border-slate-800 hover:border-slate-700 shadow-md' : 'border-slate-800/50 opacity-60'
                }`}
              >
                <div>
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                        <Server className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white tracking-wide">{server.name}</h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 uppercase border border-slate-700">
                            {server.transport}
                          </span>
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase ${statusBg}`}>
                            {server.enabled ? server.status : 'DISABLED'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleToggleEnable(server)}
                        title={server.enabled ? 'Disable Server' : 'Enable Server'}
                        className={`p-1.5 rounded-lg border transition ${
                          server.enabled 
                            ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400 hover:bg-emerald-900/40' 
                            : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <Power className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(server)}
                        title="Delete Server"
                        className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-rose-950/40 border border-slate-700/60 hover:border-rose-500/40 text-slate-400 hover:text-rose-400 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                    {server.description || 'No description provided.'}
                  </p>

                  <div className="mt-3 p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px] font-mono text-slate-400 truncate">
                    {server.server_url}
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                  <div className="text-[11px] text-slate-400">
                    <span className="font-semibold text-indigo-300">{server.capabilities_count || 0}</span> capabilities
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDiscover(server)}
                      disabled={isDiscovering || !server.enabled}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/80 disabled:opacity-50 text-slate-200 text-xs font-medium rounded-lg flex items-center gap-1.5 transition"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isDiscovering ? 'animate-spin text-indigo-400' : ''}`} />
                      <span>{isDiscovering ? 'Discovering...' : 'Discover'}</span>
                    </button>
                    <button
                      onClick={() => handleViewCapabilities(server)}
                      className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-medium rounded-lg flex items-center gap-1 transition"
                    >
                      <span>Capabilities</span>
                      <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {/* Register Server Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                Register MCP Server
              </h3>
              <button onClick={() => setShowRegisterModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleRegister} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Server Name *</label>
                <input
                  type="text"
                  placeholder="e.g. GitHub Workspace Server"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Connection URL / Command Path *</label>
                <input
                  type="text"
                  placeholder="e.g. http://localhost:8000/sse or mock://github"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 font-mono text-xs focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Transport</label>
                  <select
                    value={transport}
                    onChange={(e) => setTransport(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="sse">SSE (Server-Sent Events)</option>
                    <option value="streamable_http">Streamable HTTP</option>
                    <option value="stdio">Process STDIO</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Authentication</label>
                  <select
                    value={authType}
                    onChange={(e) => setAuthType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="none">None (Open)</option>
                    <option value="api_key">API Key</option>
                    <option value="bearer">Bearer Token</option>
                    <option value="oauth">OAuth 2.0</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Describe tools or resources this server provides..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-semibold flex items-center gap-1.5"
                >
                  {isSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isSubmitting ? 'Registering...' : 'Register Server'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Capabilities Inspection Modal */}
      {showCapabilitiesModal && selectedServer && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <Server className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-wide">{selectedServer.name} Capabilities</h3>
                  <p className="text-xs text-slate-400">{capabilities.length} total discovered capabilities</p>
                </div>
              </div>
              <button onClick={() => setShowCapabilitiesModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Capability Type Tabs */}
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs">
              <button
                onClick={() => { setActiveTab('tool'); setSelectedCap(null); }}
                className={`px-3 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition ${
                  activeTab === 'tool' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <Wrench className="w-3.5 h-3.5" />
                <span>Tools ({toolsList.length})</span>
              </button>
              <button
                onClick={() => { setActiveTab('resource'); setSelectedCap(null); }}
                className={`px-3 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition ${
                  activeTab === 'resource' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>Resources ({resourcesList.length})</span>
              </button>
              <button
                onClick={() => { setActiveTab('prompt'); setSelectedCap(null); }}
                className={`px-3 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition ${
                  activeTab === 'prompt' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Prompts ({promptsList.length})</span>
              </button>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 overflow-y-auto min-h-[300px]">
              
              {/* Capabilities List */}
              <div className="space-y-2 overflow-y-auto pr-1">
                {isLoadingCaps ? (
                  <div className="flex items-center justify-center py-12 text-slate-400 text-xs gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                    <span>Loading capabilities...</span>
                  </div>
                ) : (
                  (activeTab === 'tool' ? toolsList : activeTab === 'resource' ? resourcesList : promptsList).length === 0 ? (
                    <div className="text-center py-12 text-slate-500 text-xs">
                      No {activeTab}s discovered. Click "Discover" on server card to synchronize.
                    </div>
                  ) : (
                    (activeTab === 'tool' ? toolsList : activeTab === 'resource' ? resourcesList : promptsList).map((cap) => (
                      <div
                        key={cap.id}
                        onClick={() => setSelectedCap(cap)}
                        className={`p-3 rounded-xl border text-xs cursor-pointer transition flex items-center justify-between ${
                          selectedCap?.id === cap.id 
                            ? 'bg-indigo-950/40 border-indigo-500 text-white' 
                            : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                        }`}
                      >
                        <div className="space-y-1 truncate pr-2">
                          <div className="font-semibold font-mono text-indigo-300">{cap.name}</div>
                          <p className="text-[11px] text-slate-400 truncate">{cap.description || 'No description'}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
                      </div>
                    ))
                  )
                )}
              </div>

              {/* Capability Details & Schema Inspector */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-y-auto space-y-3">
                {selectedCap ? (
                  <div className="space-y-3 text-xs">
                    <div>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {selectedCap.capability_type}
                      </span>
                      <h4 className="text-sm font-bold text-white font-mono mt-2">{selectedCap.name}</h4>
                      <p className="text-slate-400 text-xs mt-1 leading-relaxed">{selectedCap.description || 'No description provided.'}</p>
                    </div>

                    {selectedCap.input_schema && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-semibold text-slate-300">Input Schema (JSON Schema)</span>
                        <pre className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                          {JSON.stringify(selectedCap.input_schema, null, 2)}
                        </pre>
                      </div>
                    )}

                    {selectedCap.metadata && Object.keys(selectedCap.metadata).length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-semibold text-slate-300">Metadata</span>
                        <pre className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                          {JSON.stringify(selectedCap.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs text-center py-12">
                    <Code className="w-6 h-6 mb-2 text-slate-600" />
                    <span>Select a capability from the list to inspect its schema and metadata.</span>
                  </div>
                )}
              </div>

            </div>

          </div>
        </div>
      )}

    </div>
  );
}
