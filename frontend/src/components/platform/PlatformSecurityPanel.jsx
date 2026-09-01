import React from 'react';
import { 
  ShieldCheck, 
  Lock, 
  Users, 
  Key, 
  EyeOff, 
  Server, 
  Database, 
  AlertTriangle,
  CheckCircle2
} from 'lucide-react';

export default function PlatformSecurityPanel({
  status,
  activeWorkspaceId,
  user
}) {
  return (
    <div className="flex flex-col gap-6 bg-[#0d101780] border border-[rgba(255,255,255,0.06)] p-6 rounded-xl backdrop-blur-md">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <div>
          <h4 className="text-sm font-bold text-slate-100 uppercase tracking-wide flex items-center gap-2">
            <ShieldCheck size={16} className="text-cyan-400" />
            <span>Platform Security & Governance Control</span>
          </h4>
          <span className="text-xs text-slate-400 mt-0.5 block">
            Cryptographic tenant isolation, fail-closed RBAC, and untrusted data boundaries
          </span>
        </div>

        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
          <CheckCircle2 size={13} /> Strict Isolation Active
        </span>
      </div>

      {/* Security Context Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Active Tenant / Workspace */}
        <div className="p-4 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.04)] flex flex-col gap-2">
          <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
            <Lock size={13} className="text-cyan-400" /> Tenant Workspace
          </span>
          <span className="text-sm font-bold text-slate-100 truncate">
            {activeWorkspaceId || status?.workspace_id || 'Active Workspace'}
          </span>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            All capability calls enforce strict workspace database partitioning. Cross-tenant access is deterministically denied.
          </p>
        </div>

        {/* User Identity & Role */}
        <div className="p-4 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.04)] flex flex-col gap-2">
          <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
            <Users size={13} className="text-purple-400" /> Caller Security Context
          </span>
          <span className="text-sm font-bold text-slate-100 truncate">
            {user?.email || 'Authenticated User'} ({user?.role || 'Operator'})
          </span>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Identity binding is immutable. User-controlled payload inputs cannot override caller or tenant identity.
          </p>
        </div>

        {/* Secret Sanitization */}
        <div className="p-4 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.04)] flex flex-col gap-2">
          <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
            <EyeOff size={13} className="text-amber-400" /> Credential Scrubbing
          </span>
          <span className="text-sm font-bold text-slate-100">
            Automatic Zero-Leak Redaction
          </span>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            All inputs, outputs, events, and provenance records pass through CredentialStore sanitization before presentation.
          </p>
        </div>
      </div>

      {/* Trust Invariant Guarantees */}
      <div className="p-4 rounded-xl bg-black/30 border border-slate-800 flex flex-col gap-3">
        <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300">
          Core Security Invariants & Policies
        </h5>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-400">
          <div className="flex items-start gap-2">
            <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>Passive Data Policy:</strong> External MCP data and document text are treated purely as passive data and never converted into system instructions.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>Single-Use Confirmation:</strong> Restricted MCP actions require single-use cryptographic tokens bound to user, workspace, and args hash.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>SSRF & Host Blocking:</strong> Resource reading enforces strict host validation, blocking private networks and loopback interfaces.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>Deterministic State Lifecycle:</strong> Executions follow the 6-stage lifecycle with complete audit event provenance.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
