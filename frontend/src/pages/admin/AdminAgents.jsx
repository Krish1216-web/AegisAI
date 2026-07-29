import React, { useState } from 'react';
import { Sliders, Bot, Play, Pause, RotateCcw, AlertTriangle, Eye } from 'lucide-react';

export default function AdminAgents({ addLog }) {
  const [agents, setAgents] = useState([
    { id: 'orch', name: 'Orchestrator', role: 'System Coordinator', status: 'active', tasks: 0, latency: '14ms', cpu: 12, memory: '4.8 MB', rate: '99.9%' },
    { id: 'plan', name: 'Planner Agent', role: 'Task Decomposer', status: 'active', tasks: 0, latency: '22ms', cpu: 8, memory: '3.1 MB', rate: '99.5%' },
    { id: 'research', name: 'Research Agent', role: 'Context Gatherer', status: 'active', tasks: 0, latency: '124ms', cpu: 24, memory: '12.2 MB', rate: '98.8%' },
    { id: 'exec', name: 'Executor Agent', role: 'MCP Interface Tool', status: 'active', tasks: 1, latency: '8ms', cpu: 18, memory: '6.4 MB', rate: '99.2%' },
    { id: 'mem', name: 'Memory Agent', role: 'DB Context Manager', status: 'active', tasks: 0, latency: '4ms', cpu: 6, memory: '8.1 MB', rate: '99.7%' },
    { id: 'critic', name: 'Critic Agent', role: 'Quality Checker', status: 'inactive', tasks: 0, latency: '---', cpu: 0, memory: '0.0 MB', rate: '99.8%' }
  ]);

  const [activeLogAgent, setActiveLogAgent] = useState(null);

  const handleToggleAgent = (agentId) => {
    setAgents(prev => prev.map(ag => {
      if (ag.id === agentId) {
        const nextStatus = ag.status === 'active' ? 'inactive' : 'active';
        addLog('SYS', `AI Agent [${ag.name}] has been toggled to: ${nextStatus.toUpperCase()}`, 'info');
        return { ...ag, status: nextStatus, cpu: nextStatus === 'inactive' ? 0 : ag.cpu };
      }
      return ag;
    }));
  };

  const handleRestartAgent = (agentName) => {
    addLog('SYS', `AI Agent [${agentName}] is restarting daemon...`, 'info');
    alert(`Rebooting specialized execution thread for agent: ${agentName}`);
  };

  const getAgentLogs = (id) => {
    switch (id) {
      case 'orch': return ['[INFO] Coordinate loop sync: OK', '[INFO] Awaiting prompt requests...', '[SUCCESS] Task resolved in 14.5s'];
      case 'plan': return ['[INFO] Decomposing prompt schemas', '[INFO] Tasks priority mapped: Pending', '[SUCCESS] Exec plan finalized'];
      case 'exec': return ['[INFO] Launching stdio subprocesses', '[INFO] Write file permission granted', '[SUCCESS] MCP call done'];
      default: return ['[INFO] Thread initialized.', '[INFO] Connection status: normal', '[INFO] Standby.'];
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Header title */}
      <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Sliders size={20} className="text-purple-400" />
            Specialized Agent Monitoring
          </h2>
          <p className="text-xs text-slate-500 mt-1">Audit active agent loops, evaluate success rates, and restart thread subprocesses.</p>
        </div>
      </div>

      {/* Main Grid display */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Side: Agent Cards stack */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((ag) => (
            <div key={ag.id} className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.04)] hover:border-purple-500/20 transition-all flex flex-col gap-3 relative">
              
              {/* Header info */}
              <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.04)] pb-2">
                <div className="flex items-center gap-2.5">
                  <div className={`w-2.5 h-2.5 rounded-full ${ag.status === 'active' ? 'bg-green-400 animate-pulse' : 'bg-rose-500'}`}></div>
                  <span className="font-bold text-white text-sm">{ag.name}</span>
                </div>
                <span className="text-[9px] text-slate-500 uppercase">{ag.role}</span>
              </div>

              {/* Specs */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-500">Latency:</span>
                  <span className="font-mono text-slate-300">{ag.latency}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-500">Success Rate:</span>
                  <span className="font-mono text-slate-300">{ag.rate}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-500">CPU Usage:</span>
                  <span className="font-mono text-slate-300">{ag.cpu}%</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-500">Memory Size:</span>
                  <span className="font-mono text-slate-300">{ag.memory}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-between items-center border-t border-[rgba(255,255,255,0.03)] pt-3 mt-auto">
                <button
                  onClick={() => handleToggleAgent(ag.id)}
                  className={`p-1.5 rounded-lg border text-xs flex items-center gap-1.5 cursor-pointer transition-all ${ag.status === 'active' ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}
                >
                  {ag.status === 'active' ? <Pause size={12} /> : <Play size={12} />}
                  {ag.status === 'active' ? 'PAUSE' : 'START'}
                </button>
                
                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveLogAgent(activeLogAgent === ag.id ? null : ag.id)}
                    className="p-1.5 rounded bg-white/2 hover:bg-white/5 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white cursor-pointer"
                    title="Audit Logs"
                  >
                    <Eye size={12} />
                  </button>
                  <button
                    onClick={() => handleRestartAgent(ag.name)}
                    className="p-1.5 rounded bg-white/2 hover:bg-white/5 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white cursor-pointer"
                    title="Restart thread daemon"
                  >
                    <RotateCcw size={12} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Right Side: Log visualizer audit drawer */}
        <div className="glass-panel p-5 bg-[#090b10ab] border-purple-500/10 flex flex-col gap-4">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
            <Bot size={14} className="text-purple-400 animate-pulse" />
            Agent stdout stream
          </h4>

          {activeLogAgent ? (
            <div className="flex-1 flex flex-col gap-3 font-mono text-[10px] text-slate-300">
              <span className="text-[9px] text-slate-500 uppercase">DAEMON LOGS FOR: {activeLogAgent}</span>
              <div className="bg-black/40 p-4 rounded-lg border border-[rgba(255,255,255,0.04)] flex flex-col gap-2 leading-relaxed">
                {getAgentLogs(activeLogAgent).map((log, idx) => (
                  <div key={idx} className="whitespace-pre-wrap">{log}</div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 text-xs py-20 gap-2">
              <AlertTriangle size={18} className="text-purple-400/40" />
              <span>Select the eye icon on any agent card to inspect stdout streams.</span>
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
