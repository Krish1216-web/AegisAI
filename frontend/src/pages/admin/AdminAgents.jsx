import React, { useState, useEffect } from 'react';
import { Bot, Sliders, Cpu, Activity, RefreshCw, CheckCircle2, Clock, Zap } from 'lucide-react';
import { getPlatformCapabilities } from '../../api/platform';

export default function AdminAgents({ addLog }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const res = await getPlatformCapabilities('agent');
      setAgents(res.items || []);
    } catch (err) {
      console.error('Failed to load agent capabilities:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300 font-sans">
      <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Sliders size={20} className="text-purple-400" />
            AI Agent Registry & Orchestration Telemetry
          </h2>
          <p className="text-xs text-slate-500 mt-1">Audit cognitive agent nodes, execution state graphs, required permissions, and lifecycle health.</p>
        </div>

        <button 
          onClick={fetchAgents}
          className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> REFRESH
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.length === 0 ? (
          <div className="col-span-full py-12 text-center text-slate-500 text-xs font-mono">
            {loading ? 'Discovering registered agent capabilities...' : 'No agent capabilities registered.'}
          </div>
        ) : (
          agents.map((agent, idx) => (
            <div key={idx} className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col justify-between gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                    <Bot size={20} />
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${agent.enabled ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                    {agent.enabled ? 'ONLINE' : 'DISABLED'}
                  </span>
                </div>
                <h3 className="font-bold text-sm text-white mt-1">{agent.name}</h3>
                <p className="text-xs text-slate-400">{agent.description}</p>
              </div>

              <div className="flex flex-col gap-2 pt-3 border-t border-[rgba(255,255,255,0.04)] text-[10px] font-mono text-slate-500">
                <div className="flex justify-between">
                  <span>Capability ID:</span>
                  <span className="text-slate-300">{agent.capability_id}</span>
                </div>
                <div className="flex justify-between">
                  <span>Version:</span>
                  <span className="text-slate-300">{agent.version}</span>
                </div>
                <div className="flex justify-between">
                  <span>Permissions:</span>
                  <span className="text-purple-400">{agent.required_permissions.length === 0 ? 'Public' : agent.required_permissions.join(', ')}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
