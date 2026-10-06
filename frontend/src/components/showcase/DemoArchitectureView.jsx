import React from 'react';
import {
  User,
  Bot,
  BrainCircuit,
  Database,
  Server,
  Workflow,
  ShieldAlert,
  ShieldCheck,
  FileText,
  GitBranch,
  Layers,
  ArrowDown,
  Sparkles,
  Info
} from 'lucide-react';

export function DemoArchitectureView() {
  return (
    <div className="flex flex-col gap-6">
      {/* Legend Header */}
      <div className="p-4 rounded-xl border border-white/10 bg-[#0d1017] flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Layers size={18} className="text-cyan-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100">
            AegisAI Enterprise System Architecture
          </h3>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-cyan-500/20 border border-cyan-500" />
            <span className="text-slate-300">Real Platform Component</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-amber-500/20 border border-amber-500" />
            <span className="text-slate-300">Simulated Demo Event</span>
          </div>
        </div>
      </div>

      {/* Architecture Flow Canvas */}
      <div className="p-6 rounded-xl border border-white/10 bg-[#0a0d14] flex flex-col items-center gap-6 select-none">
        
        {/* Level 1: User & Interface */}
        <div className="w-full max-w-xl flex flex-col items-center gap-2">
          <div className="p-3.5 w-full rounded-xl border border-cyan-500/40 bg-cyan-500/10 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <User size={18} className="text-cyan-400" />
              <div>
                <h4 className="text-xs font-bold text-white uppercase">User Interface & AI OS Console</h4>
                <p className="text-[11px] text-slate-400">Natural language intent input & structured payload ingestion</p>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold">REAL CORE</span>
          </div>
          <ArrowDown size={16} className="text-cyan-400 animate-bounce" />
        </div>

        {/* Level 2: Orchestration & 9-Agent Collective Swarm */}
        <div className="w-full max-w-3xl flex flex-col items-center gap-2">
          <div className="p-4 w-full rounded-xl border border-purple-500/40 bg-purple-500/10 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BrainCircuit size={18} className="text-purple-400" />
                <h4 className="text-xs font-bold text-white uppercase">Multi-Agent Collective Swarm (9 Canonical Nodes)</h4>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold">DAG ORCHESTRATION</span>
            </div>

            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 text-center text-[11px] font-mono">
              <div className="p-2 rounded bg-black/40 border border-white/10 text-cyan-300">Orchestrator</div>
              <div className="p-2 rounded bg-black/40 border border-white/10 text-indigo-300">Planner</div>
              <div className="p-2 rounded bg-black/40 border border-white/10 text-blue-300">Research RAG</div>
              <div className="p-2 rounded bg-black/40 border border-white/10 text-teal-300">Graph Reasoner</div>
              <div className="p-2 rounded bg-black/40 border border-white/10 text-emerald-300">Critic Verifier</div>
            </div>
          </div>
          <ArrowDown size={16} className="text-purple-400" />
        </div>

        {/* Level 3: Dual Foundation Pillars (Knowledge & Tools) */}
        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-4">
          
          {/* Left Pillar: Memory & Knowledge Intelligence */}
          <div className="p-4 rounded-xl border border-blue-500/40 bg-blue-500/10 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database size={16} className="text-blue-400" />
                <h4 className="text-xs font-bold text-white uppercase">Knowledge & Memory Tier</h4>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">PGVECTOR + GRAPH</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Dense vector embeddings (1536-dim cosine similarity), semantic chunking, and multi-hop Knowledge Graph relational triples.
            </p>
          </div>

          {/* Right Pillar: MCP Tools & Visual Workflows */}
          <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server size={16} className="text-emerald-400" />
                <h4 className="text-xs font-bold text-white uppercase">MCP Tools & Workflows Tier</h4>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">SANDBOXED ENGINE</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Standardized Model Context Protocol servers (SSE, HTTP, Stdio) coupled with @xyflow/react visual DAG execution.
            </p>
          </div>
        </div>

        <ArrowDown size={16} className="text-slate-400" />

        {/* Level 4: Enterprise Governance & Cryptographic Auditing */}
        <div className="w-full max-w-xl p-4 rounded-xl border border-rose-500/40 bg-rose-500/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck size={20} className="text-rose-400" />
            <div>
              <h4 className="text-xs font-bold text-white uppercase">Enterprise Governance & Zero-Trust Verification</h4>
              <p className="text-[11px] text-slate-400">RBAC Gating • Dual-Key Human Approval • SHA-256 Hash Chains</p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold">IMMUTABLE LEDGER</span>
        </div>

      </div>
    </div>
  );
}
