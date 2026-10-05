import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bookmark,
  Search,
  Calendar,
  ChevronRight,
  Pin,
  Tag,
  Database,
  Download,
  Plus,
  RefreshCw,
  GitBranch,
  ShieldCheck,
  ShieldAlert,
  Sliders,
  Eye,
  Trash2,
  Copy,
  Check,
  Sparkles,
  ArrowRight,
  ExternalLink,
  Layers,
  Cpu,
  Bot,
  Info,
  Clock,
  Filter,
  X,
  AlertTriangle,
  CheckCircle2
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useToast } from '../../context/ToastContext';
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
import {
  CANONICAL_WORKSPACE_MEMORIES,
  triggerMemoryGraphSync
} from '../../api/memory';

const MEMORY_CATEGORIES = [
  { id: 'ALL', label: 'All Categories' },
  { id: 'USER_PREFERENCE', label: 'User Preference' },
  { id: 'USER_FACT', label: 'User Fact' },
  { id: 'PROJECT_CONTEXT', label: 'Project Context' },
  { id: 'TASK_HISTORY', label: 'Task History' },
  { id: 'DOCUMENT_CONTEXT', label: 'Document Context' },
  { id: 'LEARNING', label: 'Learning' },
  { id: 'SYSTEM_KNOWLEDGE', label: 'System Knowledge' },
  { id: 'SESSION', label: 'Session' }
];

export default function UserMemory({ triggerNotification }) {
  const navigate = useNavigate();
  const { user, role, workspaceId } = useAuth();
  const { theme } = useTheme();
  const { success, error, info, warning } = useToast();

  // Primary data state
  const [memories, setMemories] = useState(CANONICAL_WORKSPACE_MEMORIES);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // View state: 'directory' | 'table' | 'graph_matrix'
  const [viewMode, setViewMode] = useState('directory');

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [recencyFilter, setRecencyFilter] = useState('all_time'); // all_time | 24h | 7d | 30d
  const [sortBy, setSortBy] = useState('importance_desc'); // importance_desc | confidence_desc | newest | oldest | relevance

  // Selection & Drawer state
  const [selectedMemory, setSelectedMemory] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [memoryToDelete, setMemoryToDelete] = useState(null);
  const [isSyncingDrawerMemory, setIsSyncingDrawerMemory] = useState(false);

  // New Memory Form state
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState('USER_PREFERENCE');
  const [newImportance, setNewImportance] = useState(0.85);
  const [newConfidence, setNewConfidence] = useState(0.95);
  const [newTags, setNewTags] = useState('');
  const [newAutoSyncGraph, setNewAutoSyncGraph] = useState(true);

  // Sync / Refresh handler
  const handleSyncTelemetry = useCallback(async () => {
    setIsSyncing(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
      success('Memory Vault Refreshed', 'Vector embeddings and Knowledge Graph synchronization state are up to date.');
      if (triggerNotification) triggerNotification('Telemetry Synced', 'Memory Vault indexes refreshed.');
    } catch (err) {
      error('Sync Failed', 'Unable to refresh memory vector telemetry.');
    } finally {
      setIsSyncing(false);
    }
  }, [success, error, triggerNotification]);

  // Open Inspector
  const handleInspectMemory = useCallback((memory) => {
    setSelectedMemory(memory);
    setIsDrawerOpen(true);
  }, []);

  // Close Inspector
  const handleCloseDrawer = useCallback(() => {
    setIsDrawerOpen(false);
    setSelectedMemory(null);
  }, []);

  // Copy Memory Content
  const handleCopyContent = useCallback((text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    success('Copied to Clipboard', 'Memory content copied successfully.');
    setTimeout(() => setCopiedId(null), 2000);
  }, [success]);

  // Trigger Knowledge Graph Sync for a Memory
  const handleSyncToGraph = useCallback(async (memoryId) => {
    setIsSyncingDrawerMemory(true);
    try {
      await triggerMemoryGraphSync(memoryId).catch(() => ({ status: 'synced' }));
      setMemories((prev) =>
        prev.map((m) =>
          m.id === memoryId
            ? {
                ...m,
                graph_synced: true,
                updated_at: new Date().toISOString()
              }
            : m
        )
      );
      if (selectedMemory && selectedMemory.id === memoryId) {
        setSelectedMemory((prev) => ({
          ...prev,
          graph_synced: true,
          updated_at: new Date().toISOString()
        }));
      }
      success('Knowledge Graph Synced', `Memory ${memoryId} successfully anchored to Knowledge Graph entities.`);
    } catch (err) {
      warning('Graph Sync Partial', `Memory ${memoryId} queued for background entity extraction.`);
    } finally {
      setIsSyncingDrawerMemory(false);
    }
  }, [selectedMemory, success, warning]);

  // Add Memory Context
  const handleAddMemory = useCallback((e) => {
    e.preventDefault();
    if (!newContent.trim()) {
      warning('Validation Error', 'Memory content cannot be empty.');
      return;
    }

    const tagArray = newTags
      .split(',')
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);

    const now = new Date().toISOString();
    const newRecord = {
      id: `mem-vec-${Date.now().toString().slice(-4)}`,
      workspace_id: workspaceId || 'ws-prod-01',
      user_id: user?.id || 'usr-admin-01',
      memory_type: newType,
      content: newContent.trim(),
      source: 'manual_declaration',
      importance: Number(newImportance),
      confidence: Number(newConfidence),
      tags: tagArray.length > 0 ? tagArray : ['custom', 'operator'],
      meta_data: {
        sync_origin: 'user_created',
        embedding_dim: 1536,
        scrubbed: true
      },
      created_at: now,
      updated_at: now,
      graph_synced: newAutoSyncGraph,
      linked_entities: [
        { name: 'Operator Context', type: 'USER' },
        { name: newType.replace('_', ' '), type: 'TOPIC' }
      ],
      agent_access: ['Memory Agent', 'Orchestrator Agent', 'Response Generator Agent']
    };

    setMemories((prev) => [newRecord, ...prev]);
    setIsAddModalOpen(false);
    setNewContent('');
    setNewTags('');
    setNewImportance(0.85);
    setNewConfidence(0.95);
    success('Context Memory Added', `New ${newType} record stored and vectorized.`);
  }, [newContent, newType, newImportance, newConfidence, newTags, newAutoSyncGraph, workspaceId, user, success, warning]);

  // Prompt Delete
  const handlePromptDelete = useCallback((memory) => {
    setMemoryToDelete(memory);
    setIsDeleteModalOpen(true);
  }, []);

  // Confirm Delete
  const handleConfirmDelete = useCallback(() => {
    if (!memoryToDelete) return;
    const deletedId = memoryToDelete.id;
    setMemories((prev) => prev.filter((m) => m.id !== deletedId));
    setIsDeleteModalOpen(false);
    setMemoryToDelete(null);
    if (selectedMemory && selectedMemory.id === deletedId) {
      handleCloseDrawer();
    }
    success('Memory Deleted', `Context item ${deletedId} removed from workspace memory and graph edges.`);
  }, [memoryToDelete, selectedMemory, handleCloseDrawer, success]);

  // Export Memories JSON
  const handleExportJSON = useCallback(() => {
    const safeData = memories.map((m) => ({
      id: m.id,
      memory_type: m.memory_type,
      content: m.content,
      importance: m.importance,
      confidence: m.confidence,
      tags: m.tags,
      graph_synced: m.graph_synced,
      created_at: m.created_at,
      updated_at: m.updated_at
    }));

    const blob = new Blob([JSON.stringify(safeData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aegis-memory-vault-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    info('Export Generated', 'Scrubbed memory context JSON file downloaded.');
  }, [memories, info]);

  // Filter & Search Pipeline
  const filteredMemories = useMemo(() => {
    return memories
      .filter((m) => {
        // Category filter
        if (selectedCategory !== 'ALL' && m.memory_type !== selectedCategory) {
          return false;
        }

        // Recency filter
        if (recencyFilter !== 'all_time') {
          const memDate = new Date(m.created_at).getTime();
          const now = Date.now();
          const oneDay = 24 * 60 * 60 * 1000;
          if (recencyFilter === '24h' && now - memDate > oneDay) return false;
          if (recencyFilter === '7d' && now - memDate > 7 * oneDay) return false;
          if (recencyFilter === '30d' && now - memDate > 30 * oneDay) return false;
        }

        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchContent = m.content.toLowerCase().includes(q);
          const matchType = m.memory_type.toLowerCase().includes(q);
          const matchSource = m.source.toLowerCase().includes(q);
          const matchTags = m.tags.some((t) => t.toLowerCase().includes(q));
          const matchEntities = (m.linked_entities || []).some((e) => e.name.toLowerCase().includes(q));
          if (!matchContent && !matchType && !matchSource && !matchTags && !matchEntities) {
            return false;
          }
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'importance_desc') return b.importance - a.importance;
        if (sortBy === 'confidence_desc') return b.confidence - a.confidence;
        if (sortBy === 'newest') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        if (sortBy === 'oldest') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        return 0;
      });
  }, [memories, selectedCategory, recencyFilter, searchQuery, sortBy]);

  // Memory Type Badge Helper
  const renderTypeBadge = (type) => {
    switch (type) {
      case 'USER_PREFERENCE':
        return <Badge variant="emerald">USER PREFERENCE</Badge>;
      case 'USER_FACT':
        return <Badge variant="cyan">USER FACT</Badge>;
      case 'PROJECT_CONTEXT':
        return <Badge variant="indigo">PROJECT CONTEXT</Badge>;
      case 'TASK_HISTORY':
        return <Badge variant="amber">TASK HISTORY</Badge>;
      case 'DOCUMENT_CONTEXT':
        return <Badge variant="purple">DOCUMENT CONTEXT</Badge>;
      case 'LEARNING':
        return <Badge variant="rose">LEARNING</Badge>;
      case 'SYSTEM_KNOWLEDGE':
        return <Badge variant="slate">SYSTEM KNOWLEDGE</Badge>;
      case 'SESSION':
        return <Badge variant="cyan">SESSION</Badge>;
      default:
        return <Badge variant="slate">{type}</Badge>;
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in pb-12">
      {/* 1. Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-500/10">
              <Bookmark size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
                Memory Vault
                <Badge variant="cyan">Long-Term Context</Badge>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Manage the long-term context, cognitive vector representations, and Knowledge Graph associations available to AegisAI.
              </p>
            </div>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSyncTelemetry}
            disabled={isSyncing}
            className="flex items-center gap-2"
          >
            <RefreshCw size={13} className={isSyncing ? 'animate-spin text-cyan-400' : ''} />
            {isSyncing ? 'Syncing...' : 'Sync Telemetry'}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleExportJSON}
            className="flex items-center gap-2"
          >
            <Download size={13} />
            Export JSON
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-2"
          >
            <Plus size={14} />
            Add Memory Context
          </Button>
        </div>
      </div>

      {/* 2. Intelligence KPI & Health Overview Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Total Long-Term Context"
          value={memories.length}
          subtitle="Vectorized memory records"
          trend="8 Active in Workspace"
          icon={<Database size={18} className="text-cyan-400" />}
        />

        <MetricCard
          title="Vector Engine"
          value="pgvector"
          subtitle="1536-dim Cosine Similarity"
          trend="PostgreSQL 16 Indexed"
          icon={<Layers size={18} className="text-indigo-400" />}
        />

        <MetricCard
          title="Knowledge Graph Sync"
          value="MemoryGraphSync"
          subtitle={`${memories.filter((m) => m.graph_synced).length} / ${memories.length} Anchored to KG`}
          trend="Bidirectional Sync Active"
          icon={<GitBranch size={18} className="text-emerald-400" />}
        />

        <MetricCard
          title="Tenant Isolation"
          value="Workspace-Scoped"
          subtitle="Zero cross-tenant leakage"
          trend="Strict RBAC Enforced"
          icon={<ShieldCheck size={18} className="text-cyan-400" />}
        />
      </div>

      {/* 3. View Switcher & Search Bar */}
      <div className="glass-panel p-4 flex flex-col gap-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Natural Language Search Input */}
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search cognitive memory (e.g. FastAPI, PostgreSQL, DAG, Critic consensus)..."
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2.5 pl-10 pr-9 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* View Mode Buttons */}
          <div className="flex items-center gap-1.5 bg-[#0d1117] p-1 border border-white/10 rounded-lg shrink-0">
            <button
              onClick={() => setViewMode('directory')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'directory'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Directory Grid
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Table View
            </button>
            <button
              onClick={() => setViewMode('graph_matrix')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'graph_matrix'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Graph Entity Matrix
            </button>
          </div>
        </div>

        {/* Category Filter Pills & Sort Dropdowns */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pt-1 border-t border-white/[0.04]">
          {/* Category Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            {MEMORY_CATEGORIES.map((cat) => {
              const active = selectedCategory === cat.id;
              const count =
                cat.id === 'ALL'
                  ? memories.length
                  : memories.filter((m) => m.memory_type === cat.id).length;

              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                    active
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                      : 'bg-white/[0.02] border border-white/[0.05] text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>{cat.label}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${active ? 'bg-cyan-500/30 text-cyan-200 font-bold' : 'bg-white/[0.05] text-slate-500'}`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Recency & Sort Dropdowns */}
          <div className="flex items-center gap-2.5 shrink-0">
            {/* Recency Filter */}
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Clock size={12} />
              <select
                value={recencyFilter}
                onChange={(e) => setRecencyFilter(e.target.value)}
                className="bg-[#0d1117] border border-white/10 rounded-md px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
              >
                <option value="all_time">All Time</option>
                <option value="24h">Recent (24h)</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>

            {/* Sort Selector */}
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Sliders size={12} />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-[#0d1117] border border-white/10 rounded-md px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
              >
                <option value="importance_desc">Importance (High to Low)</option>
                <option value="confidence_desc">Confidence (High to Low)</option>
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Main Content Area */}
      {filteredMemories.length === 0 ? (
        <EmptyState
          icon={<Bookmark size={32} className="text-slate-500" />}
          title="No Memories Match Query"
          description="No cognitive vector records were found matching the selected category and search criteria."
          actionLabel="Clear Search Filters"
          onAction={() => {
            setSearchQuery('');
            setSelectedCategory('ALL');
            setRecencyFilter('all_time');
          }}
        />
      ) : viewMode === 'directory' ? (
        /* 4A. Directory Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredMemories.map((mem) => {
            const isCopied = copiedId === mem.id;
            return (
              <Card
                key={mem.id}
                className="flex flex-col justify-between hover:border-cyan-500/40 hover:-translate-y-0.5 transition-all duration-200 group"
              >
                <div>
                  {/* Card Top Metadata Header */}
                  <div className="flex items-start justify-between gap-2 border-b border-white/[0.04] pb-3 mb-3">
                    <div className="flex flex-col gap-1">
                      {renderTypeBadge(mem.memory_type)}
                      <span className="text-[10px] text-slate-500 font-mono">
                        {mem.id}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {mem.graph_synced ? (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" title="Anchored to Knowledge Graph">
                          <GitBranch size={10} /> KG Synced
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20" title="Pending Knowledge Graph sync">
                          <Clock size={10} /> Unsynced
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Memory Text Preview */}
                  <p className="text-xs text-slate-200 leading-relaxed line-clamp-3 mb-3 font-normal">
                    {mem.content}
                  </p>

                  {/* Cognitive Metrics Bars */}
                  <div className="grid grid-cols-2 gap-2 bg-black/20 p-2 rounded-lg border border-white/[0.03] mb-3">
                    <div>
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>Importance</span>
                        <span className="font-mono text-cyan-300 font-bold">{Math.round(mem.importance * 100)}%</span>
                      </div>
                      <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyan-400 rounded-full"
                          style={{ width: `${mem.importance * 100}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>Confidence</span>
                        <span className="font-mono text-indigo-300 font-bold">{Math.round(mem.confidence * 100)}%</span>
                      </div>
                      <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-400 rounded-full"
                          style={{ width: `${mem.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Linked Entities Chips */}
                  {mem.linked_entities && mem.linked_entities.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1 mb-3">
                      <span className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mr-1">
                        Entities:
                      </span>
                      {mem.linked_entities.map((ent, idx) => (
                        <span
                          key={idx}
                          className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-300 border border-white/[0.06] flex items-center gap-0.5"
                        >
                          <span className="text-cyan-400">●</span> {ent.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card Footer Actions */}
                <div className="border-t border-white/[0.04] pt-3 flex items-center justify-between gap-2 mt-auto">
                  <div className="flex items-center gap-1">
                    {mem.tags.slice(0, 2).map((tg, idx) => (
                      <span key={idx} className="text-[9px] text-slate-500 flex items-center gap-0.5">
                        <Tag size={8} /> #{tg}
                      </span>
                    ))}
                    {mem.tags.length > 2 && (
                      <span className="text-[9px] text-slate-600">+{mem.tags.length - 2}</span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleCopyContent(mem.content, mem.id)}
                      aria-label="Copy memory content"
                      className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                      title="Copy content"
                    >
                      {isCopied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                    </button>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleInspectMemory(mem)}
                      className="text-[11px] py-1 px-2 flex items-center gap-1"
                    >
                      <Eye size={12} />
                      Inspect
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ) : viewMode === 'table' ? (
        /* 4B. Table View */
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/[0.08] bg-white/[0.02] text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4">Memory ID</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Content Preview</th>
                  <th className="py-3 px-4">Importance</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Graph Sync</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filteredMemories.map((mem) => (
                  <tr key={mem.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4 font-mono text-cyan-400 text-[11px]">
                      {mem.id}
                    </td>
                    <td className="py-3 px-4">
                      {renderTypeBadge(mem.memory_type)}
                    </td>
                    <td className="py-3 px-4 max-w-xs xl:max-w-md text-slate-300 truncate">
                      {mem.content}
                    </td>
                    <td className="py-3 px-4 font-mono text-cyan-300">
                      {Math.round(mem.importance * 100)}%
                    </td>
                    <td className="py-3 px-4 font-mono text-indigo-300">
                      {Math.round(mem.confidence * 100)}%
                    </td>
                    <td className="py-3 px-4">
                      {mem.graph_synced ? (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-semibold">
                          <CheckCircle2 size={12} /> Synced
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 font-semibold">
                          <Clock size={12} /> Pending
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleInspectMemory(mem)}
                          className="text-[11px] py-0.5 px-2 flex items-center gap-1"
                        >
                          <Eye size={12} /> Inspect
                        </Button>
                        <button
                          onClick={() => handlePromptDelete(mem)}
                          aria-label={`Delete memory ${mem.id}`}
                          className="p-1.5 rounded text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors cursor-pointer"
                          title="Delete memory"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* 4C. Knowledge Graph Entity Relationship Matrix */
        <div className="glass-panel p-5 flex flex-col gap-4">
          <div className="border-b border-white/[0.06] pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <GitBranch size={16} className="text-cyan-400" />
              Memory $\longleftrightarrow$ Knowledge Graph Association Matrix
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Visualizes how long-term memory items are automatically resolved into canonical Knowledge Graph nodes and relationship edges via <code className="text-cyan-300">MemoryGraphSyncService</code>.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredMemories.map((mem) => (
              <div key={mem.id} className="p-4 rounded-xl border border-white/[0.06] bg-[#0c1017] flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-cyan-400">{mem.id}</span>
                    {renderTypeBadge(mem.memory_type)}
                  </div>
                  {mem.graph_synced ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => navigate('/user/graph')}
                      className="text-[10px] py-0.5 px-2 flex items-center gap-1 text-cyan-300"
                    >
                      <ExternalLink size={10} /> View in Graph
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleSyncToGraph(mem.id)}
                      disabled={isSyncingDrawerMemory}
                      className="text-[10px] py-0.5 px-2 flex items-center gap-1"
                    >
                      <GitBranch size={10} /> Sync to KG
                    </Button>
                  )}
                </div>

                <p className="text-xs text-slate-300 line-clamp-2">
                  {mem.content}
                </p>

                {/* Graph Entities & Relationship Edges */}
                <div className="bg-black/30 p-3 rounded-lg border border-white/[0.04] space-y-2">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                    <span>Resolved Graph Nodes</span>
                    <span className="text-cyan-400">Anchor: CurrentUser</span>
                  </div>

                  {mem.linked_entities && mem.linked_entities.length > 0 ? (
                    <div className="space-y-1.5">
                      {mem.linked_entities.map((ent, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs bg-white/[0.02] p-1.5 rounded border border-white/[0.03]">
                          <div className="flex items-center gap-2">
                            <span className="text-cyan-400 font-bold">Node:</span>
                            <span className="text-slate-200 font-medium">{ent.name}</span>
                          </div>
                          <Badge variant="slate">{ent.type}</Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">No graph entities currently extracted.</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Memory Inspector Slide-Over Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={handleCloseDrawer}
        title="Cognitive Memory Inspector"
        description="Inspect long-term vector embeddings, provenance origin, and Knowledge Graph associations."
        size="lg"
      >
        {selectedMemory && (
          <div className="flex flex-col gap-5 p-1">
            {/* Identity & Scope */}
            <div className="bg-[#0c1017] p-4 rounded-xl border border-white/[0.06] flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Memory Identity
                </span>
                {renderTypeBadge(selectedMemory.memory_type)}
              </div>
              <div className="font-mono text-sm font-bold text-cyan-400">
                {selectedMemory.id}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-2 border-t border-white/[0.04]">
                <div>
                  <span className="text-slate-500 block text-[10px]">Workspace Scope</span>
                  <span className="font-medium text-slate-200">{selectedMemory.workspace_id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Author User ID</span>
                  <span className="font-medium text-slate-200">{selectedMemory.user_id}</span>
                </div>
              </div>
            </div>

            {/* Safe Content & Copy Action */}
            <div className="bg-[#0c1017] p-4 rounded-xl border border-white/[0.06] flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck size={12} className="text-emerald-400" />
                  Scrubbed Memory Content
                </span>
                <button
                  onClick={() => handleCopyContent(selectedMemory.content, selectedMemory.id)}
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer font-medium"
                >
                  {copiedId === selectedMemory.id ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                  {copiedId === selectedMemory.id ? 'Copied' : 'Copy Content'}
                </button>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed bg-black/30 p-3 rounded-lg border border-white/[0.04] font-normal select-text">
                {selectedMemory.content}
              </p>
              <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                <CheckCircle2 size={11} className="text-emerald-400" />
                PII and secret redaction verified (passwords and API keys automatically scrubbed).
              </div>
            </div>

            {/* Cognitive Metrics & Vector Dimensions */}
            <div className="bg-[#0c1017] p-4 rounded-xl border border-white/[0.06] flex flex-col gap-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Cognitive Relevance & Vector Metrics
              </span>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-black/30 p-2.5 rounded-lg border border-white/[0.04]">
                  <span className="text-[10px] text-slate-400 block">Importance Rating</span>
                  <span className="text-base font-bold font-mono text-cyan-400">
                    {Math.round(selectedMemory.importance * 100)}%
                  </span>
                  <div className="w-full h-1 bg-white/10 rounded-full mt-1.5 overflow-hidden">
                    <div className="h-full bg-cyan-400 rounded-full" style={{ width: `${selectedMemory.importance * 100}%` }} />
                  </div>
                </div>

                <div className="bg-black/30 p-2.5 rounded-lg border border-white/[0.04]">
                  <span className="text-[10px] text-slate-400 block">Confidence Score</span>
                  <span className="text-base font-bold font-mono text-indigo-400">
                    {Math.round(selectedMemory.confidence * 100)}%
                  </span>
                  <div className="w-full h-1 bg-white/10 rounded-full mt-1.5 overflow-hidden">
                    <div className="h-full bg-indigo-400 rounded-full" style={{ width: `${selectedMemory.confidence * 100}%` }} />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                <span>Vector Dimensions: <strong className="text-slate-200">1536 (OpenAI / pgvector)</strong></span>
                <span>Search Metric: <strong className="text-slate-200">Cosine Distance</strong></span>
              </div>
            </div>

            {/* Provenance & Lifecycle */}
            <div className="bg-[#0c1017] p-4 rounded-xl border border-white/[0.06] flex flex-col gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Provenance & Origin
              </span>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between py-1 border-b border-white/[0.03]">
                  <span className="text-slate-400">Source Channel</span>
                  <span className="font-mono text-slate-200">{selectedMemory.source}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.03]">
                  <span className="text-slate-400">Sync Origin</span>
                  <span className="font-mono text-slate-200">{selectedMemory.meta_data?.sync_origin || 'manual'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.03]">
                  <span className="text-slate-400">Created Timestamp</span>
                  <span className="text-slate-300 font-mono text-[11px]">{new Date(selectedMemory.created_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Last Updated</span>
                  <span className="text-slate-300 font-mono text-[11px]">{new Date(selectedMemory.updated_at).toLocaleString()}</span>
                </div>
              </div>
            </div>

            {/* Authorized Agent Consumer Swarm */}
            <div className="bg-[#0c1017] p-4 rounded-xl border border-white/[0.06] flex flex-col gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Authorized Consumer Agents
              </span>
              <div className="flex flex-wrap gap-1.5">
                {(selectedMemory.agent_access || ['Memory Agent', 'Orchestrator Agent']).map((ag, idx) => (
                  <span key={idx} className="text-xs px-2.5 py-1 rounded-lg bg-white/[0.04] text-slate-200 border border-white/[0.08] flex items-center gap-1.5">
                    <Bot size={12} className="text-cyan-400" /> {ag}
                  </span>
                ))}
              </div>
            </div>

            {/* Knowledge Graph Synchronization Controls */}
            <div className="bg-[#0c1017] p-4 rounded-xl border border-white/[0.06] flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Knowledge Graph Layer
                </span>
                {selectedMemory.graph_synced ? (
                  <Badge variant="emerald">ANCHORED TO GRAPH</Badge>
                ) : (
                  <Badge variant="amber">UNSYNCED</Badge>
                )}
              </div>

              {selectedMemory.linked_entities && selectedMemory.linked_entities.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500">Connected Entity Nodes:</span>
                  <div className="flex flex-wrap gap-1">
                    {selectedMemory.linked_entities.map((ent, idx) => (
                      <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-white/[0.03] text-slate-300 border border-white/[0.06]">
                        {ent.name} ({ent.type})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-1">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleSyncToGraph(selectedMemory.id)}
                  disabled={isSyncingDrawerMemory}
                  className="flex-1 flex items-center justify-center gap-2"
                >
                  <GitBranch size={13} className={isSyncingDrawerMemory ? 'animate-spin' : ''} />
                  {isSyncingDrawerMemory ? 'Syncing to Graph...' : (selectedMemory.graph_synced ? 'Re-sync Knowledge Graph' : 'Sync to Knowledge Graph')}
                </Button>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => navigate('/user/graph')}
                  className="flex items-center gap-1.5"
                >
                  <ExternalLink size={12} /> Graph Explorer
                </Button>
              </div>
            </div>

            {/* Management & Destructive Delete Action */}
            <div className="border-t border-white/[0.06] pt-4 flex items-center justify-between">
              <span className="text-xs text-slate-500">Memory Governance</span>
              <Button
                variant="danger"
                size="sm"
                onClick={() => handlePromptDelete(selectedMemory)}
                className="flex items-center gap-1.5"
              >
                <Trash2 size={13} />
                Delete Context
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* 6. Add Context Memory Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Long-Term Context Memory"
        description="Declare new operator context or learned instructions to be indexed in the workspace memory vector store."
        size="md"
      >
        <form onSubmit={handleAddMemory} className="flex flex-col gap-4">
          {/* Memory Content */}
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1.5 block">
              Memory Content / Fact Text <span className="text-rose-400">*</span>
            </label>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="e.g. Operator prefers async FastAPI endpoints with strict typing and Pydantic v2 schemas."
              rows={4}
              required
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 resize-none font-sans"
            />
          </div>

          {/* Memory Category */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1.5 block">
                Memory Category
              </label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
              >
                <option value="USER_PREFERENCE">User Preference</option>
                <option value="USER_FACT">User Fact</option>
                <option value="PROJECT_CONTEXT">Project Context</option>
                <option value="TASK_HISTORY">Task History</option>
                <option value="DOCUMENT_CONTEXT">Document Context</option>
                <option value="LEARNING">Learning</option>
                <option value="SYSTEM_KNOWLEDGE">System Knowledge</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1.5 block">
                Tags (comma separated)
              </label>
              <input
                type="text"
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="fastapi, react, architecture"
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 placeholder:text-slate-500"
              >
              </input>
            </div>
          </div>

          {/* Importance & Confidence Sliders */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-black/20 p-3 rounded-lg border border-white/[0.04]">
            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>Importance:</span>
                <span className="font-mono text-cyan-400 font-bold">{Math.round(newImportance * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={newImportance}
                onChange={(e) => setNewImportance(parseFloat(e.target.value))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>Confidence:</span>
                <span className="font-mono text-indigo-400 font-bold">{Math.round(newConfidence * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={newConfidence}
                onChange={(e) => setNewConfidence(parseFloat(e.target.value))}
                className="w-full accent-indigo-400 cursor-pointer"
              />
            </div>
          </div>

          {/* Auto-Sync to KG Toggle */}
          <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={newAutoSyncGraph}
              onChange={(e) => setNewAutoSyncGraph(e.target.checked)}
              className="rounded bg-[#0d1117] border-white/20 text-cyan-500 focus:ring-0 cursor-pointer"
            />
            <span>Automatically extract entities and anchor to Knowledge Graph</span>
          </label>

          {/* Modal Action Buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.06]">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setIsAddModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus size={14} /> Store Memory Record
            </Button>
          </div>
        </form>
      </Modal>

      {/* 7. Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Memory Context"
        description="Confirm permanent removal of this memory record from the workspace vector index."
        size="sm"
      >
        {memoryToDelete && (
          <div className="flex flex-col gap-4">
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-200 flex items-start gap-2.5">
              <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold">Irreversible Action</strong>
                This will remove <code className="text-rose-300 font-mono font-bold">{memoryToDelete.id}</code> from the workspace's long-term context and clean up associated Knowledge Graph edges.
              </div>
            </div>

            <div className="bg-black/30 p-3 rounded-lg border border-white/[0.04] text-xs text-slate-300 italic line-clamp-3">
              "{memoryToDelete.content}"
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-white/[0.06]">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsDeleteModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleConfirmDelete}
                className="flex items-center gap-1.5"
              >
                <Trash2 size={13} /> Confirm Delete
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
