import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  BrainCircuit,
  Bot,
  Database,
  Server,
  Workflow,
  ShieldAlert,
  ShieldCheck,
  FileText,
  GitBranch,
  ArrowRight,
  CheckCircle2,
  Lock,
  Cpu,
  Layers,
  Activity,
  Terminal,
  Clock,
  Zap,
  Globe,
  Sun,
  Moon,
  Users,
  TrendingUp,
  Sparkles,
  ChevronRight,
  Check,
  Search,
  ExternalLink
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Button, StatusBadge, Badge, Card, CardHeader, CardTitle, CardContent } from '../components/ui';

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, role } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [activeTourStation, setActiveTourStation] = useState('agents');
  const [activePipelineStep, setActivePipelineStep] = useState(0);

  // Auto-advance pipeline step subtly if animations not reduced
  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const interval = setInterval(() => {
      setActivePipelineStep((prev) => (prev + 1) % 8);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleAccessTerminal = () => {
    if (isAuthenticated) {
      if (role === 'admin' || role === 'super admin') {
        navigate('/admin/dashboard');
      } else {
        navigate('/user/dashboard');
      }
    } else {
      navigate('/login');
    }
  };

  // 7 Structured Intelligence Tour Stations
  const tourStations = [
    {
      id: 'agents',
      title: '01 — Agent Orchestration',
      subtitle: 'Multi-Agent Collective Intelligence',
      icon: <Bot size={20} className="text-cyan-400" />,
      what: 'Coordinates specialized planner, researcher, executor, critic, and response agents in deterministic DAG workflows.',
      why: 'Breaks complex tasks into verified sub-goals, preventing hallucination through strict verification and consensus.',
      flow: ['User Request', 'Orchestrator', 'Task Planner', 'Specialized Agents', 'Verification Critic', 'Evidence & Response']
    },
    {
      id: 'memory',
      title: '02 — Long-Term Memory',
      subtitle: 'Episodic & Semantic Cognitive Vault',
      icon: <Database size={20} className="text-purple-400" />,
      what: 'Indexes conversational history, agent reflections, and entity profiles into semantic vector memories.',
      why: 'Enables persistent context across sessions while enforcing strict workspace-level tenant isolation.',
      flow: ['Interaction Stream', 'Importance Filter', 'Vector Embedding', 'Memory Vault', 'Semantic Retrieval', 'Execution Context']
    },
    {
      id: 'knowledge',
      title: '03 — Enterprise Knowledge & RAG',
      subtitle: 'Hybrid Vector & Graph Intelligence',
      icon: <FileText size={20} className="text-blue-400" />,
      what: 'Extracts documents, computes 1536-dim embeddings, and synthesizes multi-hop Knowledge Graph relationships.',
      why: 'Answers queries with exact citations, physical document reconciliation, and verifiable knowledge provenance.',
      flow: ['Document Ingestion', 'Semantic Chunking', 'Vector Indexing', 'Knowledge Graph Triples', 'Hybrid RAG Search', 'Attributed Evidence']
    },
    {
      id: 'mcp',
      title: '04 — Model Context Protocol (MCP)',
      subtitle: 'Extensible Sandboxed Tool Ecosystem',
      icon: <Server size={20} className="text-amber-400" />,
      what: 'Integrates external tools, databases, APIs, and cloud resources via standardized MCP client-server protocols.',
      why: 'Empowers agents to safely interact with production systems with human-in-the-loop approval gates.',
      flow: ['MCP Discovery', 'Capability Binding', 'Permission Evaluation', 'Sandbox Execution', 'Result Normalization', 'Audit Logging']
    },
    {
      id: 'workflows',
      title: '05 — Workflow Automation',
      subtitle: 'Visual DAG Execution Engine',
      icon: <Workflow size={20} className="text-indigo-400" />,
      what: 'Visual workflow canvas allowing declarative chaining of agents, conditions, loops, and human approvals.',
      why: 'Automates complex business operations deterministically with scheduled triggers and execution replay.',
      flow: ['Workflow Trigger', 'DAG Parser', 'Node Evaluation', 'Approval Checkpoint', 'Worker Execution', 'Persisted Result']
    },
    {
      id: 'execution',
      title: '06 — Observable Execution',
      subtitle: 'Tamper-Evident Lifecycle Tracking',
      icon: <Activity size={20} className="text-emerald-400" />,
      what: 'Tracks every background job and execution through structured JSON events and cryptographic hash chains.',
      why: 'Provides real-time visibility and post-mortem auditability with zero credential exposure.',
      flow: ['Requested', 'Validating', 'Planned', 'Executing', 'Verifying', 'Completed']
    },
    {
      id: 'governance',
      title: '07 — Governance & Security',
      subtitle: 'Enterprise-Grade Fail-Closed Controls',
      icon: <ShieldCheck size={20} className="text-rose-400" />,
      what: 'Enforces strict tenant boundaries, role-based access control (RBAC), recursive secret redaction, and SSRF defenses.',
      why: 'Guarantees enterprise data compliance and prevents unauthorized lateral access or prompt injection attacks.',
      flow: ['Identity Verification', 'RBAC Permission Gate', 'SSRF / Injection Filter', 'Secret Redaction', 'SHA-256 Hash Chain', 'Secure Delivery']
    }
  ];

  const activeStation = tourStations.find((s) => s.id === activeTourStation) || tourStations[0];

  // Pipeline Steps
  const pipelineSteps = [
    { label: 'INPUT', desc: 'Secure Prompt & Payload Ingestion' },
    { label: 'UNDERSTAND', desc: 'Intent & Entity Classification' },
    { label: 'RETRIEVE', desc: 'Hybrid RAG & Memory Lookup' },
    { label: 'REASON', desc: 'DAG Task Decomposition' },
    { label: 'ORCHESTRATE', desc: 'Multi-Agent Dispatching' },
    { label: 'EXECUTE', desc: 'Sandboxed MCP Tool Calls' },
    { label: 'VERIFY', desc: 'Critic & Consensus Evaluation' },
    { label: 'RESPOND', desc: 'Evidence-Backed Delivery' },
  ];

  return (
    <div className="min-h-screen bg-[#07080a] text-slate-100 font-sans selection:bg-cyan-500/30 selection:text-white">
      
      {/* ==============================================================================
       * 1. Public Top Navigation
       * ============================================================================== */}
      <header className="sticky top-0 z-50 h-16 border-b border-white/[0.08] bg-[#07080a]/90 backdrop-blur-md px-6 md:px-12 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-400 to-indigo-500 flex items-center justify-center shadow-md shadow-cyan-500/10 shrink-0">
            <BrainCircuit size={18} className="text-black font-bold" />
          </div>
          <span className="font-bold text-base tracking-wider bg-gradient-to-r from-cyan-400 via-purple-300 to-indigo-400 bg-clip-text text-transparent">
            AEGISAI
          </span>
        </div>

        {/* Desktop Anchor Navigation */}
        <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-400">
          <a href="#platform" className="hover:text-cyan-400 transition-colors">Platform</a>
          <a href="#tour" className="hover:text-cyan-400 transition-colors">Intelligence Factory</a>
          <a href="#architecture" className="hover:text-cyan-400 transition-colors">Architecture</a>
          <a href="#security" className="hover:text-cyan-400 transition-colors">Security</a>
          <a href="#use-cases" className="hover:text-cyan-400 transition-colors">Use Cases</a>
        </nav>

        {/* CTA Buttons */}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/showcase')}
            leftIcon={<Sparkles size={13} className="text-cyan-400" />}
            className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10"
          >
            Showcase Mode
          </Button>

          <button
            onClick={toggleTheme}
            aria-label="Toggle theme mode"
            className="p-2 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 text-slate-400 hover:text-white transition-all cursor-pointer"
          >
            {theme === 'dark' ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-cyan-400" />}
          </button>

          {!isAuthenticated ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                Sign In
              </Button>
              <Button variant="primary" size="sm" onClick={handleAccessTerminal} rightIcon={<ArrowRight size={14} />}>
                Enter AegisAI
              </Button>
            </>
          ) : (
            <Button variant="primary" size="sm" onClick={handleAccessTerminal} rightIcon={<ArrowRight size={14} />}>
              Open Workspace
            </Button>
          )}
        </div>
      </header>

      {/* ==============================================================================
       * 2. Hero Section
       * ============================================================================== */}
      <section className="relative pt-20 pb-24 px-6 md:px-12 max-w-7xl mx-auto flex flex-col items-center text-center">
        {/* Subtle decorative glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-cyan-500/5 blur-[120px] rounded-full pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs font-mono font-medium mb-6 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span>ENTERPRISE AI OPERATING SYSTEM</span>
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white max-w-4xl leading-[1.15]">
          Autonomous Intelligence for the <span className="gradient-text">Enterprise</span>
        </h1>

        <p className="text-sm sm:text-base text-slate-400 max-w-2xl mt-6 leading-relaxed">
          Orchestrate multi-agent collectives, long-term episodic memory, enterprise knowledge graphs, and extensible MCP tools through one secure, verifiable operating system.
        </p>

        {/* Primary CTAs */}
        <div className="flex flex-wrap items-center justify-center gap-4 mt-10">
          <Button variant="primary" size="lg" onClick={handleAccessTerminal} rightIcon={<ArrowRight size={16} />}>
            Enter the Intelligence Factory
          </Button>
          <Button
            variant="secondary"
            size="lg"
            onClick={() => navigate('/showcase')}
            leftIcon={<Sparkles size={16} className="text-cyan-400" />}
          >
            Launch Interactive Showcase
          </Button>
        </div>

        {/* Factory Visual Blueprint Mock */}
        <div className="w-full max-w-5xl mt-16 p-4 rounded-2xl border border-white/10 bg-[#0d1017]/80 backdrop-blur-xl shadow-2xl relative overflow-hidden">
          <div className="px-4 py-2 border-b border-white/10 flex items-center justify-between text-xs text-slate-400 font-mono">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
              <span className="ml-2 text-slate-300 font-semibold">AEGIS_OS_CORE :: INTELLIGENCE_FACTORY</span>
            </div>
            <div className="flex items-center gap-4">
              <span>STATUS: ONLINE</span>
              <span className="text-cyan-400">LATENCY: 12ms</span>
            </div>
          </div>

          <div className="p-6 md:p-10 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02]">
              <div className="flex items-center gap-2 text-cyan-400 mb-2">
                <Bot size={18} />
                <h4 className="text-xs font-bold uppercase tracking-wider">Multi-Agent Swarm</h4>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Planner, Critic, and Execution nodes collaborate with deterministic DAG scheduling.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02]">
              <div className="flex items-center gap-2 text-purple-400 mb-2">
                <Database size={18} />
                <h4 className="text-xs font-bold uppercase tracking-wider">Cognitive Memory Vault</h4>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Episodic and semantic recall with strict multi-tenant workspace isolation.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02]">
              <div className="flex items-center gap-2 text-emerald-400 mb-2">
                <Server size={18} />
                <h4 className="text-xs font-bold uppercase tracking-wider">MCP Tool Ecosystem</h4>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Standardized Model Context Protocol servers for sandboxed external operations.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ==============================================================================
       * 3. Product Capability Strip
       * ============================================================================== */}
      <section id="platform" className="border-y border-white/[0.08] bg-[#090b10] py-6 px-6 md:px-12 overflow-x-auto select-none">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-8 min-w-[800px] text-xs font-mono font-medium text-slate-400">
          <div className="flex items-center gap-2 text-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            <span>MULTI-AGENT ORCHESTRATION</span>
          </div>
          <div className="flex items-center gap-2 text-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
            <span>LONG-TERM MEMORY</span>
          </div>
          <div className="flex items-center gap-2 text-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            <span>ENTERPRISE RAG</span>
          </div>
          <div className="flex items-center gap-2 text-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
            <span>KNOWLEDGE GRAPH</span>
          </div>
          <div className="flex items-center gap-2 text-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>MCP ECOSYSTEM</span>
          </div>
          <div className="flex items-center gap-2 text-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            <span>VERIFIABLE SECURITY</span>
          </div>
        </div>
      </section>

      {/* ==============================================================================
       * 4. Central Factory Pipeline Visual
       * ============================================================================== */}
      <section className="py-20 px-6 md:px-12 max-w-7xl mx-auto text-center">
        <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold block mb-2">
          Assembly Line Architecture
        </span>
        <h2 className="text-3xl font-bold text-white tracking-tight">The Intelligence Factory Pipeline</h2>
        <p className="text-xs text-slate-400 max-w-xl mx-auto mt-2 leading-relaxed">
          Every request traverses a verified, multi-stage intelligence assembly line ensuring accuracy, safety, and evidence provenance.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 mt-12">
          {pipelineSteps.map((step, idx) => {
            const isCurrent = activePipelineStep === idx;
            return (
              <div
                key={step.label}
                onClick={() => setActivePipelineStep(idx)}
                className={`p-3.5 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col items-center justify-center text-center ${
                  isCurrent
                    ? 'border-cyan-400/50 bg-cyan-500/10 shadow-lg shadow-cyan-500/10 scale-105'
                    : 'border-white/[0.08] bg-[#0d1017]/60 hover:border-white/20'
                }`}
              >
                <span className="text-[10px] font-mono text-slate-500">0{idx + 1}</span>
                <span className={`text-xs font-bold font-mono mt-1 ${isCurrent ? 'text-cyan-300' : 'text-slate-200'}`}>
                  {step.label}
                </span>
                <span className="text-[10px] text-slate-400 mt-1 leading-tight line-clamp-2">
                  {step.desc}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* ==============================================================================
       * 5. Interactive Intelligence Tour (7 Stations)
       * ============================================================================== */}
      <section id="tour" className="py-20 px-6 md:px-12 border-t border-white/[0.08] bg-[#080a0f]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <span className="text-xs font-mono text-purple-400 uppercase tracking-widest font-semibold block mb-2">
              Interactive Factory Tour
            </span>
            <h2 className="text-3xl font-bold text-white tracking-tight">Inspect Platform Stations</h2>
            <p className="text-xs text-slate-400 max-w-lg mx-auto mt-2 leading-relaxed">
              Explore how AegisAI transforms raw enterprise data into verifiable, autonomous intelligence.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Station Selector Sidebar */}
            <div className="lg:col-span-4 flex flex-col gap-2">
              {tourStations.map((station) => {
                const isActive = activeTourStation === station.id;
                return (
                  <button
                    key={station.id}
                    onClick={() => setActiveTourStation(station.id)}
                    className={`flex items-center justify-between p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      isActive
                        ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300 shadow-md'
                        : 'border-white/[0.06] bg-[#0d1017]/40 text-slate-400 hover:border-white/15 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="shrink-0">{station.icon}</div>
                      <div>
                        <span className="text-xs font-bold block text-slate-100">{station.title}</span>
                        <span className="text-[11px] text-slate-400">{station.subtitle}</span>
                      </div>
                    </div>
                    {isActive && <ChevronRight size={16} className="text-cyan-400 shrink-0" />}
                  </button>
                );
              })}
            </div>

            {/* Station Deep Dive Panel */}
            <div className="lg:col-span-8 rounded-2xl border border-white/10 bg-[#0d1017] p-6 md:p-8 flex flex-col justify-between min-h-[420px]">
              <div>
                <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-white/5 border border-white/10">{activeStation.icon}</div>
                    <div>
                      <h3 className="text-lg font-bold text-white">{activeStation.title}</h3>
                      <span className="text-xs text-cyan-400 font-mono">{activeStation.subtitle}</span>
                    </div>
                  </div>
                  <StatusBadge status="ACTIVE" size="xs" />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                    <span className="text-[10px] font-mono uppercase text-slate-500 font-bold block mb-1">
                      WHAT IT DOES
                    </span>
                    <p className="text-xs text-slate-300 leading-relaxed">{activeStation.what}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                    <span className="text-[10px] font-mono uppercase text-slate-500 font-bold block mb-1">
                      WHY IT MATTERS
                    </span>
                    <p className="text-xs text-slate-300 leading-relaxed">{activeStation.why}</p>
                  </div>
                </div>

                {/* Conceptual Architecture Flow */}
                <div className="mt-8 border-t border-white/10 pt-6">
                  <span className="text-[10px] font-mono uppercase text-slate-500 font-bold block mb-3">
                    EXECUTION FLOW SEQUENCE
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    {activeStation.flow.map((step, idx) => (
                      <React.Fragment key={step}>
                        <span className="px-2.5 py-1 rounded bg-white/5 border border-white/10 text-xs font-mono text-slate-200">
                          {step}
                        </span>
                        {idx < activeStation.flow.length - 1 && (
                          <ChevronRight size={14} className="text-slate-600 shrink-0" />
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
                <span>Verified locally under Phase 12.1 design governance.</span>
                <Button variant="ghost" size="xs" onClick={handleAccessTerminal} rightIcon={<ArrowRight size={12} />}>
                  Try in Workspace
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ==============================================================================
       * 6. High-Level Architecture Section
       * ============================================================================== */}
      <section id="architecture" className="py-20 px-6 md:px-12 max-w-7xl mx-auto text-center">
        <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold block mb-2">
          System Architecture
        </span>
        <h2 className="text-3xl font-bold text-white tracking-tight">Engineered for Enterprise Scale</h2>
        <p className="text-xs text-slate-400 max-w-xl mx-auto mt-2 leading-relaxed">
          Multi-tier architecture partitioning stateless API clusters from persistent storage and sandboxed worker pools.
        </p>

        <div className="mt-12 p-8 rounded-2xl border border-white/10 bg-[#0d1017]/80 text-left font-mono text-xs">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-500/5">
              <span className="text-[10px] text-cyan-400 font-bold block mb-1">01. INGRESS TIER</span>
              <h5 className="font-bold text-slate-100">Reverse Proxy</h5>
              <p className="text-[11px] text-slate-400 mt-2">Nginx TLS 1.2/1.3 with HSTS, trusted proxies, and rate limiting.</p>
            </div>

            <div className="p-4 rounded-xl border border-purple-500/20 bg-purple-500/5">
              <span className="text-[10px] text-purple-400 font-bold block mb-1">02. COMPUTE TIER</span>
              <h5 className="font-bold text-slate-100">Stateless Cluster</h5>
              <p className="text-[11px] text-slate-400 mt-2">FastAPI backend replicas & Vite SPA frontend running as non-root UID 10001.</p>
            </div>

            <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
              <span className="text-[10px] text-emerald-400 font-bold block mb-1">03. DATA TIER</span>
              <h5 className="font-bold text-slate-100">Durable Persistence</h5>
              <p className="text-[11px] text-slate-400 mt-2">PostgreSQL 16 with advisory locking, Qdrant vectors, and Redis 7.2.</p>
            </div>

            <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
              <span className="text-[10px] text-amber-400 font-bold block mb-1">04. ASYNC TIER</span>
              <h5 className="font-bold text-slate-100">Worker & Scheduler</h5>
              <p className="text-[11px] text-slate-400 mt-2">BackgroundJob queue with leader election, stale recovery, and dead-lettering.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ==============================================================================
       * 7. Enterprise Security Controls Section
       * ============================================================================== */}
      <section id="security" className="py-20 px-6 md:px-12 border-t border-white/[0.08] bg-[#080a0f]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <span className="text-xs font-mono text-rose-400 uppercase tracking-widest font-semibold block mb-2">
              Security & Compliance
            </span>
            <h2 className="text-3xl font-bold text-white tracking-tight">Designed with Enterprise Security Controls</h2>
            <p className="text-xs text-slate-400 max-w-lg mx-auto mt-2 leading-relaxed">
              Fail-closed security controls embedded into every API boundary, agent invocation, and database transaction.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-xl border border-white/10 bg-[#0d1017]">
              <Lock size={20} className="text-cyan-400 mb-3" />
              <h4 className="text-sm font-bold text-white">Strict Tenant Isolation</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Mandatory workspace boundary filtering on every query. Cross-tenant leakage is blocked at the database engine level.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-white/10 bg-[#0d1017]">
              <ShieldAlert size={20} className="text-purple-400 mb-3" />
              <h4 className="text-sm font-bold text-white">Tamper-Evident Audit Trails</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Every security event and administrative action is sealed into a SHA-256 cryptographic hash chain starting from Genesis.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-white/10 bg-[#0d1017]">
              <Zap size={20} className="text-amber-400 mb-3" />
              <h4 className="text-sm font-bold text-white">SSRF & Injection Defenses</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Outbound network filters block private CIDR traversal. Multi-layer classifiers detect and quarantine prompt injection attempts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ==============================================================================
       * 8. Enterprise Use-Cases Section
       * ============================================================================== */}
      <section id="use-cases" className="py-20 px-6 md:px-12 max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-mono text-emerald-400 uppercase tracking-widest font-semibold block mb-2">
            Operational Capabilities
          </span>
          <h2 className="text-3xl font-bold text-white tracking-tight">Enterprise Value Solutions</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6">
            <CardHeader className="p-0 border-none mb-3">
              <CardTitle>Research & Synthesis</CardTitle>
            </CardHeader>
            <CardContent className="p-0 text-xs text-slate-400 leading-relaxed">
              Coordinate research agents to ingest enterprise documents, crawl technical APIs, and produce verified reports with exact citations.
            </CardContent>
          </Card>

          <Card className="p-6">
            <CardHeader className="p-0 border-none mb-3">
              <CardTitle>Workflow Automation</CardTitle>
            </CardHeader>
            <CardContent className="p-0 text-xs text-slate-400 leading-relaxed">
              Deploy repeatable multi-agent workflows with visual DAG routing, conditional branching, and human-in-the-loop approvals.
            </CardContent>
          </Card>

          <Card className="p-6">
            <CardHeader className="p-0 border-none mb-3">
              <CardTitle>Unified Governance</CardTitle>
            </CardHeader>
            <CardContent className="p-0 text-xs text-slate-400 leading-relaxed">
              Manage teams, workspaces, MCP tool access policies, and audit trails through a centralized administrative dashboard.
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ==============================================================================
       * 9. Access Terminal CTA
       * ============================================================================== */}
      <section className="py-20 px-6 md:px-12 border-t border-white/[0.08] bg-gradient-to-b from-[#080a0f] to-[#06070a] text-center">
        <div className="max-w-3xl mx-auto p-10 rounded-2xl border border-cyan-500/30 bg-[#0d1017]/90 shadow-2xl relative overflow-hidden">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mx-auto mb-4">
            <BrainCircuit size={24} />
          </div>

          <h3 className="text-2xl font-bold text-white tracking-tight">Enter the AegisAI Operating System</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-2 leading-relaxed">
            Your intelligence infrastructure is ready. Launch autonomous workflows and explore the memory vault.
          </p>

          <div className="flex items-center justify-center gap-4 mt-8">
            <Button variant="primary" size="lg" onClick={handleAccessTerminal} rightIcon={<ArrowRight size={16} />}>
              Launch Workspace
            </Button>
            {!isAuthenticated && (
              <Button variant="secondary" size="lg" onClick={() => navigate('/login')}>
                Sign In
              </Button>
            )}
          </div>
        </div>
      </section>

      {/* ==============================================================================
       * 10. Public Footer
       * ============================================================================== */}
      <footer className="py-12 px-6 md:px-12 border-t border-white/[0.08] bg-[#07080a] text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-400 to-indigo-500 flex items-center justify-center">
              <BrainCircuit size={14} className="text-black font-bold" />
            </div>
            <span className="font-bold text-slate-300">AegisAI Autonomous Intelligence Platform</span>
          </div>

          <div className="flex items-center gap-6">
            <a href="#platform" className="hover:text-slate-300 transition-colors">Platform</a>
            <a href="#architecture" className="hover:text-slate-300 transition-colors">Architecture</a>
            <a href="#security" className="hover:text-slate-300 transition-colors">Security</a>
            <a href="https://github.com/Krish1216-web/AegisAI" target="_blank" rel="noreferrer" className="hover:text-slate-300 transition-colors flex items-center gap-1">
              GitHub <ExternalLink size={12} />
            </a>
          </div>

          <span className="font-mono text-[11px]">
            © 2026 AegisAI Platform. All rights reserved.
          </span>
        </div>
      </footer>

    </div>
  );
}
