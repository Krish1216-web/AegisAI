import React, { useState } from 'react';
import { Play, Plus, Trash2, Download, Upload, Share2, Workflow, HelpCircle, Activity, Settings, Code } from 'lucide-react';

export default function UserWorkflows({ triggerNotification }) {
  const [nodes, setNodes] = useState([
    { id: '1', type: 'Trigger', x: 50, y: 150, title: 'Webhook Trigger', status: 'ready' },
    { id: '2', type: 'Planner', x: 220, y: 150, title: 'Task Decomposition', status: 'ready' },
    { id: '3', type: 'GitHub MCP', x: 390, y: 80, title: 'PR Auditor', status: 'ready' },
    { id: '4', type: 'Research', x: 390, y: 220, title: 'Web Searcher', status: 'ready' },
    { id: '5', type: 'Executor', x: 560, y: 150, title: 'Report Generator', status: 'ready' }
  ]);

  const [activeNode, setActiveNode] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);

  const nodePalette = [
    { type: 'Trigger', color: 'border-yellow-500/30 text-yellow-400 bg-yellow-500/5' },
    { type: 'Planner', color: 'border-cyan-500/30 text-cyan-400 bg-cyan-500/5' },
    { type: 'Research', color: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/5' },
    { type: 'Memory', color: 'border-purple-500/30 text-purple-400 bg-purple-500/5' },
    { type: 'GitHub MCP', color: 'border-blue-500/30 text-blue-400 bg-blue-500/5' },
    { type: 'Browser MCP', color: 'border-pink-500/30 text-pink-400 bg-pink-500/5' },
    { type: 'Database MCP', color: 'border-rose-500/30 text-rose-400 bg-rose-500/5' },
    { type: 'Executor', color: 'border-indigo-500/30 text-indigo-400 bg-indigo-500/5' }
  ];

  const handleAddNode = (type) => {
    const newId = (nodes.length + 1).toString();
    const newNode = {
      id: newId,
      type,
      x: 100 + Math.random() * 200,
      y: 100 + Math.random() * 200,
      title: `${type} Node`,
      status: 'ready'
    };
    setNodes([...nodes, newNode]);
    triggerNotification('Node Added', `Initialized ${type} block on execution grid.`);
  };

  const handleDeleteNode = (id) => {
    setNodes(nodes.filter(node => node.id !== id));
    if (activeNode?.id === id) setActiveNode(null);
  };

  const handleRunWorkflow = () => {
    if (isRunning) return;
    setIsRunning(true);
    setLogs([]);
    
    // Stage-by-stage node glowing simulation
    const steps = [
      { id: '1', log: 'Webhook Trigger activated. Recieved payload.' },
      { id: '2', log: 'Planner Node: Decomposing payload task targets...' },
      { id: '3', log: 'GitHub MCP: Auditing pull request modifications...' },
      { id: '4', log: 'Research Node: Gathering related documentation...' },
      { id: '5', log: 'Executor: Generating audit summaries and files...' }
    ];

    steps.forEach((step, idx) => {
      setTimeout(() => {
        setNodes(prev => prev.map(n => n.id === step.id ? { ...n, status: 'running' } : n));
        setLogs(prev => [...prev, `[${new Date().toTimeString().split(' ')[0]}] ${step.log}`]);
        
        setTimeout(() => {
          setNodes(prev => prev.map(n => n.id === step.id ? { ...n, status: 'completed' } : n));
          if (idx === steps.length - 1) {
            setIsRunning(false);
            triggerNotification('Workflow Completed', 'AegisAI workspace workflow pipeline finished with 100% success.');
          }
        }, 1000);
      }, idx * 1500);
    });
  };

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-140px)] animate-fade-in overflow-hidden">
      
      {/* Action Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">Multi-Agent Workflow Builder</h2>
          <p className="text-xs text-slate-400 mt-1">Design, execute, and monitor agent pipelines and MCP nodes.</p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={handleRunWorkflow} disabled={isRunning} className="btn-primary py-2 px-4 rounded-lg text-xs font-semibold shrink-0 cursor-pointer disabled:opacity-50">
            <Play size={14} className={isRunning ? 'animate-spin' : ''} /> {isRunning ? 'RUNNING_WORKFLOW...' : 'RUN_WORKFLOW'}
          </button>
          
          <button onClick={() => triggerNotification('Workflow Exported', 'Workspace blueprint downloaded as local JSON.')} className="btn-secondary p-2 rounded-lg text-xs hover:border-cyan-500/20">
            <Download size={14} />
          </button>
          <button onClick={() => triggerNotification('Workflow Shared', 'System hook generated.')} className="btn-secondary p-2 rounded-lg text-xs hover:border-cyan-500/20">
            <Share2 size={14} />
          </button>
        </div>
      </div>

      {/* Main split work-grid */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        
        {/* Left Side: Palette */}
        <div className="w-56 glass-panel p-4 flex flex-col gap-4 bg-[#0d101780] shrink-0 overflow-y-auto">
          <div>
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">Nodes Palette</h4>
            <div className="flex flex-col gap-2">
              {nodePalette.map((n) => (
                <button
                  key={n.type}
                  onClick={() => handleAddNode(n.type)}
                  className={`flex items-center justify-between p-2.5 rounded-lg border text-xs text-left cursor-pointer transition-all hover:bg-white/3 ${n.color}`}
                >
                  <span>{n.type}</span>
                  <Plus size={12} />
                </button>
              ))}
            </div>
          </div>
          
          <div className="mt-auto border-t border-[rgba(255,255,255,0.06)] pt-4">
            <div className="flex items-center gap-2 text-[10px] text-slate-500">
              <HelpCircle size={12} />
              <span>Click a node template to insert it into the active grid canvas.</span>
            </div>
          </div>
        </div>

        {/* Center: Canvas grid */}
        <div className="flex-1 glass-panel relative bg-[#090b10] border-white/5 rounded-xl overflow-hidden flex flex-col">
          {/* Dot Grid Background */}
          <div className="absolute inset-0 pointer-events-none" style={{
            backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 0)',
            backgroundSize: '20px 20px'
          }}></div>

          {/* Active Canvas nodes */}
          <div className="flex-1 p-6 relative overflow-auto">
            {nodes.map((node) => {
              let nodeColor = 'border-slate-500/20';
              if (node.status === 'running') nodeColor = 'border-cyan-500 shadow-lg shadow-cyan-500/10 scale-105';
              if (node.status === 'completed') nodeColor = 'border-emerald-500/50';

              return (
                <div
                  key={node.id}
                  onClick={() => setActiveNode(node)}
                  style={{ left: `${node.x}px`, top: `${node.y}px` }}
                  className={`absolute w-36 glass-panel p-3 border rounded-lg cursor-pointer transition-all ${nodeColor} ${activeNode?.id === node.id ? 'ring-1 ring-cyan-500/30' : ''}`}
                >
                  <div className="flex justify-between items-start">
                    <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 bg-white/5 px-1.5 py-0.5 rounded">{node.type}</span>
                    <button onClick={(e) => { e.stopPropagation(); handleDeleteNode(node.id); }} className="text-slate-500 hover:text-rose-400">
                      <Trash2 size={10} />
                    </button>
                  </div>
                  <h5 className="text-[11px] font-semibold text-white mt-2 truncate">{node.title}</h5>
                  <div className="flex items-center gap-1.5 mt-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${node.status === 'completed' ? 'bg-emerald-400' : node.status === 'running' ? 'bg-cyan-400 animate-ping' : 'bg-slate-500'}`}></span>
                    <span className="text-[9px] text-slate-500 capitalize">{node.status}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Canvas Bottom Terminal Log Output */}
          <div className="h-40 border-t border-[rgba(255,255,255,0.06)] bg-[#07080a] p-4 font-mono text-[10px] flex flex-col gap-2 shrink-0">
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] pb-1.5">
              <span className="text-cyan-400 font-bold tracking-wider flex items-center gap-1.5">
                <Code size={12} /> SYSTEM EXECUTION LOGS
              </span>
              <span className="text-[9px] text-slate-600">STDOUT ticker active</span>
            </div>
            <div className="flex-1 overflow-y-auto flex flex-col gap-1 text-slate-400">
              {logs.length === 0 ? (
                <span className="text-slate-600">// Waiting for workflow trigger signal...</span>
              ) : (
                logs.map((log, idx) => <span key={idx}>{log}</span>)
              )}
            </div>
          </div>
        </div>

        {/* Right Side: Properties configuration inspector panel */}
        {activeNode && (
          <div className="w-64 glass-panel p-4 flex flex-col gap-4 bg-[#0d101780] shrink-0 overflow-y-auto animate-fade-in">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2 flex items-center gap-2">
              <Settings size={12} className="text-cyan-400" /> Block Properties
            </h4>
            
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[9px] text-slate-500 uppercase tracking-wider">Node Name</label>
                <input
                  type="text"
                  value={activeNode.title}
                  onChange={(e) => {
                    const val = e.target.value;
                    setNodes(nodes.map(n => n.id === activeNode.id ? { ...n, title: val } : n));
                    setActiveNode({ ...activeNode, title: val });
                  }}
                  className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded px-2.5 py-1 text-xs text-white outline-none focus:border-cyan-500/30"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[9px] text-slate-500 uppercase tracking-wider">Node ID Type</label>
                <span className="text-xs text-slate-400 font-mono">{activeNode.type}</span>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[9px] text-slate-500 uppercase tracking-wider">Execution coordinates</label>
                <span className="text-xs text-slate-500 font-mono">X: {Math.round(activeNode.x)}, Y: {Math.round(activeNode.y)}</span>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[9px] text-slate-500 uppercase tracking-wider">Parameters</label>
                <textarea
                  placeholder="Insert custom configuration payload (JSON format)..."
                  className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded p-2 text-[10px] text-slate-400 font-mono outline-none h-20 resize-none focus:border-cyan-500/30"
                  defaultValue="{ 'auth_token': 'sk_live_2026', 'retry_attempts': 3 }"
                />
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
