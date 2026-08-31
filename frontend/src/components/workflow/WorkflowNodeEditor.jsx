import React, { useState, useEffect } from 'react';
import {
  X,
  Trash2,
  Settings,
  HelpCircle,
  AlertTriangle,
  Plus,
  Minus,
  Layers,
  Cpu,
  Bot,
  FileSearch,
  GitBranch,
  Bookmark,
  Shield,
  Shuffle
} from 'lucide-react';
import { listWorkspaceTools, listMCPResources, listMCPPrompts } from '../../api/mcp';

export default function WorkflowNodeEditor({
  selectedNode,
  allNodes,
  onUpdateNode,
  onDeleteNode,
  onClose
}) {
  const [name, setName] = useState('');
  const [nodeKey, setNodeKey] = useState('');
  const [isEnabled, setIsEnabled] = useState(true);
  const [config, setConfig] = useState({});

  // MCP integration lookups
  const [mcpTools, setMcpTools] = useState([]);
  const [mcpResources, setMcpResources] = useState([]);
  const [mcpPrompts, setMcpPrompts] = useState([]);
  const [loadingMcp, setLoadingMcp] = useState(false);

  useEffect(() => {
    if (selectedNode) {
      setName(selectedNode.data?.name || '');
      setNodeKey(selectedNode.data?.node_key || '');
      setIsEnabled(selectedNode.data?.is_enabled !== false);
      setConfig(selectedNode.data?.config || {});

      const type = selectedNode.data?.node_type;
      if (type === 'mcp_tool') {
        loadMcpTools();
      } else if (type === 'mcp_resource') {
        loadMcpResources();
      } else if (type === 'mcp_prompt') {
        loadMcpPrompts();
      }
    }
  }, [selectedNode]);

  const loadMcpTools = async () => {
    try {
      setLoadingMcp(true);
      const res = await listWorkspaceTools({ limit: 100 });
      setMcpTools(res.tools || []);
    } catch (e) {
      console.error('Failed to load MCP tools:', e);
    } finally {
      setLoadingMcp(false);
    }
  };

  const loadMcpResources = async () => {
    try {
      setLoadingMcp(true);
      const res = await listMCPResources({ limit: 100 });
      setMcpResources(res.resources || []);
    } catch (e) {
      console.error('Failed to load MCP resources:', e);
    } finally {
      setLoadingMcp(false);
    }
  };

  const loadMcpPrompts = async () => {
    try {
      setLoadingMcp(true);
      const res = await listMCPPrompts({ limit: 100 });
      setMcpPrompts(res.prompts || []);
    } catch (e) {
      console.error('Failed to load MCP prompts:', e);
    } finally {
      setLoadingMcp(false);
    }
  };

  if (!selectedNode) return null;

  const nodeType = selectedNode.data?.node_type || 'agent';

  const handleSave = (newConfig = config, newName = name, newKey = nodeKey, newEnabled = isEnabled) => {
    onUpdateNode(selectedNode.id, {
      ...selectedNode.data,
      name: newName,
      node_key: newKey,
      is_enabled: newEnabled,
      config: newConfig
    });
  };

  const updateConfigField = (field, value) => {
    const updated = { ...config, [field]: value };
    setConfig(updated);
    handleSave(updated);
  };

  // Transform mapping helper
  const handleMappingChange = (key, expr) => {
    const curr = { ...(config.mapping || {}) };
    curr[key] = expr;
    updateConfigField('mapping', curr);
  };

  const handleRemoveMapping = (key) => {
    const curr = { ...(config.mapping || {}) };
    delete curr[key];
    updateConfigField('mapping', curr);
  };

  return (
    <aside className="w-80 bg-slate-950/90 border-l border-slate-800 flex flex-col h-full overflow-hidden select-none z-10 backdrop-blur-md">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Node Inspector
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onDeleteNode(selectedNode.id)}
            className="p-1 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
            title="Delete Node"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Form Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Basic Properties */}
        <div className="space-y-3 p-3 bg-slate-900/60 rounded-xl border border-slate-800/80">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
              Node Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                handleSave(config, e.target.value, nodeKey, isEnabled);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
              Node Key (Unique)
            </label>
            <input
              type="text"
              value={nodeKey}
              onChange={(e) => {
                const cleanKey = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_');
                setNodeKey(cleanKey);
                handleSave(config, name, cleanKey, isEnabled);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs font-mono text-indigo-300 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-slate-300">Enabled</span>
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={(e) => {
                setIsEnabled(e.target.checked);
                handleSave(config, name, nodeKey, e.target.checked);
              }}
              className="w-4 h-4 rounded text-indigo-600 bg-slate-950 border-slate-800"
            />
          </div>
        </div>

        {/* Dynamic Type-specific Configuration Forms */}
        <div className="space-y-3">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
            {nodeType.toUpperCase()} Configuration
          </h4>

          {/* START NODE */}
          {nodeType === 'start' && (
            <div className="space-y-2">
              <label className="text-slate-400 block text-[11px]">Description / Schema</label>
              <textarea
                placeholder="Workflow start trigger description"
                value={config.description || ''}
                onChange={(e) => updateConfigField('description', e.target.value)}
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}

          {/* END NODE */}
          {nodeType === 'end' && (
            <div className="space-y-2">
              <label className="text-slate-400 block text-[11px]">Output Template</label>
              <textarea
                placeholder="e.g. Result: {{nodes.agent_1.output.result}}"
                value={config.output_template || ''}
                onChange={(e) => updateConfigField('output_template', e.target.value)}
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-[11px] text-emerald-300 focus:outline-none focus:border-indigo-500"
              />
              <span className="text-[10px] text-slate-500">Supports variable references like {'{{input.x}}'}, {'{{nodes.k.output}}'}</span>
            </div>
          )}

          {/* AGENT NODE */}
          {nodeType === 'agent' && (
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Agent Type</label>
                <select
                  value={config.agent_type || 'GENERAL'}
                  onChange={(e) => updateConfigField('agent_type', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                >
                  <option value="GENERAL">General Assistant Agent</option>
                  <option value="RESEARCH">Research Agent</option>
                  <option value="ANALYSIS">Analysis Agent</option>
                  <option value="CODER">Coding Agent</option>
                </select>
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Goal / Instruction</label>
                <textarea
                  placeholder="Task goal or prompt for the agent..."
                  value={config.goal || ''}
                  onChange={(e) => updateConfigField('goal', e.target.value)}
                  rows={4}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          )}

          {/* RAG NODE */}
          {nodeType === 'rag' && (
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Retrieval Query</label>
                <input
                  type="text"
                  placeholder="e.g. {{input.query}}"
                  value={config.query || ''}
                  onChange={(e) => updateConfigField('query', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-cyan-300"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Top K</label>
                  <input
                    type="number"
                    value={config.top_k || 5}
                    onChange={(e) => updateConfigField('top_k', parseInt(e.target.value) || 5)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Similarity</label>
                  <input
                    type="number"
                    step="0.05"
                    value={config.similarity_threshold || 0.7}
                    onChange={(e) => updateConfigField('similarity_threshold', parseFloat(e.target.value) || 0.7)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                  />
                </div>
              </div>
            </div>
          )}

          {/* GRAPH NODE */}
          {nodeType === 'graph' && (
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Entity / Query</label>
                <input
                  type="text"
                  placeholder="e.g. {{input.entity_name}}"
                  value={config.query || ''}
                  onChange={(e) => updateConfigField('query', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-indigo-300"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Max Traversal Depth</label>
                <input
                  type="number"
                  value={config.max_depth || 2}
                  onChange={(e) => updateConfigField('max_depth', parseInt(e.target.value) || 2)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                />
              </div>
            </div>
          )}

          {/* MEMORY NODE */}
          {nodeType === 'memory' && (
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Memory Query</label>
                <input
                  type="text"
                  placeholder="e.g. {{input.topic}}"
                  value={config.query || ''}
                  onChange={(e) => updateConfigField('query', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-amber-300"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Category</label>
                <select
                  value={config.category || 'EPISODIC'}
                  onChange={(e) => updateConfigField('category', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                >
                  <option value="EPISODIC">Episodic Memory</option>
                  <option value="SEMANTIC">Semantic Knowledge</option>
                  <option value="PROCEDURAL">Procedural Rules</option>
                </select>
              </div>
            </div>
          )}

          {/* MCP TOOL NODE */}
          {nodeType === 'mcp_tool' && (
            <div className="space-y-3">
              <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[10px] flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 shrink-0" />
                <span>MCP executions require workspace authorization & policy confirmation.</span>
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Select Tool</label>
                {loadingMcp ? (
                  <div className="text-slate-500">Loading tools...</div>
                ) : (
                  <select
                    value={config.tool_name || ''}
                    onChange={(e) => updateConfigField('tool_name', e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                  >
                    <option value="">-- Choose MCP Tool --</option>
                    {mcpTools.map((t) => (
                      <option key={t.id} value={t.name}>
                        {t.name} ({t.server_name || 'MCP'}) - {t.risk_level}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>
          )}

          {/* MCP RESOURCE NODE */}
          {nodeType === 'mcp_resource' && (
            <div className="space-y-3">
              <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[10px]">
                UNTRUSTED_MCP: Resource content is read as untrusted context.
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Resource URI</label>
                <input
                  type="text"
                  placeholder="file:///path or https://..."
                  value={config.uri || ''}
                  onChange={(e) => updateConfigField('uri', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-teal-300"
                />
              </div>
            </div>
          )}

          {/* MCP PROMPT NODE */}
          {nodeType === 'mcp_prompt' && (
            <div className="space-y-3">
              <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[10px]">
                UNTRUSTED_MCP: Prompt template loaded from external MCP server.
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Prompt Name</label>
                <input
                  type="text"
                  placeholder="e.g. summarize_doc"
                  value={config.prompt_name || ''}
                  onChange={(e) => updateConfigField('prompt_name', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-teal-300"
                />
              </div>
            </div>
          )}

          {/* LOCAL TOOL NODE */}
          {nodeType === 'local_tool' && (
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Tool Name</label>
                <input
                  type="text"
                  placeholder="e.g. calculator"
                  value={config.tool_name || ''}
                  onChange={(e) => updateConfigField('tool_name', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200"
                />
              </div>
            </div>
          )}

          {/* CONDITION NODE */}
          {nodeType === 'condition' && (
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Left Operand</label>
                <input
                  type="text"
                  placeholder="e.g. {{input.count}}"
                  value={config.left || ''}
                  onChange={(e) => updateConfigField('left', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-yellow-300"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Operator</label>
                <select
                  value={config.operator || 'equals'}
                  onChange={(e) => updateConfigField('operator', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                >
                  <option value="equals">equals (==)</option>
                  <option value="not_equals">not_equals (!=)</option>
                  <option value="greater_than">greater_than (&gt;)</option>
                  <option value="less_than">less_than (&lt;)</option>
                  <option value="greater_or_equal">greater_or_equal (&gt;=)</option>
                  <option value="less_or_equal">less_or_equal (&lt;=)</option>
                  <option value="contains">contains</option>
                  <option value="not_contains">not_contains</option>
                  <option value="in">in list</option>
                  <option value="not_in">not_in list</option>
                  <option value="starts_with">starts_with</option>
                  <option value="ends_with">ends_with</option>
                  <option value="exists">exists (not empty)</option>
                  <option value="not_exists">not_exists (is empty)</option>
                </select>
              </div>
              {!['exists', 'not_exists'].includes(config.operator) && (
                <div>
                  <label className="text-slate-400 block mb-1">Right Operand</label>
                  <input
                    type="text"
                    placeholder="e.g. 10 or approved"
                    value={config.right !== undefined ? String(config.right) : ''}
                    onChange={(e) => updateConfigField('right', e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200"
                  />
                </div>
              )}
            </div>
          )}

          {/* HUMAN APPROVAL NODE */}
          {nodeType === 'human_approval' && (
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Approval Title</label>
                <input
                  type="text"
                  placeholder="e.g. Review Purchase Request"
                  value={config.title || ''}
                  onChange={(e) => updateConfigField('title', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Approval Message</label>
                <textarea
                  placeholder="Explain what requires human sign-off..."
                  value={config.approval_message || ''}
                  onChange={(e) => updateConfigField('approval_message', e.target.value)}
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Timeout (seconds)</label>
                <input
                  type="number"
                  value={config.timeout || 3600}
                  onChange={(e) => updateConfigField('timeout', parseInt(e.target.value) || 3600)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200"
                />
              </div>
            </div>
          )}

          {/* TRANSFORM NODE */}
          {nodeType === 'transform' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-slate-400 text-[11px]">Field Mappings</label>
                <button
                  type="button"
                  onClick={() => {
                    const nextKey = `field_${Object.keys(config.mapping || {}).length + 1}`;
                    handleMappingChange(nextKey, '{{input.data}}');
                  }}
                  className="flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold"
                >
                  <Plus className="w-3 h-3" /> Add Field
                </button>
              </div>

              <div className="space-y-2">
                {Object.entries(config.mapping || {}).map(([mKey, mExpr]) => (
                  <div key={mKey} className="p-2 bg-slate-900 rounded-lg border border-slate-800 flex items-center gap-2">
                    <input
                      type="text"
                      value={mKey}
                      onChange={(e) => {
                        const newKey = e.target.value;
                        handleRemoveMapping(mKey);
                        handleMappingChange(newKey, mExpr);
                      }}
                      className="w-24 bg-slate-950 border border-slate-800 rounded px-1.5 py-1 font-mono text-[10px] text-slate-200"
                    />
                    <span className="text-slate-500 font-mono">:</span>
                    <input
                      type="text"
                      value={mExpr}
                      onChange={(e) => handleMappingChange(mKey, e.target.value)}
                      className="flex-1 bg-slate-950 border border-slate-800 rounded px-1.5 py-1 font-mono text-[10px] text-blue-300"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveMapping(mKey)}
                      className="text-slate-500 hover:text-rose-400 p-0.5"
                    >
                      <Minus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
                {Object.keys(config.mapping || {}).length === 0 && (
                  <p className="text-[10px] text-slate-500 italic">No mapping fields specified.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
