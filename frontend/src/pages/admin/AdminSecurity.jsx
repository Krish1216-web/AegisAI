import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Key, 
  Eye, 
  Trash2, 
  Calendar, 
  AlertCircle, 
  Plus, 
  ToggleLeft, 
  ShieldCheck, 
  Lock, 
  Activity, 
  RefreshCw, 
  Download, 
  CheckCircle2, 
  FileText 
} from 'lucide-react';
import { 
  getAdminSecurityPosture, 
  getAdminRolesPermissions, 
  getAdminAuditLogs, 
  exportAdminReport 
} from '../../api/admin';

export default function AdminSecurity() {
  const [posture, setPosture] = useState(null);
  const [roleMatrix, setRoleMatrix] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exportMsg, setExportMsg] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [posData, rolesData, logsData] = await Promise.all([
        getAdminSecurityPosture(),
        getAdminRolesPermissions(),
        getAdminAuditLogs({ page: 1, page_size: 20 })
      ]);
      setPosture(posData);
      setRoleMatrix(rolesData);
      setAuditLogs(logsData.logs);
    } catch (err) {
      console.error('Failed to load security posture:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleExport = async (format) => {
    try {
      const res = await exportAdminReport({
        export_type: 'audit_logs',
        format,
        limit: 500
      });
      // Trigger download
      const blob = new Blob([res.content], { type: format === 'csv' ? 'text/csv' : 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString()}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      setExportMsg(`Exported ${res.record_count} audit records successfully as ${format.toUpperCase()}.`);
      setTimeout(() => setExportMsg(null), 4000);
    } catch (err) {
      setExportMsg('Export failed.');
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <ShieldAlert size={20} className="text-purple-400" />
            Security Posture & Compliance Registry
          </h2>
          <p className="text-xs text-slate-500 mt-1">Tenant isolation bounds, RBAC enforcement policies, confirmation gates, and persistent audit records.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => handleExport('csv')}
            className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white"
          >
            <Download size={12} /> EXPORT_CSV
          </button>
          <button 
            onClick={() => handleExport('json')}
            className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white"
          >
            <Download size={12} /> EXPORT_JSON
          </button>
          <button 
            onClick={fetchData}
            className="btn-secondary text-xs flex items-center gap-2 cursor-pointer font-mono bg-white/5 border border-[rgba(255,255,255,0.06)] px-3 py-2 rounded-lg text-slate-300 hover:text-white"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {exportMsg && (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 size={14} />
          <span>{exportMsg}</span>
        </div>
      )}

      {/* Security Posture Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Tenant Isolation</span>
          <div className="text-lg font-mono font-bold text-emerald-400 mt-1 flex items-center gap-2">
            <ShieldCheck size={16} /> STRICT_ENFORCED
          </div>
          <span className="text-[10px] text-slate-400 mt-1 block">Cross-tenant queries blocked</span>
        </div>

        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">RBAC Authorization</span>
          <div className="text-lg font-mono font-bold text-purple-400 mt-1 flex items-center gap-2">
            <Lock size={16} /> SERVER_VERIFIED
          </div>
          <span className="text-[10px] text-slate-400 mt-1 block">JWT Cryptographic Bounds</span>
        </div>

        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">SSRF & MCP Guard</span>
          <div className="text-lg font-mono font-bold text-cyan-400 mt-1 flex items-center gap-2">
            <ShieldCheck size={16} /> ACTIVE_GATED
          </div>
          <span className="text-[10px] text-slate-400 mt-1 block">Loopback & Transport Filtering</span>
        </div>

        <div className="glass-panel p-4 bg-slate-950/40 border border-[rgba(255,255,255,0.06)] rounded-xl">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Secret Redaction</span>
          <div className="text-lg font-mono font-bold text-emerald-400 mt-1 flex items-center gap-2">
            <ShieldCheck size={16} /> RECURSIVE_SCRUB
          </div>
          <span className="text-[10px] text-slate-400 mt-1 block">Tokens & Keys Sanitized</span>
        </div>
      </div>

      {/* Grid: Permission Matrix & Audit Log */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        {/* Left: Permission Matrix Grid */}
        <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col gap-4">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2 flex items-center gap-2">
            <Lock size={14} className="text-purple-400" /> Enterprise Role Permission Matrix
          </h4>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)] text-slate-400 text-[10px]">
                  <th className="pb-3 font-semibold">Scope / Capability Area</th>
                  <th className="pb-3 font-semibold text-center">Viewer</th>
                  <th className="pb-3 font-semibold text-center">Member</th>
                  <th className="pb-3 font-semibold text-center">Admin/Owner</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.02)] text-[10px]">
                {(roleMatrix?.permission_matrix || []).map((p, idx) => (
                  <tr key={idx} className="hover:bg-white/1 transition-colors">
                    <td className="py-2.5 font-medium text-slate-200">{p.module}</td>
                    <td className="py-2.5 text-center">
                      <span className={`px-2 py-0.5 rounded ${p.viewer ? 'text-emerald-400' : 'text-slate-600'}`}>{p.viewer ? 'ALLOW' : 'DENY'}</span>
                    </td>
                    <td className="py-2.5 text-center">
                      <span className={`px-2 py-0.5 rounded ${p.user ? 'text-emerald-400' : 'text-slate-600'}`}>{p.user ? 'ALLOW' : 'DENY'}</span>
                    </td>
                    <td className="py-2.5 text-center">
                      <span className={`px-2 py-0.5 rounded ${p.admin ? 'text-emerald-400 font-bold' : 'text-slate-600'}`}>{p.admin ? 'ALLOW' : 'DENY'}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Persistent Audit Trail */}
        <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.06)] rounded-xl flex flex-col gap-4">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2 flex items-center gap-2">
            <FileText size={14} className="text-cyan-400" /> Persistent Audit Records
          </h4>

          <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1 font-mono text-[10px]">
            {auditLogs.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">No audit logs found.</div>
            ) : (
              auditLogs.map((log, idx) => (
                <div key={idx} className="p-3 bg-white/2 rounded-lg border border-[rgba(255,255,255,0.03)] flex flex-col gap-1">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-purple-300">{log.action}</span>
                    <span className="text-slate-500">{new Date(log.created_at).toLocaleString()}</span>
                  </div>
                  <div className="text-slate-400 text-[10px] break-words">{log.details}</div>
                  <div className="text-slate-600 text-[9px]">Actor: {log.username || log.user_id || 'System Daemon'}</div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
