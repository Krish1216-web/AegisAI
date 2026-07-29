import React, { useState } from 'react';
import { ShieldAlert, Key, Eye, Trash2, Calendar, AlertCircle, Plus, ToggleLeft, ShieldCheck, Lock, Activity } from 'lucide-react';

export default function AdminSecurity() {
  const [keys, setKeys] = useState([
    { id: '1', name: 'OpenAI GPT-4 Gateway', value: 'sk-proj-••••4x91', created: '2026-07-20', status: 'active' },
    { id: '2', name: 'ChromaDB Core Service', value: 'sk-local-••••8a23', created: '2026-07-18', status: 'active' }
  ]);

  const [newKeyName, setNewKeyName] = useState('');
  
  // Custom Permission Matrix Grid Data representation
  const [permissions, setPermissions] = useState([
    { feature: 'Core AI Workspace (Chat)', user: true, admin: true, super: true },
    { feature: 'Workflow Node Builder', user: true, admin: true, super: true },
    { feature: 'Database & MCP Connection', user: false, admin: true, super: true },
    { feature: 'User Suspend/Reboot Node', user: false, admin: true, super: true },
    { feature: 'Agent Telemetry Diagnostics', user: false, admin: true, super: true },
    { feature: 'System Analytics Graphs', user: false, admin: true, super: true },
    { feature: 'Global Config & Keys Rewrite', user: false, admin: false, super: true }
  ]);

  const handleAddKey = (e) => {
    e.preventDefault();
    if (!newKeyName) return;
    const newKey = {
      id: (keys.length + 1).toString(),
      name: newKeyName,
      value: `sk-gen-••••${Math.floor(1000 + Math.random() * 9000)}`,
      created: new Date().toISOString().split('T')[0],
      status: 'active'
    };
    setKeys([...keys, newKey]);
    setNewKeyName('');
  };

  const handleDeleteKey = (id) => {
    setKeys(keys.filter(k => k.id !== id));
  };

  const togglePermission = (idx, role) => {
    setPermissions(prev => prev.map((p, i) => {
      if (i === idx) {
        return {
          ...p,
          [role]: !p[role]
        };
      }
      return p;
    }));
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-wide">Sysadmin Security & Keys Registry</h2>
        <p className="text-xs text-slate-400 mt-1">Configure global role access controls, API key registrations, and inspect authorization logs.</p>
      </div>

      {/* Threat Ticker */}
      <div className="glass-panel p-4 border-purple-500/10 flex items-center justify-between bg-purple-500/5 shrink-0">
        <div className="flex items-center gap-3">
          <Activity size={16} className="text-purple-400 animate-pulse shrink-0" />
          <span className="text-xs text-slate-300 font-mono">SECGUARD: Threat monitoring active. Handshake channels report normal.</span>
        </div>
        <span className="text-[10px] text-purple-400 font-bold bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded">THREAT_LEVEL_ZERO</span>
      </div>

      {/* Grid: Permission Matrix & Key Manager */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left/Center: Permission Matrix Grid */}
        <div className="xl:col-span-2 glass-panel p-5 flex flex-col gap-4">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2 flex items-center gap-2">
            <Lock size={12} className="text-purple-400" /> Enterprise Permission Matrix
          </h4>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)] text-slate-400">
                  <th className="pb-3 font-semibold">Module / Operational Scope</th>
                  <th className="pb-3 font-semibold text-center w-28">User (Operator)</th>
                  <th className="pb-3 font-semibold text-center w-28">Admin</th>
                  <th className="pb-3 font-semibold text-center w-28">Super Admin</th>
                </tr>
              </thead>
              <tbody>
                {permissions.map((p, idx) => (
                  <tr key={idx} className="border-b border-[rgba(255,255,255,0.02)] hover:bg-white/1 transition-colors">
                    <td className="py-3 font-medium text-slate-200">{p.feature}</td>
                    
                    <td className="py-3 text-center">
                      <button
                        onClick={() => togglePermission(idx, 'user')}
                        className={`mx-auto w-6 h-6 rounded flex items-center justify-center border transition-all cursor-pointer ${p.user ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-transparent border-[rgba(255,255,255,0.06)] text-slate-600'}`}
                      >
                        {p.user ? '✓' : '✗'}
                      </button>
                    </td>

                    <td className="py-3 text-center">
                      <button
                        onClick={() => togglePermission(idx, 'admin')}
                        className={`mx-auto w-6 h-6 rounded flex items-center justify-center border transition-all cursor-pointer ${p.admin ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-transparent border-[rgba(255,255,255,0.06)] text-slate-600'}`}
                      >
                        {p.admin ? '✓' : '✗'}
                      </button>
                    </td>

                    <td className="py-3 text-center">
                      <button
                        onClick={() => togglePermission(idx, 'super')}
                        className={`mx-auto w-6 h-6 rounded flex items-center justify-center border transition-all cursor-pointer ${p.super ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-transparent border-[rgba(255,255,255,0.06)] text-slate-600'}`}
                      >
                        {p.super ? '✓' : '✗'}
                      </button>
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Side: Key Manager */}
        <div className="xl:col-span-1 glass-panel p-5 flex flex-col gap-4">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2 flex items-center gap-2">
            <Key size={12} className="text-purple-400" /> API Keys Registry
          </h4>

          {/* New Key Form */}
          <form onSubmit={handleAddKey} className="flex gap-2">
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="e.g. OpenAI Key"
              className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-purple-500/30 flex-1 min-w-0"
            />
            <button type="submit" className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-400 hover:bg-purple-500/20 cursor-pointer shrink-0">
              <Plus size={14} />
            </button>
          </form>

          {/* Keys list */}
          <div className="flex flex-col gap-3 mt-1">
            {keys.map((key) => (
              <div key={key.id} className="p-3 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)] flex justify-between items-center text-xs">
                <div className="min-w-0">
                  <h5 className="font-semibold text-white truncate">{key.name}</h5>
                  <code className="text-[10px] text-slate-500 mt-1 block font-mono">{key.value}</code>
                </div>
                <button
                  onClick={() => handleDeleteKey(key.id)}
                  className="p-1.5 rounded bg-white/3 hover:bg-white/5 border border-[rgba(255,255,255,0.06)] text-slate-500 hover:text-rose-400 cursor-pointer transition-all"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
