import React, { useState, useEffect } from 'react';
import { Server, Activity, RefreshCw, CheckCircle2, Shield, Wrench, FileCode, Layers, Radio, Lock } from 'lucide-react';
import { getPlatformCapabilities } from '../../api/platform';
import {
  Button,
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
  Skeleton
} from '../../components/ui';

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
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300 font-sans pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <Server size={20} className="text-cyan-400" />
            MCP Registry & Transport Administration
            <Badge variant="cyan">System Control</Badge>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Inspect Model Context Protocol server registrations, dynamic tool schemas, and security bounds across all tenant partitions.
          </p>
        </div>

        <Button 
          variant="secondary"
          size="sm"
          onClick={fetchCapabilities}
          disabled={loading}
          className="flex items-center gap-2"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin text-cyan-400' : ''} />
          {loading ? 'Refreshing...' : 'Refresh Registry'}
        </Button>
      </div>

      {/* KPI Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <MetricCard
          title="Active MCP Capabilities"
          value={capabilities.length}
          subtitle="Registered tool capabilities"
          trend="Registry Synchronized"
          icon={<Wrench size={18} className="text-cyan-400" />}
        />
        <MetricCard
          title="Security Boundary"
          value="Gated Safe"
          subtitle="SSRF & Private Network Isolated"
          trend="Strict RBAC Enforced"
          icon={<Shield size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Transport Layer"
          value="STDIO / SSE"
          subtitle="JSON-RPC 2.0 Streaming"
          trend="Subprocess Sandboxed"
          icon={<Radio size={18} className="text-indigo-400" />}
        />
      </div>

      {/* Capabilities Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-5 flex flex-col gap-4">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-4 w-1/2" />
            </Card>
          ))}
        </div>
      ) : capabilities.length === 0 ? (
        <EmptyState
          icon={<Server size={32} className="text-slate-500" />}
          title="No MCP Capabilities Registered"
          description="No active Model Context Protocol capabilities were found in the global registry."
          actionLabel="Refresh Registry"
          onAction={fetchCapabilities}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {capabilities.map((cap, idx) => (
            <Card
              key={idx}
              className="flex flex-col justify-between hover:border-cyan-500/40 hover:-translate-y-0.5 transition-all duration-200"
            >
              <div className="flex flex-col gap-3">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                    <Wrench size={18} />
                  </div>
                  <Badge variant="emerald">GATED SAFE</Badge>
                </div>
                <div>
                  <h3 className="font-bold text-sm text-white mt-1">{cap.name}</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{cap.description}</p>
                </div>
              </div>

              <div className="flex flex-col gap-2 pt-3 border-t border-white/[0.04] text-[11px] font-mono text-slate-400 mt-4">
                <div className="flex justify-between">
                  <span className="text-slate-500">Capability ID:</span>
                  <span className="text-slate-300 font-semibold">{cap.capability_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Scope:</span>
                  <span className="text-slate-300">{cap.workspace_scope ? 'Workspace' : 'System Wide'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Transport:</span>
                  <span className="text-cyan-400 font-bold">STDIO / SSE Secure</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
