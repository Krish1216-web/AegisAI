import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  BrainCircuit, 
  Layers, 
  Play, 
  History, 
  ShieldCheck, 
  Activity, 
  RefreshCw,
  BarChart3
} from 'lucide-react';

import { 
  getPlatformStatus, 
  getPlatformCapabilities, 
  executePlatformCapability, 
  cancelPlatformExecution 
} from '../../api/platform';
import { useAuth } from '../../context/AuthContext';

import PlatformCapabilityExplorer from '../../components/platform/PlatformCapabilityExplorer';
import PlatformCapabilityDetail from '../../components/platform/PlatformCapabilityDetail';
import PlatformExecutionConsole from '../../components/platform/PlatformExecutionConsole';
import PlatformExecutionTimeline from '../../components/platform/PlatformExecutionTimeline';
import PlatformResultViewer from '../../components/platform/PlatformResultViewer';
import PlatformEvidenceViewer from '../../components/platform/PlatformEvidenceViewer';
import PlatformSecurityPanel from '../../components/platform/PlatformSecurityPanel';
import PlatformExecutionHistory from '../../components/platform/PlatformExecutionHistory';
import PlatformAnalyticsDashboard from '../../components/platform/PlatformAnalyticsDashboard';

export default function UserPlatform({ triggerNotification }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();

  // Navigation State
  const activeTab = searchParams.get('tab') || 'capabilities';
  const initialCapId = searchParams.get('capability');
  const initialExecId = searchParams.get('execution');

  // Platform Data State
  const [status, setStatus] = useState(null);
  const [capabilities, setCapabilities] = useState([]);
  const [selectedCapability, setSelectedCapability] = useState(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isLoadingCaps, setIsLoadingCaps] = useState(true);

  // Execution State
  const [currentExecution, setCurrentExecution] = useState(null);
  const [executionEvents, setExecutionEvents] = useState([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [executionHistory, setExecutionHistory] = useState([]);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);

  // Load Status & Capabilities
  const loadPlatformData = useCallback(async () => {
    try {
      setIsLoadingStatus(true);
      setIsLoadingCaps(true);

      const [statusRes, capsRes] = await Promise.all([
        getPlatformStatus(),
        getPlatformCapabilities()
      ]);

      setStatus(statusRes);
      setCapabilities(capsRes.items || []);

      if (initialCapId && capsRes.items) {
        const found = capsRes.items.find(c => c.capability_id === initialCapId);
        if (found) setSelectedCapability(found);
      } else if (capsRes.items && capsRes.items.length > 0 && !selectedCapability) {
        setSelectedCapability(capsRes.items[0]);
      }
    } catch (err) {
      console.error('Failed to load platform data:', err);
      if (triggerNotification) {
        triggerNotification('Platform Error', 'Failed to load platform capabilities.');
      }
    } finally {
      setIsLoadingStatus(false);
      setIsLoadingCaps(false);
    }
  }, [initialCapId, triggerNotification]);

  useEffect(() => {
    loadPlatformData();
  }, [loadPlatformData]);

  // Handle Tab Switch
  const setTab = (tabName) => {
    const params = new URLSearchParams(searchParams);
    params.set('tab', tabName);
    setSearchParams(params);
  };

  // Select Capability
  const handleSelectCapability = (cap) => {
    setSelectedCapability(cap);
    const params = new URLSearchParams(searchParams);
    params.set('capability', cap.capability_id);
    setSearchParams(params);
  };

  // Trigger Execution
  const handleExecute = async (requestPayload) => {
    try {
      setIsExecuting(true);
      setPendingConfirmation(null);
      setExecutionEvents([
        {
          event_type: 'REQUESTED',
          source_component: 'platform_execution_service',
          timestamp: new Date().toISOString(),
          payload: { action: 'execution_requested', capability: requestPayload.capability_id }
        }
      ]);

      const result = await executePlatformCapability(requestPayload);
      setCurrentExecution(result);

      // Add to execution events
      setExecutionEvents(prev => [
        ...prev,
        {
          event_type: result.status.toUpperCase(),
          source_component: 'platform_dispatcher',
          timestamp: new Date().toISOString(),
          payload: { status: result.status, output: result.output }
        }
      ]);

      // Check for restricted confirmation waiting state
      if (result.status === 'waiting' || result.output?.confirmation_required) {
        setPendingConfirmation({
          tool_name: result.output?.tool_name || 'Restricted Tool',
          token: result.output?.confirmation_token || 'CONFIRM_TOKEN',
          original_payload: requestPayload
        });
      }

      // Add to session history
      setExecutionHistory(prev => [result, ...prev.filter(e => e.execution_id !== result.execution_id)]);

      // Switch to Timeline & Result tab
      setTab('timeline');

      if (triggerNotification) {
        triggerNotification(
          'Execution Completed',
          `Capability ${requestPayload.capability_id} status: ${result.status}`
        );
      }
    } catch (err) {
      console.error('Execution failed:', err);
      const errorResult = {
        execution_id: `err_${Date.now()}`,
        capability_id: requestPayload.capability_id,
        status: 'failed',
        output: {},
        provenance: [],
        warnings: [],
        errors: [{ code: 'EXECUTION_FAILED', message: err.message || 'Execution error' }],
        started_at: new Date().toISOString(),
        duration_ms: 0,
        correlation_id: `corr_${Date.now()}`,
        metadata: {}
      };
      setCurrentExecution(errorResult);
      setTab('timeline');

      if (triggerNotification) {
        triggerNotification('Execution Failed', err.message || 'Execution failed');
      }
    } finally {
      setIsExecuting(false);
    }
  };

  // Handle Confirmation Approval / Rejection
  const handleConfirmExecution = async (approved, token) => {
    if (!pendingConfirmation) return;

    if (!approved) {
      setPendingConfirmation(null);
      if (triggerNotification) {
        triggerNotification('Execution Aborted', 'Restricted tool execution was rejected by operator.');
      }
      return;
    }

    const nextPayload = {
      ...pendingConfirmation.original_payload,
      input_data: {
        ...(pendingConfirmation.original_payload.input_data || {}),
        confirmation_token: token
      }
    };

    setPendingConfirmation(null);
    await handleExecute(nextPayload);
  };

  // Handle Cancellation
  const handleCancelExecution = async (executionId) => {
    try {
      setIsCancelling(true);
      const cancelled = await cancelPlatformExecution(executionId, 'User requested cancellation');
      setCurrentExecution(cancelled);
      setExecutionHistory(prev => prev.map(e => e.execution_id === executionId ? cancelled : e));
      if (triggerNotification) {
        triggerNotification('Execution Cancelled', `Execution ${executionId} cancelled successfully.`);
      }
    } catch (err) {
      console.error('Cancellation failed:', err);
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto pb-16">
      {/* Top Banner: AegisAI Platform Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 p-6 rounded-2xl bg-gradient-to-r from-[#0d1017] via-[#101726] to-[#0d1017] border border-[rgba(255,255,255,0.08)] shadow-2xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-center gap-4 relative z-10">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-400 to-purple-500 flex items-center justify-center shadow-lg shadow-cyan-500/20 shrink-0">
            <BrainCircuit size={28} className="text-black" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-slate-100 font-sans">
                AegisAI Unified Platform
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold font-mono uppercase bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                Phase 8.6
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Centralized cognitive execution engine orchestrating Multi-Agent reasoning, Vector/Hybrid RAG, Knowledge Graph traversal, and external MCP tools.
            </p>
          </div>
        </div>

        {/* Platform Telemetry Metrics */}
        <div className="flex items-center gap-4 relative z-10 shrink-0">
          <div className="flex flex-col p-3 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)] min-w-[110px]">
            <span className="text-[10px] uppercase font-bold text-slate-500">Platform Health</span>
            <span className="text-sm font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              {status?.system_health || 'HEALTHY'}
            </span>
          </div>

          <div className="flex flex-col p-3 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)] min-w-[110px]">
            <span className="text-[10px] uppercase font-bold text-slate-500">Active Capabilities</span>
            <span className="text-sm font-bold text-cyan-400 mt-0.5">
              {capabilities.length || status?.active_capabilities || 0}
            </span>
          </div>

          <button
            onClick={loadPlatformData}
            className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-slate-200 border border-[rgba(255,255,255,0.06)] transition-all cursor-pointer"
            title="Refresh Platform State"
          >
            <RefreshCw size={16} className={isLoadingStatus ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-1">
        <div className="flex items-center gap-2 overflow-x-auto">
          <button
            onClick={() => setTab('capabilities')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              activeTab === 'capabilities'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Layers size={14} />
            <span>Capability Explorer ({capabilities.length})</span>
          </button>

          <button
            onClick={() => setTab('execute')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              activeTab === 'execute'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Play size={14} className="fill-current" />
            <span>Execution Console</span>
          </button>

          <button
            onClick={() => setTab('timeline')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              activeTab === 'timeline'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Activity size={14} />
            <span>Lifecycle & Evidence</span>
            {currentExecution && (
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            )}
          </button>

          <button
            onClick={() => setTab('history')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              activeTab === 'history'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <History size={14} />
            <span>Execution History ({executionHistory.length})</span>
          </button>

          <button
            onClick={() => setTab('security')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              activeTab === 'security'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <ShieldCheck size={14} />
            <span>Security & Governance</span>
          </button>

          <button
            onClick={() => setTab('analytics')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              activeTab === 'analytics'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <BarChart3 size={14} />
            <span>Observability & Analytics</span>
          </button>
        </div>
      </div>

      {/* Main Tab Content Panes */}
      <div className="flex flex-col gap-6">
        {/* TAB 1: CAPABILITY EXPLORER & DETAIL */}
        {activeTab === 'capabilities' && (
          <div className="flex flex-col gap-6">
            <PlatformCapabilityExplorer
              capabilities={capabilities}
              selectedCapability={selectedCapability}
              onSelectCapability={handleSelectCapability}
              onOpenExecute={(cap) => {
                handleSelectCapability(cap);
                setTab('execute');
              }}
            />

            {selectedCapability && (
              <PlatformCapabilityDetail
                capability={selectedCapability}
                onOpenExecute={(cap) => {
                  handleSelectCapability(cap);
                  setTab('execute');
                }}
              />
            )}
          </div>
        )}

        {/* TAB 2: EXECUTION CONSOLE */}
        {activeTab === 'execute' && (
          <PlatformExecutionConsole
            capabilities={capabilities}
            selectedCapability={selectedCapability}
            onSelectCapability={handleSelectCapability}
            onExecute={handleExecute}
            isExecuting={isExecuting}
            pendingConfirmation={pendingConfirmation}
            onConfirmExecution={handleConfirmExecution}
          />
        )}

        {/* TAB 3: LIFECYCLE, RESULT & EVIDENCE */}
        {activeTab === 'timeline' && (
          <div className="flex flex-col gap-6">
            <PlatformExecutionTimeline
              execution={currentExecution}
              events={executionEvents}
              onCancelExecution={handleCancelExecution}
              isCancelling={isCancelling}
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
              <PlatformResultViewer execution={currentExecution} />
              <PlatformEvidenceViewer provenance={currentExecution?.provenance || []} />
            </div>
          </div>
        )}

        {/* TAB 4: EXECUTION HISTORY */}
        {activeTab === 'history' && (
          <PlatformExecutionHistory
            history={executionHistory}
            selectedExecutionId={currentExecution?.execution_id}
            onSelectExecution={(exec) => {
              setCurrentExecution(exec);
              setTab('timeline');
            }}
          />
        )}

        {/* TAB 5: SECURITY & GOVERNANCE */}
        {activeTab === 'security' && (
          <PlatformSecurityPanel
            status={status}
            activeWorkspaceId={status?.workspace_id}
            user={user}
          />
        )}

        {/* TAB 6: OBSERVABILITY & ANALYTICS */}
        {activeTab === 'analytics' && (
          <PlatformAnalyticsDashboard
            triggerNotification={triggerNotification}
          />
        )}
      </div>
    </div>
  );
}
