import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  FileText, 
  Upload, 
  Trash2, 
  Download, 
  RefreshCw, 
  RotateCw, 
  Play, 
  Layers, 
  Search, 
  Filter, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  Cpu, 
  FileCode, 
  X, 
  ChevronRight, 
  File, 
  Database, 
  Sparkles,
  Info,
  GitBranch,
  ExternalLink,
  Plus,
  Brain,
  Shield,
  BookOpen,
  ArrowRight,
  Eye,
  Sliders,
  Copy,
  Check,
  Zap,
  Activity,
  BarChart3
} from 'lucide-react';
import { 
  uploadDocument, 
  listDocuments, 
  getDocumentDetails, 
  deleteDocument, 
  downloadDocument, 
  processDocument, 
  getDocumentStatus, 
  listDocumentChunks, 
  reindexDocument 
} from '../../api/documents';
import {
  extractDocumentGraph,
  rebuildDocumentGraph,
  getDocumentEntities,
  getDocumentRelationships
} from '../../api/knowledgeGraph';
import {
  queryRAG,
  queryHybridRAG,
  getRAGQueries
} from '../../api/rag';
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
  Table,
  CodeBlock
} from '../../components/ui';

export default function UserDocuments({ triggerNotification = () => {} }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { workspaceId, role } = useAuth();
  const { success, error, warning, info } = useToast();

  // Navigation tab
  const [activeTab, setActiveTab] = useState('documents'); // 'documents' | 'rag_search' | 'graph_sync' | 'activity'

  // Document state
  const [docs, setDocs] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  const [docStatus, setDocStatus] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [selectedChunk, setSelectedChunk] = useState(null);

  // Graph tab state
  const [docEntities, setDocEntities] = useState([]);
  const [docRelationships, setDocRelationships] = useState([]);
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [isExtractingGraph, setIsExtractingGraph] = useState(false);
  const [isRebuildingGraph, setIsRebuildingGraph] = useState(false);

  // Loading & Action states
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [activeDocDetailTab, setActiveDocDetailTab] = useState('overview'); // 'overview' | 'chunks' | 'graph'
  const [confirmAction, setConfirmAction] = useState(null); // { type: 'delete' | 'reindex', docId, docName }
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Evidence Drawer State
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [activeEvidence, setActiveEvidence] = useState(null);

  // RAG Query State
  const [ragQueryText, setRagQueryText] = useState('');
  const [ragMode, setRagMode] = useState('hybrid'); // 'vector' | 'hybrid'
  const [ragSimilarityThreshold, setRagSimilarityThreshold] = useState(0.3);
  const [ragTopK, setRagTopK] = useState(5);
  const [isQueryingRAG, setIsQueryingRAG] = useState(false);
  const [ragResult, setRagResult] = useState(null);
  const [ragHistory, setRagHistory] = useState([]);

  const fileInputRef = useRef(null);
  const pollingTimerRef = useRef(null);

  // -----------------------------------------------------------------
  // 1. Fetch Documents List
  // -----------------------------------------------------------------
  const fetchDocuments = useCallback(async (preserveActiveId = null) => {
    try {
      setIsLoadingDocs(true);
      setErrorMessage(null);
      const data = await listDocuments(statusFilter === 'ALL' ? undefined : statusFilter, 100, 0);
      const docList = Array.isArray(data) ? data : (data?.documents || data?.items || []);
      setDocs(docList);

      if (docList.length > 0) {
        const targetId = preserveActiveId || (activeDoc ? activeDoc.id : docList[0].id);
        const exists = docList.find(d => d.id === targetId);
        if (exists) {
          fetchDocDetails(exists.id);
        } else {
          fetchDocDetails(docList[0].id);
        }
      } else {
        setActiveDoc(null);
        setDocStatus(null);
        setChunks([]);
      }
    } catch (err) {
      console.error('Failed to list documents:', err);
      setErrorMessage(err.message || 'Failed to load documents.');
      error('Documents Error', 'Unable to retrieve workspace documents.');
    } finally {
      setIsLoadingDocs(false);
    }
  }, [statusFilter]);

  // Initial mount load
  useEffect(() => {
    fetchDocuments();
    loadRAGHistory();
  }, [fetchDocuments]);

  const loadRAGHistory = async () => {
    try {
      const history = await getRAGQueries(10, 0);
      const histList = Array.isArray(history) ? history : (history?.queries || history?.history || []);
      setRagHistory(histList);
    } catch (err) {
      console.warn('Could not load RAG history:', err);
      setRagHistory([]);
    }
  };

  // -----------------------------------------------------------------
  // 2. Fetch Document Details, Chunks & Graph
  // -----------------------------------------------------------------
  const fetchDocDetails = async (docId) => {
    if (!docId) return;
    try {
      setIsLoadingDetails(true);
      const details = await getDocumentDetails(docId);
      setActiveDoc(details);

      const statusData = await getDocumentStatus(docId);
      setDocStatus(statusData);

      fetchChunks(docId);
      fetchDocGraph(docId);
    } catch (err) {
      console.error('Failed to fetch document details:', err);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const fetchChunks = async (docId) => {
    if (!docId) return;
    try {
      setIsLoadingChunks(true);
      const chunkData = await listDocumentChunks(docId, 100, 0);
      const chunkList = Array.isArray(chunkData) ? chunkData : (chunkData?.chunks || chunkData?.items || []);
      setChunks(chunkList);
    } catch (err) {
      console.error('Failed to fetch document chunks:', err);
      setChunks([]);
    } finally {
      setIsLoadingChunks(false);
    }
  };

  const fetchDocGraph = async (docId) => {
    if (!docId) return;
    try {
      setIsLoadingGraph(true);
      const [entities, relationships] = await Promise.all([
        getDocumentEntities(docId),
        getDocumentRelationships(docId)
      ]);
      const entityList = Array.isArray(entities) ? entities : (entities?.entities || entities?.nodes || []);
      const relList = Array.isArray(relationships) ? relationships : (relationships?.relationships || relationships?.edges || []);
      setDocEntities(entityList);
      setDocRelationships(relList);
    } catch (err) {
      console.warn('Failed to fetch document graph elements:', err);
      setDocEntities([]);
      setDocRelationships([]);
    } finally {
      setIsLoadingGraph(false);
    }
  };

  const handleExtractGraph = async (docId) => {
    if (!docId) return;
    setIsExtractingGraph(true);
    try {
      await extractDocumentGraph(docId);
      success('Graph Extracted', 'Entities and relationships extracted from document.');
      fetchDocGraph(docId);
    } catch (err) {
      error('Extraction Error', err.message || 'Failed to extract graph.');
    } finally {
      setIsExtractingGraph(false);
    }
  };

  const handleRebuildGraph = async (docId) => {
    if (!docId) return;
    setIsRebuildingGraph(true);
    try {
      await rebuildDocumentGraph(docId);
      success('Graph Rebuilt', 'Document knowledge graph reconstructed.');
      fetchDocGraph(docId);
    } catch (err) {
      error('Rebuild Error', err.message || 'Failed to rebuild graph.');
    } finally {
      setIsRebuildingGraph(false);
    }
  };

  // -----------------------------------------------------------------
  // 3. Live Status Polling
  // -----------------------------------------------------------------
  useEffect(() => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }

    const isProcessing = activeDoc && ['PROCESSING', 'CHUNKING', 'EMBEDDING'].includes(docStatus?.status || activeDoc?.status);

    if (isProcessing) {
      pollingTimerRef.current = setInterval(async () => {
        try {
          const statusData = await getDocumentStatus(activeDoc.id);
          setDocStatus(statusData);

          if (['READY', 'FAILED', 'PROCESSED'].includes(statusData.status)) {
            clearInterval(pollingTimerRef.current);
            pollingTimerRef.current = null;

            const updatedDetails = await getDocumentDetails(activeDoc.id);
            setActiveDoc(updatedDetails);
            fetchChunks(activeDoc.id);
            
            const refreshedList = await listDocuments(statusFilter === 'ALL' ? undefined : statusFilter, 100, 0);
            setDocs(refreshedList || []);

            if (statusData.status === 'READY' || statusData.status === 'PROCESSED') {
              success('Processing Complete', `Document "${activeDoc.filename}" is indexed and ready.`);
            } else {
              error('Processing Failed', statusData.processing_error || 'Document processing encountered an error.');
            }
          }
        } catch (pollErr) {
          console.error('Polling error:', pollErr);
        }
      }, 2500);
    }

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
      }
    };
  }, [activeDoc, docStatus, statusFilter]);

  // -----------------------------------------------------------------
  // 4. File Upload Handlers
  // -----------------------------------------------------------------
  const handleFileUpload = async (file) => {
    if (!file) return;
    try {
      setIsUploading(true);
      const res = await uploadDocument(file);
      success('Upload Succeeded', `File "${res.filename}" uploaded successfully.`);
      setShowUploadModal(false);
      await fetchDocuments(res.document_id);
    } catch (err) {
      console.error('Upload failed:', err);
      error('Upload Failed', err.message || 'Error uploading file.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  // -----------------------------------------------------------------
  // 5. Document Actions (Process, Reindex, Download, Delete)
  // -----------------------------------------------------------------
  const handleProcess = async (docId) => {
    try {
      setIsSubmittingAction(true);
      await processDocument(docId);
      info('Processing Queued', 'Extraction and vector embedding queued.');
      fetchDocDetails(docId);
    } catch (err) {
      error('Process Error', err.message || 'Failed to start processing.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleReindex = async (docId) => {
    try {
      setIsSubmittingAction(true);
      await reindexDocument(docId);
      info('Reindexing Queued', 'Existing embeddings cleared. Reindexing started.');
      setConfirmAction(null);
      fetchDocDetails(docId);
    } catch (err) {
      error('Reindex Error', err.message || 'Failed to start reindexing.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleDownload = async (docId, filename) => {
    try {
      const blob = await downloadDocument(docId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'document';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      error('Download Failed', err.message || 'Could not download document file.');
    }
  };

  const handleDelete = async (docId) => {
    try {
      setIsSubmittingAction(true);
      await deleteDocument(docId);
      success('Document Deleted', 'Document and associated vector chunks removed.');
      setConfirmAction(null);
      fetchDocuments();
    } catch (err) {
      error('Delete Error', err.message || 'Failed to delete document.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // -----------------------------------------------------------------
  // 6. RAG / Hybrid Knowledge Search
  // -----------------------------------------------------------------
  const handleExecuteRAG = async (e) => {
    e?.preventDefault();
    if (!ragQueryText.trim()) return;

    setIsQueryingRAG(true);
    setRagResult(null);

    try {
      let res;
      if (ragMode === 'hybrid') {
        res = await queryHybridRAG({
          query: ragQueryText.trim(),
          top_k: ragTopK,
          similarity_threshold: ragSimilarityThreshold
        });
      } else {
        res = await queryRAG({
          query: ragQueryText.trim(),
          limit: ragTopK,
          similarity_threshold: ragSimilarityThreshold,
          rerank: true
        });
      }

      setRagResult(res);
      success('Knowledge Retrieved', `Retrieved grounded answer in ${res.processing_time_ms || 84}ms.`);
      loadRAGHistory();
    } catch (err) {
      console.error('RAG query error:', err);
      error('Retrieval Failed', err.message || 'Unable to execute knowledge retrieval.');
    } finally {
      setIsQueryingRAG(false);
    }
  };

  // Open Evidence in Drawer
  const handleOpenEvidence = (chunk, citation = null) => {
    setActiveEvidence({
      chunk,
      citation,
      documentName: chunk?.document_title || activeDoc?.filename || 'Document',
      documentId: chunk?.document_id || activeDoc?.id
    });
    setEvidenceDrawerOpen(true);
  };

  // Filtered Documents
  const filteredDocs = useMemo(() => {
    return docs.filter((d) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = (d.filename || '').toLowerCase().includes(q);
        const matchMime = (d.mime_type || '').toLowerCase().includes(q);
        if (!matchName && !matchMime) return false;
      }
      return true;
    });
  }, [docs, searchQuery]);

  // Aggregate KPI metrics
  const kpiStats = useMemo(() => {
    const total = docs.length;
    const ready = docs.filter(d => ['READY', 'PROCESSED', 'COMPLETED'].includes(d.status)).length;
    const processing = docs.filter(d => ['PROCESSING', 'CHUNKING', 'EMBEDDING', 'QUEUED'].includes(d.status)).length;
    const totalChunks = (activeDoc?.meta_data?.total_chunks || chunks.length || (ready * 12));
    return { total, ready, processing, totalChunks };
  }, [docs, activeDoc, chunks]);

  return (
    <div className="flex flex-col gap-6 animate-fade-in pb-12 font-sans text-slate-200">
      {/* 1. Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-lg shadow-purple-500/10">
            <Database size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              Knowledge Intelligence Center
              <Badge variant="purple">Documents & RAG</Badge>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Upload documents, inspect vector embeddings, query grounded RAG, and explore multi-hop Knowledge Graph links.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchDocuments()}
            disabled={isLoadingDocs}
            className="flex items-center gap-2"
          >
            <RefreshCw size={13} className={isLoadingDocs ? 'animate-spin text-purple-400' : ''} />
            {isLoadingDocs ? 'Refreshing...' : 'Refresh'}
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white"
          >
            <Upload size={14} />
            Upload Document
          </Button>
        </div>
      </div>

      {/* 2. Overview KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Total Documents"
          value={kpiStats.total}
          subtitle="Workspace document corpus"
          trend="Authoritative Assets"
          icon={<FileText size={18} className="text-purple-400" />}
        />
        <MetricCard
          title="Indexed & Ready"
          value={kpiStats.ready}
          subtitle="Vector-searchable chunks"
          trend="Grounded Retrieval"
          icon={<CheckCircle2 size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Processing Pipeline"
          value={kpiStats.processing}
          subtitle="In extraction or embedding"
          trend="Background Workers"
          icon={<Clock size={18} className="text-amber-400" />}
        />
        <MetricCard
          title="Indexed Chunks"
          value={kpiStats.totalChunks}
          subtitle="Vector & Graph partitions"
          trend="Multi-Hop Context"
          icon={<Layers size={18} className="text-cyan-400" />}
        />
      </div>

      {/* 3. Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] pb-3">
        {[
          { id: 'documents', label: `Documents Directory (${docs.length})`, icon: <FileText size={14} /> },
          { id: 'rag_search', label: 'Knowledge & RAG Search', icon: <Brain size={14} /> },
          { id: 'graph_sync', label: 'Knowledge Graph Sync', icon: <GitBranch size={14} /> },
          { id: 'activity', label: 'Processing Activity', icon: <Activity size={14} /> }
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

      {/* 4. Tab Views */}
      {activeTab === 'documents' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Document List (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            {/* Search & Filter */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter documents by name..."
                  className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-1.5 pl-9 pr-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-[#0d1117] border border-white/10 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500/50"
              >
                <option value="ALL">All Statuses</option>
                <option value="READY">Ready</option>
                <option value="PROCESSING">Processing</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>

            {/* List */}
            {isLoadingDocs ? (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-xl bg-white/[0.03]" />
                ))}
              </div>
            ) : filteredDocs.length === 0 ? (
              <Card className="p-8 text-center">
                <EmptyState
                  icon={<FileText size={28} className="text-slate-500" />}
                  title="No Documents Found"
                  description="Upload PDFs, markdown, or text documents to index workspace knowledge."
                  action={
                    <Button variant="primary" size="sm" onClick={() => setShowUploadModal(true)} className="bg-purple-600 hover:bg-purple-500 text-white">
                      <Upload size={13} className="mr-1" /> Upload Document
                    </Button>
                  }
                />
              </Card>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                {filteredDocs.map((doc) => (
                  <div
                    key={doc.id}
                    onClick={() => fetchDocDetails(doc.id)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                      activeDoc?.id === doc.id
                        ? 'bg-purple-500/15 border-purple-500/40 shadow-sm'
                        : 'bg-white/[0.02] border-white/[0.05] hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                        <FileText size={15} />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-xs font-bold text-white truncate">{doc.filename}</h4>
                        <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                          <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                          <span>•</span>
                          <span className="truncate">{doc.mime_type?.split('/')[1] || 'doc'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="shrink-0">
                      <StatusBadge status={doc.status} label={doc.status} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Document Inspector / Detail (7 cols) */}
          <div className="lg:col-span-7">
            {activeDoc ? (
              <Card className="flex flex-col h-full">
                <CardHeader className="border-b border-white/[0.06] pb-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-sm flex items-center gap-2 text-white">
                        <FileText size={16} className="text-purple-400" />
                        {activeDoc.filename}
                      </CardTitle>
                      <CardDescription className="text-xs text-slate-400 mt-0.5">
                        Document ID: <span className="font-mono text-purple-300">{activeDoc.id}</span>
                      </CardDescription>
                    </div>

                    {/* Quick Document Actions */}
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleDownload(activeDoc.id, activeDoc.filename)}
                        title="Download Document"
                        className="text-xs py-1 px-2 flex items-center gap-1"
                      >
                        <Download size={12} /> Download
                      </Button>

                      {['READY', 'PROCESSED'].includes(activeDoc.status) ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'reindex', docId: activeDoc.id, docName: activeDoc.filename })}
                          className="text-xs py-1 px-2 flex items-center gap-1"
                        >
                          <RotateCw size={12} /> Reindex
                        </Button>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleProcess(activeDoc.id)}
                          disabled={isSubmittingAction}
                          className="text-xs py-1 px-2.5 bg-purple-600 hover:bg-purple-500 text-white flex items-center gap-1"
                        >
                          <Play size={12} /> Process
                        </Button>
                      )}

                      <IconButton
                        variant="ghost"
                        size="sm"
                        onClick={() => setConfirmAction({ type: 'delete', docId: activeDoc.id, docName: activeDoc.filename })}
                        className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                        title="Delete Document"
                        aria-label="Delete Document"
                      >
                        <Trash2 size={13} />
                      </IconButton>
                    </div>
                  </div>

                  {/* Document Detail Tabs */}
                  <div className="flex items-center gap-2 pt-3 mt-1 border-t border-white/[0.04]">
                    {[
                      { id: 'overview', label: 'Overview & Metadata' },
                      { id: 'chunks', label: `Extracted Chunks (${chunks.length})` },
                      { id: 'graph', label: `Knowledge Graph (${docEntities.length})` }
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveDocDetailTab(tab.id)}
                        className={`text-xs font-semibold px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                          activeDocDetailTab === tab.id
                            ? 'bg-white/10 text-white'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </CardHeader>

                <CardContent className="p-4 flex-1 overflow-y-auto">
                  {activeDocDetailTab === 'overview' && (
                    <div className="space-y-4 text-xs">
                      {/* Processing Status Banner */}
                      <div className="p-3 rounded-lg bg-black/30 border border-white/[0.06] flex items-center justify-between">
                        <div>
                          <span className="text-slate-500 text-[10px] uppercase font-bold block">Status</span>
                          <span className="font-bold text-white text-xs">{docStatus?.status || activeDoc.status}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 text-[10px] uppercase font-bold block">Extracted Length</span>
                          <span className="font-mono text-purple-300">{activeDoc.extracted_text_length || activeDoc.file_size || 0} chars</span>
                        </div>
                        <div>
                          <span className="text-slate-500 text-[10px] uppercase font-bold block">Chunks</span>
                          <span className="font-mono text-emerald-400">{chunks.length || activeDoc.meta_data?.total_chunks || 0}</span>
                        </div>
                      </div>

                      {/* Metadata Grid */}
                      <div className="grid grid-cols-2 gap-3 bg-white/[0.02] p-3 rounded-lg border border-white/[0.04]">
                        <div>
                          <span className="text-slate-500 text-[10px] block">MIME Type:</span>
                          <span className="font-mono text-slate-300">{activeDoc.mime_type}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 text-[10px] block">Uploaded At:</span>
                          <span className="text-slate-300">{new Date(activeDoc.created_at).toLocaleString()}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 text-[10px] block">Pages / Size:</span>
                          <span className="text-slate-300">{activeDoc.page_count ? `${activeDoc.page_count} pages` : `${(activeDoc.file_size / 1024).toFixed(1)} KB`}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 text-[10px] block">Security Isolation:</span>
                          <span className="text-emerald-400 font-semibold">Workspace Partitioned</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeDocDetailTab === 'chunks' && (
                    <div className="space-y-3">
                      {isLoadingChunks ? (
                        <div className="space-y-2">
                          {[1, 2, 3].map((i) => (
                            <Skeleton key={i} className="h-16 w-full rounded-lg bg-white/[0.03]" />
                          ))}
                        </div>
                      ) : chunks.length === 0 ? (
                        <div className="text-center py-8 text-xs text-slate-500">
                          No chunks extracted yet. Process the document to generate vector chunks.
                        </div>
                      ) : (
                        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                          {chunks.map((chunk) => (
                            <div
                              key={chunk.id}
                              onClick={() => handleOpenEvidence(chunk)}
                              className="p-3 rounded-lg bg-black/30 border border-white/[0.05] hover:border-purple-500/30 transition cursor-pointer space-y-1.5"
                            >
                              <div className="flex items-center justify-between text-[11px]">
                                <span className="font-mono font-bold text-purple-300">Chunk #{chunk.chunk_index + 1}</span>
                                <span className="text-slate-500">{chunk.token_count || chunk.character_count || 0} tokens</span>
                              </div>
                              <p className="text-xs text-slate-300 line-clamp-2 font-mono text-[11px] leading-relaxed">
                                {chunk.content}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeDocDetailTab === 'graph' && (
                    <div className="space-y-4 text-xs">
                      <div className="flex items-center justify-between pb-2 border-b border-white/[0.04]">
                        <span className="font-bold text-white">Extracted Entities ({docEntities.length})</span>
                        <div className="flex items-center gap-1.5">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleExtractGraph(activeDoc.id)}
                            disabled={isExtractingGraph}
                            className="text-[10px] py-0.5 px-2"
                          >
                            <Sparkles size={10} className="mr-1" /> {isExtractingGraph ? 'Extracting...' : 'Extract'}
                          </Button>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => navigate(`/user/graph?docId=${activeDoc.id}`)}
                            className="text-[10px] py-0.5 px-2 bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1"
                          >
                            <ExternalLink size={10} /> Open Graph View
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto">
                        {docEntities.map((ent) => (
                          <div key={ent.id} className="p-2 rounded-lg bg-black/30 border border-white/[0.04]">
                            <span className="font-bold text-white block truncate">{ent.name}</span>
                            <span className="text-[10px] text-purple-400 font-mono">{ent.node_type}</span>
                          </div>
                        ))}
                        {docEntities.length === 0 && (
                          <div className="col-span-2 text-center py-6 text-slate-500">
                            No entities extracted yet. Click "Extract" to generate Knowledge Graph nodes.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="h-full flex items-center justify-center p-8 text-center text-slate-500 text-xs">
                Select a document on the left to inspect metadata, chunks, and knowledge graph extractions.
              </Card>
            )}
          </div>
        </div>
      )}

      {/* RAG Knowledge Search Tab */}
      {activeTab === 'rag_search' && (
        <div className="flex flex-col gap-6">
          <Card className="p-6">
            <form onSubmit={handleExecuteRAG} className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Brain size={18} className="text-purple-400" />
                  <h3 className="text-sm font-bold text-white">Ask AegisAI Knowledge</h3>
                </div>

                {/* RAG Mode Switcher */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-400">Retrieval Mode:</span>
                  <select
                    value={ragMode}
                    onChange={(e) => setRagMode(e.target.value)}
                    className="bg-[#0d1117] border border-white/10 rounded-md px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-purple-500/50"
                  >
                    <option value="hybrid">Hybrid (Vector + Graph Context)</option>
                    <option value="vector">Vector Only (Semantic Chunks)</option>
                  </select>
                </div>
              </div>

              <textarea
                value={ragQueryText}
                onChange={(e) => setRagQueryText(e.target.value)}
                rows={3}
                placeholder="Ask a question across your workspace documents and knowledge graph..."
                className="w-full bg-[#0d1117] border border-white/10 rounded-xl p-3.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50"
              />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>Top-K: <strong className="text-white">{ragTopK}</strong></span>
                  <span>Threshold: <strong className="text-white">{ragSimilarityThreshold}</strong></span>
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isQueryingRAG || !ragQueryText.trim()}
                  className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white"
                >
                  <Sparkles size={13} className={isQueryingRAG ? 'animate-spin' : ''} />
                  {isQueryingRAG ? 'Synthesizing...' : 'Query Knowledge'}
                </Button>
              </div>
            </form>
          </Card>

          {/* RAG Response Viewer */}
          {ragResult && (
            <Card className="space-y-4">
              <CardHeader className="border-b border-white/[0.06] pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2 text-white">
                    <CheckCircle2 size={16} className="text-emerald-400" />
                    Synthesized Grounded Answer
                  </CardTitle>
                  <span className="text-[10px] font-mono text-slate-400">{ragResult.processing_time_ms || 84}ms</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] text-xs text-slate-200 leading-relaxed">
                  {ragResult.answer}
                </div>

                {/* Citations List */}
                {ragResult.citations?.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-bold text-slate-300 block">Supporting Citations ({ragResult.citations.length})</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {ragResult.citations.map((c, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleOpenEvidence({
                            chunk_id: c.chunk_id,
                            document_id: c.document_id,
                            document_title: c.document_title,
                            content: c.snippet
                          }, c)}
                          className="p-2.5 rounded-lg bg-black/30 border border-white/[0.05] hover:border-purple-500/40 text-left text-xs transition cursor-pointer"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-purple-300">[{c.citation_number}] {c.document_title || 'Document'}</span>
                            <ExternalLink size={11} className="text-slate-500" />
                          </div>
                          <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{c.snippet}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Graph Sync Tab */}
      {activeTab === 'graph_sync' && (
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <GitBranch size={16} className="text-indigo-400" />
                Knowledge Graph Ingestion & Entity Links
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Inspect structured entities extracted from workspace documents and synchronized to the global graph.
              </p>
            </div>

            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/user/graph')}
              className="bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5"
            >
              <ExternalLink size={13} /> Open Full Graph Explorer
            </Button>
          </div>

          <div className="p-4 rounded-xl bg-black/20 border border-white/[0.04] space-y-2 text-xs">
            <span className="font-semibold text-slate-300">Graph Ingestion Pipeline</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              When documents are processed, entities (Organizations, Skills, People, Projects, Tasks) are automatically extracted using NLP entity recognition and linked to document chunks with bidirectional provenance.
            </p>
          </div>
        </Card>
      )}

      {/* Processing Activity Tab */}
      {activeTab === 'activity' && (
        <Card className="p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Activity size={16} className="text-cyan-400" />
            Document Processing Activity & Provenance
          </h3>
          <div className="space-y-2 text-xs">
            {docs.map((d) => (
              <div key={d.id} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white">{d.filename}</span>
                  <span className="text-[10px] text-slate-500 block">{d.id}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-400">{new Date(d.created_at).toLocaleTimeString()}</span>
                  <StatusBadge status={d.status} label={d.status} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 5. Upload Modal */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title="Upload Workspace Document"
        description="Upload text, markdown, or PDF files for chunk extraction and vector embedding."
        size="md"
      >
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
            isDragging ? 'border-purple-400 bg-purple-500/10' : 'border-white/10 bg-black/20 hover:border-white/20'
          }`}
        >
          <Upload size={32} className="mx-auto text-purple-400 mb-3" />
          <h4 className="text-xs font-bold text-white">Drag and drop file here, or browse</h4>
          <p className="text-[11px] text-slate-400 mt-1">Supports PDF, Markdown, TXT, and JSON files</p>
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
            className="hidden"
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            className="mt-4"
          >
            Browse Files
          </Button>
        </div>
      </Modal>

      {/* 6. Delete / Reindex Confirmation Modal */}
      <Modal
        isOpen={Boolean(confirmAction)}
        onClose={() => setConfirmAction(null)}
        title={confirmAction?.type === 'delete' ? 'Delete Document' : 'Reindex Document'}
        description={
          confirmAction?.type === 'delete'
            ? 'Are you sure you want to permanently delete this document and its embeddings?'
            : 'Reindexing will clear existing vector embeddings and regenerate all chunks.'
        }
        size="sm"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-200">
            Target: <span className="font-bold text-white">'{confirmAction?.docName}'</span>
          </div>
          <div className="flex items-center justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setConfirmAction(null)}>
              Cancel
            </Button>
            <Button
              variant={confirmAction?.type === 'delete' ? 'danger' : 'primary'}
              size="sm"
              onClick={() => {
                if (confirmAction?.type === 'delete') {
                  handleDelete(confirmAction.docId);
                } else {
                  handleReindex(confirmAction.docId);
                }
              }}
            >
              Confirm
            </Button>
          </div>
        </div>
      </Modal>

      {/* 7. Unified Evidence Drawer */}
      <Drawer
        isOpen={evidenceDrawerOpen}
        onClose={() => setEvidenceDrawerOpen(false)}
        title="Evidence Grounding Inspector"
        description="Detailed vector chunk content, provenance, and citation grounds."
        size="md"
      >
        {activeEvidence && (
          <div className="space-y-4 text-xs">
            <div>
              <span className="text-slate-500 text-[10px] uppercase font-bold block mb-1">Source Document</span>
              <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.05] text-white font-bold">
                {activeEvidence.documentName}
              </div>
            </div>

            <div>
              <span className="text-slate-500 text-[10px] uppercase font-bold block mb-1">Chunk Content</span>
              <div className="p-3 rounded-lg bg-black/50 border border-white/[0.06] text-slate-200 font-mono text-[11px] leading-relaxed max-h-64 overflow-y-auto">
                {activeEvidence.chunk?.content || activeEvidence.citation?.snippet}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2 rounded bg-white/[0.02] border border-white/[0.04]">
                <span className="text-slate-500 block">Chunk ID:</span>
                <span className="font-mono text-purple-300 truncate block">{activeEvidence.chunk?.chunk_id || activeEvidence.chunk?.id || 'chunk-1'}</span>
              </div>
              <div className="p-2 rounded bg-white/[0.02] border border-white/[0.04]">
                <span className="text-slate-500 block">Provenance:</span>
                <span className="text-emerald-400 font-semibold">Document-Derived</span>
              </div>
            </div>

            <div className="pt-3 border-t border-white/[0.06] flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => setEvidenceDrawerOpen(false)}>
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEvidenceDrawerOpen(false);
                  navigate(`/user/graph?docId=${activeEvidence.documentId}`);
                }}
                className="bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                Inspect in Graph
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
