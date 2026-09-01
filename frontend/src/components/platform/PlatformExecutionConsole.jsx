import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Code2, 
  Sliders, 
  Key, 
  Clock, 
  RefreshCw, 
  ShieldAlert
} from 'lucide-react';

export default function PlatformExecutionConsole({
  capabilities = [],
  selectedCapability,
  onSelectCapability,
  onExecute,
  isExecuting = false,
  pendingConfirmation = null,
  onConfirmExecution = null
}) {
  const [activeCapId, setActiveCapId] = useState(selectedCapability?.capability_id || capabilities[0]?.capability_id || '');
  const [editorMode, setEditorMode] = useState('guided'); // 'guided' | 'json'
  
  // Guided inputs state
  const [agentQuery, setAgentQuery] = useState('Analyze system architecture components');
  const [agentModel, setAgentModel] = useState('gpt-4o-mini');
  const [ragQuery, setRagQuery] = useState('What are the core platform security guarantees?');
  const [ragTopK, setRagTopK] = useState(5);
  const [ragThreshold, setRagThreshold] = useState(0.0);
  const [graphEntity, setGraphEntity] = useState('Platform Security Engine');
  const [graphDepth, setGraphDepth] = useState(2);
  const [mcpToolName, setMcpToolName] = useState('echo_service');
  const [mcpArgumentsJson, setMcpArgumentsJson] = useState('{"message": "Hello from Platform Console"}');
  const [mcpRiskLevel, setMcpRiskLevel] = useState('SAFE');
  const [genericJson, setGenericJson] = useState('{\n  "query": "Synthesize platform analysis"\n}');

  // Platform execution controls
  const [timeoutSeconds, setTimeoutSeconds] = useState(30);
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [jsonError, setJsonError] = useState(null);

  // Confirmation Modal state
  const [confirmationTokenInput, setConfirmationTokenInput] = useState('');

  useEffect(() => {
    if (selectedCapability) {
      setActiveCapId(selectedCapability.capability_id);
    }
  }, [selectedCapability]);

  const currentCap = capabilities.find(c => c.capability_id === activeCapId) || selectedCapability;

  const handleGenerateIdempotencyKey = () => {
    setIdempotencyKey(`idem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`);
  };

  const buildPayload = () => {
    if (editorMode === 'json') {
      try {
        const parsed = JSON.parse(genericJson);
        setJsonError(null);
        return parsed;
      } catch (err) {
        setJsonError(`Invalid JSON payload: ${err.message}`);
        return null;
      }
    }

    // Guided mode
    if (!currentCap) return {};

    switch (currentCap.capability_type) {
      case 'agent':
        return {
          query: agentQuery,
          model: agentModel,
          provider: 'openai'
        };
      case 'rag':
        if (currentCap.capability_id.includes('hybrid')) {
          return {
            query: ragQuery,
            top_k: Number(ragTopK),
            graph_depth: Number(graphDepth),
            include_graph: true
          };
        }
        return {
          query: ragQuery,
          top_k: Number(ragTopK),
          similarity_threshold: Number(ragThreshold),
          rerank: true
        };
      case 'knowledge_graph':
        return {
          entity: graphEntity,
          depth: Number(graphDepth)
        };
      case 'mcp':
        let argsObj = {};
        try {
          argsObj = JSON.parse(mcpArgumentsJson);
        } catch {
          argsObj = { raw_args: mcpArgumentsJson };
        }
        return {
          tool_name: mcpToolName,
          risk_level: mcpRiskLevel,
          arguments: argsObj
        };
      case 'intelligence':
        return {
          query: agentQuery,
          mode: 'adaptive',
          confidence_threshold: 0.60
        };
      default:
        try {
          return JSON.parse(genericJson);
        } catch {
          return { input: genericJson };
        }
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = buildPayload();
    if (!payload) return;

    onExecute({
      capability_id: activeCapId,
      input_data: payload,
      idempotency_key: idempotencyKey.trim() || undefined,
      timeout_seconds: Number(timeoutSeconds)
    });
  };

  return (
    <div className="flex flex-col gap-6 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-6 rounded-xl backdrop-blur-md relative">
      {/* Header with Capability Selector & Mode Switcher */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <div className="flex flex-col gap-1 w-full md:w-auto">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Capability</label>
          <select
            value={activeCapId}
            onChange={(e) => {
              setActiveCapId(e.target.value);
              const cap = capabilities.find(c => c.capability_id === e.target.value);
              if (cap && onSelectCapability) onSelectCapability(cap);
            }}
            className="bg-black/50 border border-slate-700/80 rounded-lg px-3 py-1.5 text-sm text-cyan-300 font-semibold outline-none focus:border-cyan-500/50 cursor-pointer"
          >
            {capabilities.map(cap => (
              <option key={cap.capability_id} value={cap.capability_id} className="bg-[#0d1017] text-slate-200">
                {cap.name} ({cap.capability_id})
              </option>
            ))}
          </select>
        </div>

        {/* Guided vs JSON Mode Toggle */}
        <div className="flex items-center bg-black/40 p-1 rounded-lg border border-[rgba(255,255,255,0.04)]">
          <button
            type="button"
            onClick={() => setEditorMode('guided')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              editorMode === 'guided' 
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders size={13} />
            <span>Guided Form</span>
          </button>
          <button
            type="button"
            onClick={() => setEditorMode('json')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              editorMode === 'json' 
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code2 size={13} />
            <span>Raw JSON</span>
          </button>
        </div>
      </div>

      {/* Execution Form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {editorMode === 'json' ? (
          <div className="flex flex-col gap-2">
            <label className="text-xs font-semibold text-slate-300">Input Data Payload (JSON)</label>
            <textarea
              rows={8}
              value={genericJson}
              onChange={(e) => {
                setGenericJson(e.target.value);
                setJsonError(null);
              }}
              className="w-full bg-black/50 border border-slate-800 rounded-lg p-3 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500/50 leading-relaxed resize-y"
              placeholder='{\n  "query": "..."\n}'
            />
            {jsonError && (
              <span className="text-xs text-rose-400 font-medium">{jsonError}</span>
            )}
          </div>
        ) : (
          /* Dynamic Guided Fields */
          <div className="flex flex-col gap-4">
            {currentCap?.capability_type === 'agent' && (
              <>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">User Query / Agent Prompt</label>
                  <textarea
                    rows={3}
                    value={agentQuery}
                    onChange={(e) => setAgentQuery(e.target.value)}
                    className="w-full bg-black/40 border border-slate-700/60 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 resize-none"
                    placeholder="Enter multi-agent instruction..."
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-slate-300">Model</label>
                    <input
                      type="text"
                      value={agentModel}
                      onChange={(e) => setAgentModel(e.target.value)}
                      className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>
                </div>
              </>
            )}

            {currentCap?.capability_type === 'rag' && (
              <>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">RAG Search Query</label>
                  <input
                    type="text"
                    value={ragQuery}
                    onChange={(e) => setRagQuery(e.target.value)}
                    className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                    placeholder="Ask a question against indexed documents..."
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-slate-300">Top K Chunks (Max 50)</label>
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={ragTopK}
                      onChange={(e) => setRagTopK(Number(e.target.value))}
                      className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-slate-300">Similarity Threshold</label>
                    <input
                      type="number"
                      step="0.05"
                      min={0.0}
                      max={1.0}
                      value={ragThreshold}
                      onChange={(e) => setRagThreshold(Number(e.target.value))}
                      className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>
                  {currentCap.capability_id.includes('hybrid') && (
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-slate-300">Graph Expansion Depth</label>
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={graphDepth}
                        onChange={(e) => setGraphDepth(Number(e.target.value))}
                        className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                      />
                    </div>
                  )}
                </div>
              </>
            )}

            {currentCap?.capability_type === 'knowledge_graph' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">Entity Name / Node Identifier</label>
                  <input
                    type="text"
                    value={graphEntity}
                    onChange={(e) => setGraphEntity(e.target.value)}
                    className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">Traversal Depth (Max 5)</label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={graphDepth}
                    onChange={(e) => setGraphDepth(Number(e.target.value))}
                    className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                  />
                </div>
              </div>
            )}

            {currentCap?.capability_type === 'mcp' && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-slate-300">Tool Name</label>
                    <input
                      type="text"
                      value={mcpToolName}
                      onChange={(e) => setMcpToolName(e.target.value)}
                      className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-slate-300">Risk Policy Simulation</label>
                    <select
                      value={mcpRiskLevel}
                      onChange={(e) => setMcpRiskLevel(e.target.value)}
                      className="bg-black/40 border border-slate-700/60 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                    >
                      <option value="SAFE">SAFE (Immediate execution)</option>
                      <option value="RESTRICTED">RESTRICTED (Requires single-use confirmation)</option>
                      <option value="DANGEROUS">DANGEROUS (Blocked)</option>
                    </select>
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">Arguments (JSON)</label>
                  <textarea
                    rows={3}
                    value={mcpArgumentsJson}
                    onChange={(e) => setMcpArgumentsJson(e.target.value)}
                    className="w-full bg-black/40 border border-slate-700/60 rounded-lg p-3 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500/50 resize-none"
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* Advanced Execution Settings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-[rgba(255,255,255,0.04)]">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                <Key size={11} className="text-slate-500" /> Idempotency Key (Optional)
              </label>
              <button
                type="button"
                onClick={handleGenerateIdempotencyKey}
                className="text-[10px] text-cyan-400 hover:underline cursor-pointer"
              >
                Generate
              </button>
            </div>
            <input
              type="text"
              placeholder="e.g. exec_unique_nonce_123"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
              className="bg-black/30 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <Clock size={11} className="text-slate-500" /> Timeout (Seconds)
            </label>
            <input
              type="number"
              min={5}
              max={300}
              value={timeoutSeconds}
              onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
              className="bg-black/30 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/50"
            />
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isExecuting || (currentCap && !currentCap.enabled)}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              isExecuting
                ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 cursor-wait'
                : currentCap && !currentCap.enabled
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-black shadow-lg shadow-cyan-500/20'
            }`}
          >
            {isExecuting ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>Executing Capability...</span>
              </>
            ) : (
              <>
                <Play size={14} className="fill-current" />
                <span>Run Platform Execution</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Confirmation Required Modal (Phase 8.5 MCP Confirmation Flow) */}
      {pendingConfirmation && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f1420] border border-amber-500/40 rounded-xl p-6 max-w-lg w-full shadow-2xl shadow-amber-500/10 flex flex-col gap-4 animate-scale-up">
            <div className="flex items-center gap-3 text-amber-400">
              <ShieldAlert size={24} className="animate-pulse" />
              <div>
                <h4 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
                  Restricted Tool Confirmation Required
                </h4>
                <p className="text-xs text-slate-400">Single-use cryptographic authorization requested</p>
              </div>
            </div>

            <div className="p-3.5 bg-black/40 rounded-lg border border-[rgba(255,255,255,0.06)] text-xs flex flex-col gap-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Tool Name:</span>
                <span className="font-mono text-cyan-300">{pendingConfirmation.tool_name || 'Restricted Tool'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Confirmation Token:</span>
                <span className="font-mono text-[11px] text-amber-300 truncate max-w-xs">{pendingConfirmation.token}</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                This tool has been classified as restricted by the MCP Risk Policy. Execution requires explicit confirmation.
              </p>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => onConfirmExecution && onConfirmExecution(false)}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 cursor-pointer"
              >
                Reject / Abort
              </button>
              <button
                type="button"
                onClick={() => onConfirmExecution && onConfirmExecution(true, pendingConfirmation.token)}
                className="px-5 py-1.5 rounded-lg text-xs font-bold bg-amber-500 hover:bg-amber-400 text-black shadow-md shadow-amber-500/20 cursor-pointer"
              >
                Approve & Execute
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
