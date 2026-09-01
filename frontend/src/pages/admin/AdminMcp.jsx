import React, { useState, useEffect } from 'react';
import { Server, Activity, RefreshCw, CheckCircle2, Shield, Wrench, FileCode, Layers } from 'lucide-react';
import { getPlatformCapabilities } from '../../api/platform';

export default function AdminMcp({ addLog }) {
  const [capabilities, setCapabilities] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchCapabilities = async () => {
    setLoading(true);
    try {
      const res = await getPlatformCapabilities('mcp');
      setCapabilities(res.items || []);
    } catch (err) {
      console.error('Failed to load MCP capabilities:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCapabilities();
  }, []);

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300 font-sans">
      <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Server size={20} className="text-cyan-400" />
            MCP Registry & Transport Administration
          </h2>
          <p className="text-xs text-slate-500 mt-1">Inspect Model Context Protocol server registrations, dynamic tool schemas, and security bounds.</p>
        </div>

        <button 
          onClick={fetchCapabilities}
          className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> REFRESH
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {capabilities.length === 0 ? (
          <div className="col-span-full py-12 text-center text-slate-500 text-xs font-mono">
            {loading ? 'Querying active MCP capabilities...' : 'No MCP capabilities registered.'}
          </div>
        ) : (
          capabilities.map((cap, idx) => (
            <div key={idx} className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col justify-between gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                    <Wrench size={18} />
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    GATED_SAFE
                  </span>
                </div>
                <h3 className="font-bold text-sm text-white mt-1">{cap.name}</h3>
                <p className="text-xs text-slate-400">{cap.description}</p>
              </div>

              <div className="flex flex-col gap-2 pt-3 border-t border-[rgba(255,255,255,0.04)] text-[10px] font-mono text-slate-500">
                <div className="flex justify-between">
                  <span>Capability ID:</span>
                  <span className="text-slate-300">{cap.capability_id}</span>
                </div>
                <div className="flex justify-between">
                  <span>Scope:</span>
                  <span className="text-slate-300">{cap.workspace_scope ? 'Workspace' : 'System Wide'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Transport:</span>
                  <span className="text-cyan-400 font-bold">STDIO / SSE Secure</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
