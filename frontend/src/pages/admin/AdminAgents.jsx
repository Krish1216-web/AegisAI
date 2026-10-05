import React, { useState, useEffect, useCallback } from 'react';
import { Bot, Sliders, Cpu, Activity, RefreshCw, CheckCircle2, Clock, Zap, ShieldCheck, Lock } from 'lucide-react';
import { getPlatformCapabilities } from '../../api/platform';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  StatusBadge,
  Badge,
  EmptyState,
  Skeleton,
  MetricCard
} from '../../components/ui';

export default function AdminAgents({ addLog }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState(null);

  const fetchAgents = useCallback(async () => {
    setError(null);
    try {
      const res = await getPlatformCapabilities('agent');
      setAgents(res.items || []);
    } catch (err) {
      console.error('Failed to load agent capabilities:', err);
      setError('Failed to load agent registry telemetry.');
    } finally {
      setLoading(false);
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchAgents();
  }, [fetchAgents]);

  const handleSync = () => {
    setIsSyncing(true);
    fetchAgents();
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-100 font-sans pb-10">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/[0.08] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
              <Sliders size={20} className="text-purple-400" />
              AI Agent Registry & Orchestration Telemetry
            </h1>
            <Badge variant="purple" size="sm">ADMIN REGISTRY</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">Audit cognitive agent nodes, execution state graphs, required permissions, and lifecycle health.</p>
        </div>

        <Button 
          variant="ghost"
          size="sm"
          onClick={handleSync}
          disabled={loading || isSyncing}
          isLoading={isSyncing}
          leftIcon={<RefreshCw size={12} className={isSyncing ? 'animate-spin' : ''} />}
        >
          REFRESH_REGISTRY
        </Button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between gap-3">
          <span>{error}</span>
          <Button variant="ghost" size="xs" onClick={fetchAgents}>Retry</Button>
        </div>
      )}

      {/* Agents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="border-white/[0.08] bg-[#0d1017]/80 p-5">
              <Skeleton className="h-6 w-3/4 mb-3" />
              <Skeleton className="h-12 w-full mb-4" />
              <Skeleton className="h-4 w-1/2" />
            </Card>
          ))
        ) : agents.length === 0 ? (
          <div className="col-span-full">
            <EmptyState
              icon={<Bot size={24} />}
              title="No agent capabilities registered"
              description="Platform agent subsystem has not registered dynamic custom agent capabilities."
              actionLabel="Refresh Telemetry"
              onAction={fetchAgents}
            />
          </div>
        ) : (
          agents.map((agent, idx) => (
            <Card key={idx} className="border-white/[0.08] bg-[#0d1017]/80 flex flex-col justify-between">
              <CardHeader className="border-b border-white/[0.06] pb-3.5">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                      <Bot size={18} />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-bold text-white">{agent.name}</CardTitle>
                      <span className="text-[10px] font-mono text-purple-400">{agent.capability_id}</span>
                    </div>
                  </div>
                  <StatusBadge status={agent.enabled ? 'ONLINE' : 'DISABLED'} size="xs" />
                </div>
              </CardHeader>

              <CardContent className="p-4 flex flex-col gap-3">
                <p className="text-xs text-slate-300 leading-relaxed">{agent.description}</p>

                <div className="flex flex-col gap-1.5 pt-3 border-t border-white/[0.04] text-[11px] font-mono text-slate-400">
                  <div className="flex justify-between">
                    <span>Version:</span>
                    <span className="text-slate-200">{agent.version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Permissions:</span>
                    <span className="text-purple-300 truncate max-w-[200px]">
                      {agent.required_permissions && agent.required_permissions.length > 0
                        ? agent.required_permissions.join(', ')
                        : 'Default Workspace'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

    </div>
  );
}
