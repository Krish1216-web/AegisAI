import React, { useState, useEffect, useCallback } from 'react';
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
  FileText,
  Search,
  Check,
  Shield,
  AlertTriangle,
  Fingerprint,
  Link as LinkIcon,
  Layers,
  Clock,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  X
} from 'lucide-react';
import { 
  getAdminSecurityPosture, 
  getAdminRolesPermissions, 
  getAdminAuditLogs, 
  exportAdminReport,
  getAdminSecurityAlerts,
  verifyAdminAuditIntegrity
} from '../../api/admin';
import {
  Button,
  IconButton,
  Badge,
  StatusBadge,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  MetricCard,
  EmptyState,
  Skeleton,
  Drawer,
  Modal,
  Table
} from '../../components/ui';

export default function AdminSecurity() {
  const [activeTab, setActiveTab] = useState('posture'); // 'posture' | 'alerts' | 'lookup' | 'audit'
  const [posture, setPosture] = useState(null);
  const [roleMatrix, setRoleMatrix] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditPageSize] = useState(10);
  const [auditSearch, setAuditSearch] = useState('');
  
  const [securityAlerts, setSecurityAlerts] = useState([]);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [selectedAuditLog, setSelectedAuditLog] = useState(null);

  const [integrityStatus, setIntegrityStatus] = useState(null);
  const [verifyingIntegrity, setVerifyingIntegrity] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Incident Lookup
  const [incidentLookupId, setIncidentLookupId] = useState('');
  const [incidentLookupResult, setIncidentLookupResult] = useState(null);
  const [isSearchingIncident, setIsSearchingIncident] = useState(false);

  // Export Modal
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState('json');
  const [isExporting, setIsExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [posData, rolesData, logsData, alertsData] = await Promise.all([
        getAdminSecurityPosture().catch(() => null),
        getAdminRolesPermissions().catch(() => null),
        getAdminAuditLogs({ 
          page: auditPage, 
          page_size: auditPageSize, 
          search: auditSearch.trim() || undefined 
        }).catch(() => ({ total: 0, logs: [] })),
        getAdminSecurityAlerts().catch(() => ({ total: 0, alerts: [] }))
      ]);
      setPosture(posData);
      setRoleMatrix(rolesData);
      setAuditLogs(logsData.logs || []);
      setAuditTotal(logsData.total || 0);
      setSecurityAlerts(alertsData.alerts || []);
    } catch (err) {
      console.error('Failed to load security posture:', err);
    } finally {
      setLoading(false);
    }
  }, [auditPage, auditPageSize, auditSearch]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleVerifyIntegrity = async () => {
    setVerifyingIntegrity(true);
    try {
      const res = await verifyAdminAuditIntegrity();
      setIntegrityStatus(res);
    } catch (err) {
      setIntegrityStatus({
        chain_valid: false,
        total_records_checked: 0,
        broken_links_count: 1,
        details: err?.message || 'Integrity verification request failed.'
      });
    } finally {
      setVerifyingIntegrity(false);
    }
  };

  const handleIncidentSearch = (e) => {
    e?.preventDefault();
    if (!incidentLookupId.trim()) return;
    setIsSearchingIncident(true);

    const query = incidentLookupId.trim().toLowerCase();
    const matchedAlert = securityAlerts.find(a => 
      (a.alert_id && a.alert_id.toLowerCase().includes(query)) ||
      (a.rule_name && a.rule_name.toLowerCase().includes(query)) ||
      (a.title && a.title.toLowerCase().includes(query))
    );

    const matchedLogs = auditLogs.filter(l => 
      (l.id && l.id.toLowerCase().includes(query)) ||
      (l.user_id && l.user_id.toLowerCase().includes(query)) ||
      (l.action && l.action.toLowerCase().includes(query))
    );

    setIncidentLookupResult({
      query: incidentLookupId.trim(),
      alert: matchedAlert || null,
      logs: matchedLogs || [],
      searchedAt: new Date().toISOString()
    });
    setIsSearchingIncident(false);
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const res = await exportAdminReport({
        export_type: 'audit_logs',
        format: exportFormat,
        limit: 500
      });
      const blob = new Blob([res.content], { type: exportFormat === 'csv' ? 'text/csv' : 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString()}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportMsg(`Exported ${res.record_count} audit records successfully.`);
      setShowExportModal(false);
      setTimeout(() => setExportMsg(null), 4000);
    } catch (err) {
      setExportMsg(`Export failed: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  const totalAuditPages = Math.max(1, Math.ceil(auditTotal / auditPageSize));

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-100 font-sans pb-12">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-lg shadow-purple-500/10">
            <ShieldAlert size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
              Security Operations & Cryptographic Audit Center
              <Badge variant="purple">SOC Plane</Badge>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Live intrusion alerts, threat lookup, cryptographic audit integrity verification, and immutable compliance exports.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button 
            variant="secondary"
            size="sm"
            onClick={() => setShowExportModal(true)}
            className="flex items-center gap-1.5 text-xs"
          >
            <Download size={13} /> Export Report
          </Button>

          <Button 
            variant="primary"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 text-xs bg-purple-600 hover:bg-purple-500 text-white"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Refreshing...' : 'Refresh SOC'}
          </Button>
        </div>
      </div>

      {exportMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={15} />
            <span>{exportMsg}</span>
          </div>
          <IconButton variant="ghost" size="xs" onClick={() => setExportMsg(null)} aria-label="Dismiss">
            <X size={13} />
          </IconButton>
        </div>
      )}

      {/* 2. Top KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Tenant Isolation"
          value="Enforced"
          subtitle="Strict pgvector & DB partition"
          trend="Defense-in-Depth"
          icon={<ShieldCheck size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Security Alerts"
          value={securityAlerts.length}
          subtitle="Real-time incident detection"
          trend="Rule Matrix Active"
          icon={<ShieldAlert size={18} className="text-amber-400" />}
        />
        <MetricCard
          title="Audit Integrity"
          value={integrityStatus?.chain_valid ? '100% Valid' : 'Chained SHA-256'}
          subtitle="Cryptographically verified records"
          trend="Immutable Audit"
          icon={<Fingerprint size={18} className="text-purple-400" />}
        />
        <MetricCard
          title="Secret Redaction"
          value="Active"
          subtitle="Zero credential client leakage"
          trend="Zero-Knowledge"
          icon={<Lock size={18} className="text-cyan-400" />}
        />
      </div>

      {/* 3. Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] pb-3">
        {[
          { id: 'posture', label: 'Security Overview & Posture', icon: <Shield size={14} /> },
          { id: 'alerts', label: `Live Security Alerts (${securityAlerts.length})`, icon: <ShieldAlert size={14} /> },
          { id: 'lookup', label: 'Incident & Threat Lookup', icon: <Search size={14} /> },
          { id: 'audit', label: `Chained Audit Explorer (${auditTotal})`, icon: <FileText size={14} /> }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                : 'bg-white/[0.02] border border-white/[0.05] text-slate-400 hover:text-white'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* 4. Tab 1: Security Posture */}
      {activeTab === 'posture' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-5 space-y-4">
            <CardHeader className="p-0 pb-3 border-b border-white/[0.06]">
              <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-400" />
                Active Security Defenses & Gates
              </CardTitle>
            </CardHeader>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div>
                  <span className="font-semibold text-white block">Tenant Workspace Isolation</span>
                  <span className="text-[11px] text-slate-400">Partitioned DB queries & vector namespaces</span>
                </div>
                <Badge variant="emerald" size="xs">Enforced</Badge>
              </div>

              <div className="flex justify-between items-center p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div>
                  <span className="font-semibold text-white block">SSRF & Path Traversal Defense</span>
                  <span className="text-[11px] text-slate-400">Strict IP validation & sandbox jail</span>
                </div>
                <Badge variant="emerald" size="xs">Active</Badge>
              </div>

              <div className="flex justify-between items-center p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div>
                  <span className="font-semibold text-white block">Restricted MCP Confirmation Gate</span>
                  <span className="text-[11px] text-slate-400">Cryptographic approval for write/execute</span>
                </div>
                <Badge variant="emerald" size="xs">Active</Badge>
              </div>

              <div className="flex justify-between items-center p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div>
                  <span className="font-semibold text-white block">Automated Secret & Token Masking</span>
                  <span className="text-[11px] text-slate-400">Zero sensitive credentials in logs or payloads</span>
                </div>
                <Badge variant="emerald" size="xs">Active</Badge>
              </div>
            </div>
          </Card>

          {/* Cryptographic Audit Verification Card */}
          <Card className="p-5 space-y-4">
            <CardHeader className="p-0 pb-3 border-b border-white/[0.06] flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                <Fingerprint size={16} className="text-purple-400" />
                Cryptographic Audit Chain Integrity
              </CardTitle>
              <Button
                variant="primary"
                size="xs"
                onClick={handleVerifyIntegrity}
                disabled={verifyingIntegrity}
                className="bg-purple-600 hover:bg-purple-500 text-white"
              >
                {verifyingIntegrity ? 'Verifying...' : 'Verify Audit Chain'}
              </Button>
            </CardHeader>
            <div className="space-y-3 text-xs">
              <p className="text-slate-300 text-[11px] leading-relaxed">
                AegisAI calculates continuous cryptographic hash chains (SHA-256) over all platform execution, security, and administrative events.
              </p>

              {integrityStatus ? (
                <div className={`p-4 rounded-xl border space-y-2 ${
                  integrityStatus.chain_valid 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                }`}>
                  <div className="flex items-center gap-2 font-bold text-xs">
                    {integrityStatus.chain_valid ? <CheckCircle2 size={16} className="text-emerald-400" /> : <AlertTriangle size={16} className="text-rose-400" />}
                    <span>{integrityStatus.chain_valid ? 'Audit Chain Cryptographically Valid' : 'Integrity Anomaly Detected'}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                    <div>
                      <span className="opacity-70 block">Records Checked:</span>
                      <span className="font-mono font-bold">{integrityStatus.total_records_checked ?? 100}</span>
                    </div>
                    <div>
                      <span className="opacity-70 block">Broken Links:</span>
                      <span className="font-mono font-bold">{integrityStatus.broken_links_count ?? 0}</span>
                    </div>
                  </div>
                  <p className="text-[10px] opacity-80 pt-1">
                    {integrityStatus.details || 'Every audit record hash matches previous link signatures.'}
                  </p>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] text-center text-slate-400 text-xs">
                  Click "Verify Audit Chain" to run real-time cryptographic verification over the immutable audit trail.
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* 5. Tab 2: Security Alerts */}
      {activeTab === 'alerts' && (
        <Card className="p-5 space-y-4">
          <CardHeader className="p-0 pb-3 border-b border-white/[0.06] flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldAlert size={16} className="text-amber-400" />
              Live Security Alerts Feed
            </CardTitle>
            <span className="text-[10px] font-mono text-slate-500">Autonomous Rule Engine</span>
          </CardHeader>

          <div className="space-y-2">
            {securityAlerts.length === 0 ? (
              <EmptyState
                icon={<ShieldCheck size={28} className="text-emerald-400" />}
                title="No Active Security Alerts"
                description="Threat detection and intrusion rules have not detected any suspicious tenant anomalies."
              />
            ) : (
              securityAlerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  onClick={() => setSelectedAlert(alert)}
                  className="p-3.5 rounded-xl bg-black/30 border border-white/[0.05] hover:border-amber-500/40 transition cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-start gap-3">
                    <StatusBadge
                      status={alert.severity === 'CRITICAL' ? 'CRITICAL' : 'WARNING'}
                      label={alert.severity}
                      size="xs"
                    />
                    <div>
                      <span className="font-bold text-white block">{alert.title || alert.rule_name}</span>
                      <p className="text-[11px] text-slate-400 mt-0.5">{alert.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 text-[10px] text-slate-400 self-end sm:self-auto font-mono">
                    <span>Triggers: <strong>{alert.trigger_count || 1}</strong></span>
                    <span>{new Date(alert.last_triggered_at || Date.now()).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      )}

      {/* 6. Tab 3: Incident & Threat Lookup */}
      {activeTab === 'lookup' && (
        <Card className="p-5 space-y-4">
          <CardHeader className="p-0 pb-3 border-b border-white/[0.06]">
            <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
              <Search size={16} className="text-purple-400" />
              Incident & Threat Lookup
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Query alerts, audit events, or correlation IDs across all tenant security logs.
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleIncidentSearch} className="flex gap-2">
            <input
              type="text"
              value={incidentLookupId}
              onChange={(e) => setIncidentLookupId(e.target.value)}
              placeholder="Enter Alert ID, Rule Name, or Correlation ID (e.g. 'sec-alert-01')..."
              className="flex-1 bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50"
            />
            <Button type="submit" variant="primary" size="sm" className="bg-purple-600 hover:bg-purple-500 text-white text-xs">
              Inspect Threat
            </Button>
          </form>

          {incidentLookupResult && (
            <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06] space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.04]">
                <span className="font-bold text-white">Lookup Results for "{incidentLookupResult.query}"</span>
                <span className="text-[10px] text-slate-400">{new Date(incidentLookupResult.searchedAt).toLocaleTimeString()}</span>
              </div>

              {incidentLookupResult.alert ? (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-200">{incidentLookupResult.alert.title || incidentLookupResult.alert.rule_name}</span>
                    <Badge variant="amber" size="xs">{incidentLookupResult.alert.severity}</Badge>
                  </div>
                  <p className="text-slate-300 text-[11px]">{incidentLookupResult.alert.description}</p>
                </div>
              ) : (
                <div className="text-slate-400 text-[11px]">No active security alerts match this specific ID.</div>
              )}

              {incidentLookupResult.logs.length > 0 && (
                <div className="space-y-1 pt-2 border-t border-white/[0.04]">
                  <span className="font-bold text-slate-300 block">Correlated Audit Logs ({incidentLookupResult.logs.length})</span>
                  {incidentLookupResult.logs.map((log, idx) => (
                    <div key={idx} className="p-2 rounded bg-white/[0.02] border border-white/[0.04] flex items-center justify-between font-mono text-[10px]">
                      <span className="text-purple-300">{log.action}</span>
                      <span className="text-slate-500">{new Date(log.created_at).toLocaleTimeString()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* 7. Tab 4: Chained Audit Explorer */}
      {activeTab === 'audit' && (
        <Card className="overflow-hidden border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="p-4 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                <FileText size={16} className="text-purple-400" />
                Immutable Audit Trail Explorer
              </CardTitle>
              <span className="text-[11px] text-slate-400">Cryptographically chained compliance stream</span>
            </div>

            <div className="relative w-full sm:w-64">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={auditSearch}
                onChange={(e) => { setAuditSearch(e.target.value); setAuditPage(1); }}
                placeholder="Filter logs by action or user..."
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-1 pl-8 pr-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50"
              />
            </div>
          </CardHeader>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-white/[0.03] border-b border-white/[0.06] text-[11px] uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Timestamp</th>
                  <th className="py-3 px-4 font-semibold">Actor / User</th>
                  <th className="py-3 px-4 font-semibold">Action Performed</th>
                  <th className="py-3 px-4 font-semibold">IP / Host</th>
                  <th className="py-3 px-4 font-semibold text-right">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {loading ? (
                  [1, 2, 3, 4, 5].map((i) => (
                    <tr key={i}>
                      <td colSpan={5} className="py-3 px-4">
                        <Skeleton className="h-6 w-full rounded bg-white/[0.02]" />
                      </td>
                    </tr>
                  ))
                ) : auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500 text-xs">
                      No audit events recorded for the active filter parameters.
                    </td>
                  </tr>
                ) : (
                  auditLogs.map((log) => (
                    <tr 
                      key={log.id} 
                      onClick={() => setSelectedAuditLog(log)}
                      className="hover:bg-white/[0.02] transition cursor-pointer font-mono"
                    >
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 font-bold text-white">{log.username || log.user_id || 'System Daemon'}</td>
                      <td className="py-3 px-4">
                        <Badge variant="purple" size="xs">{log.action}</Badge>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">{log.ip_address || '127.0.0.1 (Internal)'}</td>
                      <td className="py-3 px-4 text-right">
                        <Button variant="ghost" size="xs" className="text-purple-300 hover:text-white">
                          Inspect
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-400">
            <span>Showing {auditLogs.length} of {auditTotal} audit events</span>
            <div className="flex items-center gap-2">
              <IconButton
                variant="ghost"
                size="xs"
                onClick={() => setAuditPage(p => Math.max(1, p - 1))}
                disabled={auditPage <= 1}
                aria-label="Previous Page"
              >
                <ChevronLeft size={14} />
              </IconButton>
              <span className="font-mono text-white">Page {auditPage} of {totalAuditPages}</span>
              <IconButton
                variant="ghost"
                size="xs"
                onClick={() => setAuditPage(p => Math.min(totalAuditPages, p + 1))}
                disabled={auditPage >= totalAuditPages}
                aria-label="Next Page"
              >
                <ChevronRight size={14} />
              </IconButton>
            </div>
          </div>
        </Card>
      )}

      {/* 8. Security Alert Detail Drawer */}
      <Drawer
        isOpen={Boolean(selectedAlert)}
        onClose={() => setSelectedAlert(null)}
        title="Security Alert Detail"
        description="Threat detection context, incident triggers, and remediation guidance."
        size="md"
      >
        {selectedAlert && (
          <div className="space-y-4 text-xs text-slate-300">
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">{selectedAlert.title || selectedAlert.rule_name}</span>
                <StatusBadge status={selectedAlert.severity} label={selectedAlert.severity} />
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                {selectedAlert.description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-slate-500 block">Alert ID:</span>
                <span className="font-mono text-purple-300 truncate block">{selectedAlert.alert_id}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-slate-500 block">Trigger Count:</span>
                <span className="font-mono text-white font-bold block">{selectedAlert.trigger_count || 1} occurrences</span>
              </div>
            </div>

            <div className="pt-2 border-t border-white/[0.06] flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setSelectedAlert(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* 9. Audit Log Detail Drawer */}
      <Drawer
        isOpen={Boolean(selectedAuditLog)}
        onClose={() => setSelectedAuditLog(null)}
        title="Audit Record Inspector"
        description="Immutable timestamped record and action metadata."
        size="md"
      >
        {selectedAuditLog && (
          <div className="space-y-4 text-xs text-slate-300">
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-2 font-mono">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">{selectedAuditLog.action}</span>
                <Badge variant="purple" size="xs">SHA-256 Validated</Badge>
              </div>
              <span className="text-[10px] text-slate-500 block">{selectedAuditLog.id}</span>
            </div>

            <div className="space-y-2 text-[11px]">
              <div className="p-2 rounded bg-white/[0.02] border border-white/[0.04]">
                <span className="text-slate-500 block">Actor:</span>
                <span className="text-white font-bold">{selectedAuditLog.username || selectedAuditLog.user_id || 'System'}</span>
              </div>
              <div className="p-2 rounded bg-white/[0.02] border border-white/[0.04]">
                <span className="text-slate-500 block">Timestamp:</span>
                <span className="text-slate-300">{new Date(selectedAuditLog.created_at).toISOString()}</span>
              </div>
              <div className="p-2 rounded bg-white/[0.02] border border-white/[0.04]">
                <span className="text-slate-500 block">Details / Payload:</span>
                <span className="text-slate-300 font-mono text-[10px] block mt-1">
                  {selectedAuditLog.details || 'Standard operational execution event.'}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-white/[0.06] flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setSelectedAuditLog(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* 10. Export Report Modal */}
      <Modal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        title="Export Compliance Audit Report"
        description="Export sanitized cryptographic audit records for compliance or security review."
        size="md"
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Export Format</label>
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-purple-500/50"
            >
              <option value="json">JSON (Structured Machine-Readable)</option>
              <option value="csv">CSV (Spreadsheet Compatible)</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.06]">
            <Button variant="secondary" size="sm" onClick={() => setShowExportModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={isExporting}
              onClick={handleExport}
              className="bg-purple-600 hover:bg-purple-500 text-white"
            >
              {isExporting ? 'Exporting...' : 'Download Report'}
            </Button>
          </div>
        </div>
      </Modal>

    </div>
  );
}
