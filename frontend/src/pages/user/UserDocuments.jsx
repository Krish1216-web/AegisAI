import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Plus
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

export default function UserDocuments({ triggerNotification = () => {} }) {
  const navigate = useNavigate();

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

  // Filters & Tabs
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'chunks'
  const [confirmAction, setConfirmAction] = useState(null); // { type: 'delete' | 'reindex', docId, docName }

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
      setDocs(data || []);

      if (data && data.length > 0) {
        const targetId = preserveActiveId || (activeDoc ? activeDoc.id : data[0].id);
        const exists = data.find(d => d.id === targetId);
        if (exists) {
          fetchDocDetails(exists.id);
        } else {
          fetchDocDetails(data[0].id);
        }
      } else {
        setActiveDoc(null);
        setDocStatus(null);
        setChunks([]);
      }
    } catch (err) {
      console.error('Failed to list documents:', err);
      setErrorMessage(err.message || 'Failed to load documents.');
    } finally {
      setIsLoadingDocs(false);
    }
  }, [statusFilter]);

  // Initial mount load
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // -----------------------------------------------------------------
  // 2. Fetch Document Details & Chunks
  // -----------------------------------------------------------------
  const fetchDocDetails = async (docId) => {
    if (!docId) return;
    try {
      setIsLoadingDetails(true);
      const details = await getDocumentDetails(docId);
      setActiveDoc(details);

      // Also get initial status metrics
      const statusData = await getDocumentStatus(docId);
      setDocStatus(statusData);

      // Fetch chunks
      fetchChunks(docId);

      // Fetch Knowledge Graph elements
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
      setChunks(chunkData || []);
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
      setDocEntities(entities || []);
      setDocRelationships(relationships || []);
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
      triggerNotification('Graph Extracted', 'Entities and relationships extracted successfully.');
      fetchDocGraph(docId);
    } catch (err) {
      triggerNotification('Extraction Error', err.message || 'Failed to extract graph.');
    } finally {
      setIsExtractingGraph(false);
    }
  };

  const handleRebuildGraph = async (docId) => {
    if (!docId) return;
    setIsRebuildingGraph(true);
    try {
      await rebuildDocumentGraph(docId);
      triggerNotification('Graph Rebuilt', 'Document knowledge graph reconstructed.');
      fetchDocGraph(docId);
    } catch (err) {
      triggerNotification('Rebuild Error', err.message || 'Failed to rebuild graph.');
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

            // Refresh details & list to stay in sync
            const updatedDetails = await getDocumentDetails(activeDoc.id);
            setActiveDoc(updatedDetails);
            fetchChunks(activeDoc.id);
            
            // Refresh list items
            const refreshedList = await listDocuments(statusFilter === 'ALL' ? undefined : statusFilter, 100, 0);
            setDocs(refreshedList || []);

            if (statusData.status === 'READY' || statusData.status === 'PROCESSED') {
              triggerNotification('Processing Complete', `Document "${activeDoc.filename}" is ready for RAG querying.`);
            } else {
              triggerNotification('Processing Failed', statusData.processing_error || 'Document processing encountered an error.');
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
  }, [activeDoc?.id, docStatus?.status, activeDoc?.status, statusFilter, triggerNotification]);

  // -----------------------------------------------------------------
  // 4. File Upload Handlers
  // -----------------------------------------------------------------
  const handleFileUpload = async (file) => {
    if (!file) return;

    // Check size limit (< 50MB)
    const maxBytes = 50 * 1024 * 1024;
    if (file.size > maxBytes) {
      triggerNotification('Upload Failed', 'File size exceeds the 50MB platform limit.');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);

    try {
      const uploadRes = await uploadDocument(file);
      triggerNotification('Upload Successful', `"${file.name}" uploaded and queued for workspace processing.`);
      
      // Refresh documents and select the uploaded file
      await fetchDocuments(uploadRes.document_id);
    } catch (err) {
      console.error('Upload failed:', err);
      let userFriendly = err.message || 'An error occurred while uploading.';
      if (err.code === 'DUPLICATE_DOCUMENT') {
        userFriendly = 'A file with identical content has already been uploaded in this workspace.';
      } else if (err.code === 'UNSUPPORTED_FILE_TYPE') {
        userFriendly = 'File type not supported. Please upload PDF, DOCX, PPTX, XLSX, TXT, CSV, or media files.';
      } else if (err.code === 'DOCUMENT_TOO_LARGE') {
        userFriendly = 'The file exceeds the maximum 50MB upload limit.';
      }
      triggerNotification('Upload Failed', userFriendly);
      setErrorMessage(userFriendly);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  // -----------------------------------------------------------------
  // 5. Document Actions
  // -----------------------------------------------------------------
  const handleDownload = async (doc) => {
    if (!doc) return;
    try {
      triggerNotification('Downloading', `Preparing "${doc.original_filename || doc.filename}"...`);
      const blob = await downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.original_filename || doc.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      triggerNotification('Download Failed', err.message || 'Could not download document.');
    }
  };

  const handleProcess = async (docId) => {
    if (!docId) return;
    try {
      setIsSubmittingAction(true);
      await processDocument(docId);
      triggerNotification('Processing Initiated', 'Background extraction and chunking pipeline started.');
      fetchDocDetails(docId);
    } catch (err) {
      triggerNotification('Process Failed', err.message || 'Failed to start document processing.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleReindex = async (docId) => {
    if (!docId) return;
    try {
      setIsSubmittingAction(true);
      await reindexDocument(docId);
      triggerNotification('Reindexing Started', 'Document chunks & embeddings are being regenerated.');
      setConfirmAction(null);
      fetchDocDetails(docId);
    } catch (err) {
      triggerNotification('Reindex Failed', err.message || 'Failed to reindex document.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!docId) return;
    try {
      setIsSubmittingAction(true);
      await deleteDocument(docId);
      triggerNotification('Document Deleted', 'Document and associated vectors removed.');
      setConfirmAction(null);

      if (activeDoc?.id === docId) {
        setActiveDoc(null);
        setDocStatus(null);
        setChunks([]);
      }
      fetchDocuments();
    } catch (err) {
      triggerNotification('Delete Failed', err.message || 'Failed to delete document.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // -----------------------------------------------------------------
  // Utilities
  // -----------------------------------------------------------------
  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateString;
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || 'UNKNOWN').toUpperCase();
    switch (s) {
      case 'READY':
      case 'PROCESSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 size={11} /> READY
          </span>
        );
      case 'PROCESSING':
      case 'CHUNKING':
      case 'EMBEDDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <RotateCw size={11} className="animate-spin" /> {s}
          </span>
        );
      case 'UPLOADED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Clock size={11} /> UPLOADED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle size={11} /> FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            {s}
          </span>
        );
    }
  };

  // Filtered documents list
  const filteredDocs = docs.filter(doc => {
    const nameMatch = (doc.filename || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                      (doc.original_filename || '').toLowerCase().includes(searchQuery.toLowerCase());
    return nameMatch;
  });

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-140px)] animate-fade-in overflow-hidden">
      
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <FileText className="text-cyan-400" size={22} />
            Documents Hub
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise document storage, text extraction, intelligent chunking, and pgvector embeddings.
          </p>
        </div>

        <button 
          onClick={() => fetchDocuments(activeDoc?.id)} 
          disabled={isLoadingDocs}
          className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
        >
          <RefreshCw size={13} className={isLoadingDocs ? 'animate-spin text-cyan-400' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        
        {/* Left Side: Upload & Document Registry */}
        <div className="w-88 flex flex-col gap-4 shrink-0 overflow-y-auto pr-1">
          
          {/* Upload Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => !isUploading && fileInputRef.current?.click()}
            className={`glass-panel p-5 border-dashed text-center cursor-pointer transition-all ${
              isDragging 
                ? 'border-cyan-400 bg-cyan-500/10' 
                : 'border-cyan-500/20 hover:border-cyan-500/40 bg-cyan-950/10'
            } ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              accept=".pdf,.docx,.pptx,.xlsx,.txt,.csv,.jpg,.jpeg,.png,.webp,.wav,.mp3,.mp4"
              className="hidden"
            />
            {isUploading ? (
              <div className="flex flex-col items-center py-2">
                <RotateCw size={24} className="text-cyan-400 animate-spin mb-2" />
                <span className="text-xs font-semibold text-white">Uploading file securely...</span>
                <span className="text-[10px] text-slate-400 mt-1">Generating SHA-256 and storing payload</span>
              </div>
            ) : (
              <div className="group">
                <Upload size={22} className="mx-auto text-slate-400 group-hover:text-cyan-400 transition-colors mb-2" />
                <h4 className="text-xs font-semibold text-white">Upload New Document</h4>
                <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                  Drag & drop or click to browse.<br />
                  <span className="text-[9px] text-slate-500">PDF, DOCX, PPTX, XLSX, TXT, CSV, Media (Max 50MB)</span>
                </p>
              </div>
            )}
          </div>

          {/* Search & Filter Bar */}
          <div className="glass-panel p-3 flex flex-col gap-2">
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="w-full bg-white/5 border border-white/5 rounded-lg py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-cyan-500/40 transition-all"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter size={12} className="text-slate-500 shrink-0" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full bg-[#0d1017] border border-white/10 rounded-md py-1 px-2 text-[11px] text-slate-300 outline-none focus:border-cyan-500/40"
              >
                <option value="ALL">All Statuses</option>
                <option value="UPLOADED">Uploaded</option>
                <option value="PROCESSING">Processing</option>
                <option value="READY">Ready</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>
          </div>

          {/* Document Registry List */}
          <div className="glass-panel p-4 flex-1 flex flex-col min-h-64 overflow-hidden">
            <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3 shrink-0">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Registry ({filteredDocs.length})
              </h4>
            </div>

            <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1">
              {isLoadingDocs ? (
                <div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
                  <RotateCw size={18} className="animate-spin text-cyan-400" />
                  <span className="text-xs">Loading registry...</span>
                </div>
              ) : errorMessage ? (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex flex-col gap-2">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertCircle size={14} /> Error Loading Registry
                  </div>
                  <p className="text-[11px] text-rose-300">{errorMessage}</p>
                  <button onClick={() => fetchDocuments()} className="text-[10px] underline hover:text-white self-start">
                    Retry
                  </button>
                </div>
              ) : filteredDocs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 text-slate-500 text-center px-4">
                  <FileText size={28} className="text-slate-700 mb-2" />
                  <span className="text-xs font-medium text-slate-400">No documents found</span>
                  <span className="text-[10px] text-slate-600 mt-0.5">
                    {searchQuery ? 'Try matching another query term.' : 'Upload your first document above.'}
                  </span>
                </div>
              ) : (
                filteredDocs.map((doc) => {
                  const isSelected = activeDoc?.id === doc.id;
                  return (
                    <div
                      key={doc.id}
                      onClick={() => fetchDocDetails(doc.id)}
                      className={`flex items-start gap-3 p-3 rounded-lg border text-xs cursor-pointer transition-all hover:bg-white/5 ${
                        isSelected 
                          ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300' 
                          : 'bg-white/2 border-white/5 text-slate-400'
                      }`}
                    >
                      <File size={16} className={`mt-0.5 shrink-0 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                      <div className="flex-1 min-w-0">
                        <h5 className="font-semibold text-slate-200 truncate" title={doc.original_filename || doc.filename}>
                          {doc.original_filename || doc.filename}
                        </h5>
                        <div className="flex items-center justify-between mt-1 text-[10px] text-slate-500">
                          <span>{formatBytes(doc.file_size)}</span>
                          {getStatusBadge(doc.status)}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </div>

        {/* Right Side: Active Document Workspace */}
        <div className="flex-1 glass-panel flex flex-col bg-[#090b10] border-white/5 rounded-xl overflow-hidden">
          {activeDoc ? (
            <React.Fragment>
              {/* Workspace Header */}
              <div className="h-16 border-b border-white/5 bg-[#0d101780] flex items-center justify-between px-6 shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
                    <FileText size={18} className="text-cyan-400" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-white truncate" title={activeDoc.original_filename || activeDoc.filename}>
                      {activeDoc.original_filename || activeDoc.filename}
                    </h3>
                    <div className="flex items-center gap-2 text-[10px] text-slate-500 mt-0.5">
                      <span>ID: <span className="font-mono">{activeDoc.id.slice(0, 8)}...</span></span>
                      <span>•</span>
                      <span>Uploaded: {formatDate(activeDoc.created_at)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {getStatusBadge(docStatus?.status || activeDoc.status)}

                  {/* Actions Toolbar */}
                  <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/10">
                    <button
                      onClick={() => handleDownload(activeDoc)}
                      title="Download Original File"
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded transition-all cursor-pointer"
                    >
                      <Download size={15} />
                    </button>

                    {['UPLOADED', 'FAILED'].includes(docStatus?.status || activeDoc.status) && (
                      <button
                        onClick={() => handleProcess(activeDoc.id)}
                        disabled={isSubmittingAction}
                        title="Trigger Text Extraction & Chunking"
                        className="p-1.5 text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded transition-all cursor-pointer"
                      >
                        <Play size={15} />
                      </button>
                    )}

                    {['READY', 'PROCESSED'].includes(docStatus?.status || activeDoc.status) && (
                      <button
                        onClick={() => setConfirmAction({ type: 'reindex', docId: activeDoc.id, docName: activeDoc.original_filename || activeDoc.filename })}
                        disabled={isSubmittingAction}
                        title="Reindex Document & Generate Embeddings"
                        className="p-1.5 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 rounded transition-all cursor-pointer"
                      >
                        <RotateCw size={15} />
                      </button>
                    )}
                    
                    {/* Explore in Knowledge Graph */}
                    <button
                      onClick={() => navigate(`/user/knowledge-graph?docId=${activeDoc.id}`)}
                      title="Explore in Knowledge Graph"
                      className="p-1.5 text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 rounded transition-all cursor-pointer"
                    >
                      <GitBranch size={15} />
                    </button>

                    <button
                      onClick={() => setConfirmAction({ type: 'delete', docId: activeDoc.id, docName: activeDoc.original_filename || activeDoc.filename })}
                      disabled={isSubmittingAction}
                      title="Delete Document"
                      className="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded transition-all cursor-pointer"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-white/5 bg-[#090b10] px-6 shrink-0">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`py-3 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
                    activeTab === 'overview'
                      ? 'border-cyan-400 text-cyan-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Info size={14} /> Overview & Metadata
                </button>
                <button
                  onClick={() => setActiveTab('chunks')}
                  className={`py-3 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
                    activeTab === 'chunks'
                      ? 'border-cyan-400 text-cyan-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Layers size={14} /> Document Chunks ({chunks.length})
                </button>
                <button
                  onClick={() => setActiveTab('graph')}
                  className={`py-3 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
                    activeTab === 'graph'
                      ? 'border-cyan-400 text-cyan-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <GitBranch size={14} /> Knowledge Graph ({docEntities.length})
                </button>
              </div>

              {/* Tab Body */}
              <div className="flex-1 p-6 overflow-y-auto">
                {activeTab === 'overview' ? (
                  <div className="flex flex-col gap-6 max-w-4xl">
                    
                    {/* Processing Progress Bar (if processing) */}
                    {['PROCESSING', 'CHUNKING', 'EMBEDDING'].includes(docStatus?.status || activeDoc.status) && (
                      <div className="glass-panel p-4 border-amber-500/20 bg-amber-500/5 flex flex-col gap-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-amber-400 flex items-center gap-2">
                            <RotateCw size={13} className="animate-spin" /> Document Processing In Progress...
                          </span>
                          <span className="font-mono text-amber-300">{docStatus?.progress || 0}%</span>
                        </div>
                        <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                          <div 
                            className="bg-amber-400 h-full transition-all duration-300"
                            style={{ width: `${Math.max(5, docStatus?.progress || 0)}%` }}
                          ></div>
                        </div>
                        <span className="text-[10px] text-slate-400">
                          {docStatus?.processed_chunks || 0} of {docStatus?.total_chunks || 0} chunks embedded via {docStatus?.embedding_model || 'text-embedding-3-small'}
                        </span>
                      </div>
                    )}

                    {/* Processing Error Notice */}
                    {activeDoc.processing_error && (
                      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
                        <AlertCircle size={18} className="text-rose-400 shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-xs font-bold text-rose-400">Extraction Error</h4>
                          <p className="text-xs text-rose-300 mt-1">{activeDoc.processing_error}</p>
                          <button
                            onClick={() => handleProcess(activeDoc.id)}
                            className="mt-3 px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 rounded text-[11px] text-rose-200 font-semibold transition-all cursor-pointer"
                          >
                            Retry Processing
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Metrics Grid */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Document Telemetry
                      </h4>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="glass-panel p-3.5 bg-white/2 border-white/5 rounded-lg">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider block">File Size</span>
                          <span className="text-sm font-bold text-white mt-1 block">{formatBytes(activeDoc.file_size)}</span>
                        </div>
                        <div className="glass-panel p-3.5 bg-white/2 border-white/5 rounded-lg">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Pages / Slides</span>
                          <span className="text-sm font-bold text-white mt-1 block">{activeDoc.page_count || 1}</span>
                        </div>
                        <div className="glass-panel p-3.5 bg-white/2 border-white/5 rounded-lg">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Text Extracted</span>
                          <span className="text-sm font-bold text-white mt-1 block">
                            {activeDoc.extracted_text_length ? `${activeDoc.extracted_text_length} chars` : 'Pending'}
                          </span>
                        </div>
                        <div className="glass-panel p-3.5 bg-white/2 border-white/5 rounded-lg">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Total Chunks</span>
                          <span className="text-sm font-bold text-cyan-400 mt-1 block">{chunks.length}</span>
                        </div>
                      </div>
                    </div>

                    {/* Technical Metadata Table */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Storage & Indexing Specifications
                      </h4>
                      <div className="glass-panel border-white/5 bg-white/2 rounded-lg overflow-hidden">
                        <table className="w-full text-xs text-left border-collapse">
                          <tbody>
                            <tr className="border-b border-white/5 hover:bg-white/1">
                              <td className="py-2.5 px-4 font-semibold text-slate-400 w-1/3">Storage Path</td>
                              <td className="py-2.5 px-4 font-mono text-slate-300 truncate max-w-xs">{activeDoc.storage_path}</td>
                            </tr>
                            <tr className="border-b border-white/5 hover:bg-white/1">
                              <td className="py-2.5 px-4 font-semibold text-slate-400">SHA-256 Checksum</td>
                              <td className="py-2.5 px-4 font-mono text-slate-300 truncate max-w-xs">{activeDoc.checksum}</td>
                            </tr>
                            <tr className="border-b border-white/5 hover:bg-white/1">
                              <td className="py-2.5 px-4 font-semibold text-slate-400">MIME Type</td>
                              <td className="py-2.5 px-4 text-slate-300">{activeDoc.mime_type}</td>
                            </tr>
                            <tr className="border-b border-white/5 hover:bg-white/1">
                              <td className="py-2.5 px-4 font-semibold text-slate-400">Extension</td>
                              <td className="py-2.5 px-4 font-mono text-slate-300">{activeDoc.file_extension || 'N/A'}</td>
                            </tr>
                            <tr className="border-b border-white/5 hover:bg-white/1">
                              <td className="py-2.5 px-4 font-semibold text-slate-400">Embedding Model</td>
                              <td className="py-2.5 px-4 font-mono text-cyan-400">{docStatus?.embedding_model || 'text-embedding-3-small'}</td>
                            </tr>
                            <tr className="border-b border-white/5 hover:bg-white/1">
                              <td className="py-2.5 px-4 font-semibold text-slate-400">Vector Dimensions</td>
                              <td className="py-2.5 px-4 font-mono text-slate-300">1536 (Cosine Similarity)</td>
                            </tr>
                            <tr className="hover:bg-white/1">
                              <td className="py-2.5 px-4 font-semibold text-slate-400">Last Modified</td>
                              <td className="py-2.5 px-4 text-slate-300">{formatDate(activeDoc.updated_at)}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>

                  </div>
                ) : activeTab === 'chunks' ? (
                  /* Chunks Tab */
                  <div className="flex flex-col gap-4 max-w-5xl">
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-slate-400">
                        Inspecting {chunks.length} semantically partitioned chunks ready for cognitive RAG retrieval.
                      </p>
                    </div>

                    {isLoadingChunks ? (
                      <div className="flex flex-col items-center justify-center h-48 text-slate-500 gap-2">
                        <RotateCw size={20} className="animate-spin text-cyan-400" />
                        <span className="text-xs">Loading semantic chunks...</span>
                      </div>
                    ) : chunks.length === 0 ? (
                      <div className="glass-panel p-8 text-center text-slate-500 flex flex-col items-center justify-center">
                        <Layers size={32} className="text-slate-700 mb-2" />
                        <span className="text-xs font-semibold text-slate-400">No Chunks Generated Yet</span>
                        <span className="text-[10px] text-slate-600 mt-1 max-w-sm">
                          Trigger the processing action to extract text and partition this document into embedded vector chunks.
                        </span>
                        {['UPLOADED', 'FAILED'].includes(activeDoc.status) && (
                          <button
                            onClick={() => handleProcess(activeDoc.id)}
                            className="mt-4 px-4 py-1.5 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 rounded-lg text-xs font-semibold text-cyan-300 transition-all cursor-pointer"
                          >
                            Process Document Now
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 gap-3">
                        {chunks.map((chunk) => (
                          <div
                            key={chunk.id}
                            onClick={() => setSelectedChunk(chunk)}
                            className="glass-panel p-4 bg-white/2 hover:bg-white/5 border-white/5 hover:border-cyan-500/30 rounded-lg cursor-pointer transition-all group flex flex-col gap-2"
                          >
                            <div className="flex items-center justify-between text-xs">
                              <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono text-[10px] font-bold">
                                  Chunk #{chunk.chunk_index}
                                </span>
                                {chunk.section_title && (
                                  <span className="text-slate-300 font-semibold">{chunk.section_title}</span>
                                )}
                              </div>
                              <div className="flex items-center gap-3 text-[10px] text-slate-500">
                                {chunk.page_number && <span>Page {chunk.page_number}</span>}
                                <span>{chunk.token_count} tokens</span>
                                <span>{chunk.character_count} chars</span>
                                <ChevronRight size={14} className="text-slate-600 group-hover:text-cyan-400 transition-colors" />
                              </div>
                            </div>
                            <p className="text-xs text-slate-400 line-clamp-2 font-mono bg-black/30 p-2 rounded border border-white/2">
                              {chunk.content}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  /* Knowledge Graph Tab */
                  <div className="flex flex-col gap-6 max-w-5xl">
                    
                    {/* Graph Control Banner */}
                    <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-purple-500/10 border border-purple-500/20">
                      <div>
                        <h4 className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-2">
                          <GitBranch size={15} /> Document Entity & Relationship Graph
                        </h4>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {docEntities.length} entities and {docRelationships.length} relationships mapped for this document.
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleExtractGraph(activeDoc.id)}
                          disabled={isExtractingGraph}
                          className="px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 rounded-lg text-xs font-semibold text-purple-300 transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                        >
                          {isExtractingGraph ? <RotateCw size={13} className="animate-spin" /> : <Sparkles size={13} />}
                          <span>Extract Graph</span>
                        </button>

                        <button
                          onClick={() => handleRebuildGraph(activeDoc.id)}
                          disabled={isRebuildingGraph}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-semibold text-slate-300 transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                        >
                          {isRebuildingGraph ? <RotateCw size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                          <span>Rebuild Graph</span>
                        </button>

                        <button
                          onClick={() => navigate(`/user/knowledge-graph?docId=${activeDoc.id}`)}
                          className="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 rounded-lg text-xs font-bold text-slate-950 transition-all flex items-center gap-1.5 cursor-pointer shadow-lg"
                        >
                          <span>Open Explorer</span>
                          <ExternalLink size={13} />
                        </button>
                      </div>
                    </div>

                    {/* Entities Section */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Extracted Entities ({docEntities.length})
                      </h4>

                      {isLoadingGraph ? (
                        <div className="flex flex-col items-center justify-center h-36 text-slate-500 gap-2">
                          <RotateCw size={18} className="animate-spin text-purple-400" />
                          <span className="text-xs">Loading entities...</span>
                        </div>
                      ) : docEntities.length === 0 ? (
                        <div className="glass-panel p-6 text-center text-slate-500 rounded-xl">
                          <p className="text-xs">No graph entities mapped for this document yet.</p>
                          <button
                            onClick={() => handleExtractGraph(activeDoc.id)}
                            className="mt-3 px-3 py-1.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-lg text-xs font-semibold cursor-pointer"
                          >
                            Extract Entities Now
                          </button>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                          {docEntities.map((ent) => (
                            <div
                              key={ent.id}
                              className="p-3 rounded-lg bg-white/2 border border-white/5 hover:border-purple-500/30 transition-colors"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-white">{ent.name}</span>
                                <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                  {ent.node_type}
                                </span>
                              </div>
                              {ent.description && (
                                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{ent.description}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Relationships Section */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Semantic Relationships ({docRelationships.length})
                      </h4>

                      {docRelationships.length === 0 ? (
                        <p className="text-xs text-slate-500 italic">No direct relationships formed yet.</p>
                      ) : (
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                          {docRelationships.map((rel, idx) => (
                            <div
                              key={rel.id || idx}
                              className="p-2.5 rounded-lg bg-black/40 border border-white/5 text-xs text-slate-300 flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-cyan-300">{rel.source_node_id.slice(0, 8)}...</span>
                                <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-purple-500/20 text-purple-300">
                                  {rel.relationship_type}
                                </span>
                                <span className="font-mono text-cyan-300">{rel.target_node_id.slice(0, 8)}...</span>
                              </div>
                              <span className="text-[10px] text-slate-500 font-mono">
                                Conf: {(rel.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                  </div>
                )}
              </div>
            </React.Fragment>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center text-slate-500 p-8">
              <FileText size={42} className="text-slate-800 mb-3" />
              <h3 className="text-sm font-semibold text-slate-400">No Document Selected</h3>
              <p className="text-xs text-slate-600 mt-1 max-w-sm">
                Select an uploaded document from the registry on the left, or upload a new file to explore its extracted text and vector embeddings.
              </p>
            </div>
          )}
        </div>

      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Modals & Dialogs */}
      {/* ----------------------------------------------------------------- */}

      {/* Chunk Detail Modal */}
      {selectedChunk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-fade-in">
          <div className="glass-panel w-full max-w-2xl max-h-[85vh] bg-[#0c0f17] border-white/10 rounded-xl flex flex-col overflow-hidden shadow-2xl">
            <div className="h-14 border-b border-white/5 px-6 flex items-center justify-between shrink-0 bg-white/2">
              <div className="flex items-center gap-2">
                <FileCode size={16} className="text-cyan-400" />
                <span className="text-xs font-bold text-white">Chunk #{selectedChunk.chunk_index} Inspector</span>
              </div>
              <button 
                onClick={() => setSelectedChunk(null)} 
                className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-white/5 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex flex-col gap-4">
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-2.5 rounded bg-white/2 border border-white/5">
                  <span className="text-[10px] text-slate-500 block">Page / Section</span>
                  <span className="font-semibold text-slate-200">{selectedChunk.page_number ? `Page ${selectedChunk.page_number}` : 'N/A'}</span>
                </div>
                <div className="p-2.5 rounded bg-white/2 border border-white/5">
                  <span className="text-[10px] text-slate-500 block">Token Estimate</span>
                  <span className="font-semibold text-cyan-400">{selectedChunk.token_count} tokens</span>
                </div>
                <div className="p-2.5 rounded bg-white/2 border border-white/5">
                  <span className="text-[10px] text-slate-500 block">Character Length</span>
                  <span className="font-semibold text-slate-200">{selectedChunk.character_count} chars</span>
                </div>
              </div>

              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Raw Chunk Content</span>
                <div className="p-4 rounded-lg bg-black/60 border border-white/5 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap select-text max-h-96 overflow-y-auto">
                  {selectedChunk.content}
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-white/5 bg-white/2 flex justify-end shrink-0">
              <button
                onClick={() => setSelectedChunk(null)}
                className="px-4 py-1.5 bg-white/10 hover:bg-white/15 text-xs font-semibold text-white rounded-lg transition-all cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Action Modal (Delete / Reindex) */}
      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-fade-in">
          <div className="glass-panel w-full max-w-md bg-[#0c0f17] border-white/10 rounded-xl p-6 flex flex-col gap-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                confirmAction.type === 'delete' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'
              }`}>
                {confirmAction.type === 'delete' ? <Trash2 size={20} /> : <RotateCw size={20} />}
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">
                  {confirmAction.type === 'delete' ? 'Confirm Deletion' : 'Confirm Reindexing'}
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  {confirmAction.docName}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {confirmAction.type === 'delete'
                ? 'Are you sure you want to delete this document? All associated vector embeddings and chunk indexes will be permanently removed from storage.'
                : 'Reindexing will erase existing vector chunks and re-run text parsing and embedding generation. This may take a few moments.'}
            </p>

            <div className="flex justify-end gap-3 mt-2">
              <button
                onClick={() => setConfirmAction(null)}
                disabled={isSubmittingAction}
                className="px-4 py-1.5 bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-300 rounded-lg transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (confirmAction.type === 'delete') {
                    handleDelete(confirmAction.docId);
                  } else {
                    handleReindex(confirmAction.docId);
                  }
                }}
                disabled={isSubmittingAction}
                className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer flex items-center gap-2 ${
                  confirmAction.type === 'delete'
                    ? 'bg-rose-600 hover:bg-rose-500 text-white'
                    : 'bg-amber-600 hover:bg-amber-500 text-white'
                }`}
              >
                {isSubmittingAction && <RotateCw size={13} className="animate-spin" />}
                <span>{confirmAction.type === 'delete' ? 'Delete Document' : 'Start Reindex'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
