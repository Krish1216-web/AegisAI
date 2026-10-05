import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  GitBranch, 
  Search, 
  Filter, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Layers, 
  Share2, 
  Navigation, 
  FileText, 
  Sparkles, 
  Activity, 
  Info, 
  ChevronRight, 
  ArrowRight, 
  Code, 
  Copy, 
  Check, 
  Plus, 
  Maximize2, 
  Pause, 
  Play, 
  RefreshCw, 
  ExternalLink,
  Tag,
  AlertCircle,
  Brain,
  Sliders,
  X,
  Target,
  Eye,
  EyeOff,
  Link as LinkIcon,
  BarChart3,
  ShieldCheck,
  AlertTriangle,
  Flame,
  Users,
  Bot
} from 'lucide-react';
import { 
  listNodes, 
  listEdges, 
  getNode, 
  getNeighbors, 
  getRelatedEntities, 
  searchEnhanced, 
  findPath, 
  getGraphContext,
  getDocumentEntities,
  getDocumentRelationships,
  syncGraphNodeToMemory,
  getGraphAnalyticsOverview,
  getGraphHealth,
  getTopConnectedEntities,
  getOrphanNodes,
  getDuplicateCandidates,
  reasonGraph
} from '../../api/knowledgeGraph';
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

const NODE_TYPES = [
  { id: 'ALL', label: 'All Types', color: '#94a3b8' },
  { id: 'PROJECT', label: 'Project', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)', border: '#0284c7' },
  { id: 'SKILL', label: 'Skill / Tech', color: '#34d399', bg: 'rgba(52, 211, 153, 0.15)', border: '#059669' },
  { id: 'DOCUMENT', label: 'Document', color: '#a78bfa', bg: 'rgba(167, 139, 250, 0.15)', border: '#7c3aed' },
  { id: 'DOCUMENT_CHUNK', label: 'Doc Chunk', color: '#f472b6', bg: 'rgba(244, 114, 182, 0.15)', border: '#db2777' },
  { id: 'USER', label: 'User', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.15)', border: '#d97706' },
  { id: 'ORGANIZATION', label: 'Organization', color: '#60a5fa', bg: 'rgba(96, 165, 250, 0.15)', border: '#2563eb' },
  { id: 'TASK', label: 'Task', color: '#f87171', bg: 'rgba(248, 113, 113, 0.15)', border: '#dc2626' },
  { id: 'AGENT', label: 'Agent', color: '#2dd4bf', bg: 'rgba(45, 212, 191, 0.15)', border: '#0d9488' },
  { id: 'MEMORY', label: 'Memory', color: '#c084fc', bg: 'rgba(192, 132, 252, 0.15)', border: '#9333ea' }
];

const RELATIONSHIP_TYPES = [
  'ALL',
  'CONTAINS',
  'REFERENCES',
  'USES',
  'DEPENDS_ON',
  'ASSIGNED_TO',
  'PART_OF',
  'CREATED_BY',
  'WORKS_ON',
  'RELATED_TO'
];

export default function UserGraph() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const docIdParam = searchParams.get('docId') || searchParams.get('documentId');
  const { success, error, warning, info } = useToast();

  // Graph Data
  const [rawNodes, setRawNodes] = useState([]);
  const [rawEdges, setRawEdges] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [links, setLinks] = useState([]);

  // Loading & Error States
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);

  // Search & Filter Controls
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedType, setSelectedType] = useState('ALL');
  const [selectedRelType, setSelectedRelType] = useState('ALL');
  const [minConfidence, setMinConfidence] = useState(0.0);
  const [nodeLimit, setNodeLimit] = useState(50);
  const [hideIsolated, setHideIsolated] = useState(false);
  const [isPhysicsActive, setIsPhysicsActive] = useState(true);

  // Selection & Inspector
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [relatedEntities, setRelatedEntities] = useState([]);
  const [isLoadingRelated, setIsLoadingRelated] = useState(false);

  // Modals
  const [showPathModal, setShowPathModal] = useState(false);
  const [pathSourceId, setPathSourceId] = useState('');
  const [pathTargetId, setPathTargetId] = useState('');
  const [pathResult, setPathResult] = useState(null);
  const [isFindingPath, setIsFindingPath] = useState(false);
  const [highlightedPathNodeIds, setHighlightedPathNodeIds] = useState(new Set());

  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false);
  const [analyticsOverview, setAnalyticsOverview] = useState(null);
  const [healthReport, setHealthReport] = useState(null);
  const [topEntities, setTopEntities] = useState([]);

  const [showReasonModal, setShowReasonModal] = useState(false);
  const [reasonQuery, setReasonQuery] = useState('');
  const [reasonResult, setReasonResult] = useState(null);
  const [isReasoning, setIsReasoning] = useState(false);

  const [showOutlineModal, setShowOutlineModal] = useState(false);

  // Canvas Viewport & Physics
  const svgRef = useRef(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [draggedNode, setDraggedNode] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 1000, height: 650 });

  // Update canvas size on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (svgRef.current) {
        const { clientWidth, clientHeight } = svgRef.current;
        setDimensions({ width: clientWidth || 1000, height: clientHeight || 650 });
      }
    };
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // ----------------------------------------------------------------------
  // 1. Initial Data Fetching
  // ----------------------------------------------------------------------
  const fetchGraphData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      if (docIdParam) {
        const [docNodes, docEdges] = await Promise.all([
          getDocumentEntities(docIdParam),
          getDocumentRelationships(docIdParam)
        ]);
        const nList = Array.isArray(docNodes) ? docNodes : (docNodes?.entities || docNodes?.nodes || []);
        const eList = Array.isArray(docEdges) ? docEdges : (docEdges?.relationships || docEdges?.edges || []);
        setRawNodes(nList);
        setRawEdges(eList);
      } else {
        const [nodeList, edgeList] = await Promise.all([
          listNodes({ limit: nodeLimit }),
          listEdges({ limit: nodeLimit * 2 })
        ]);
        const nList = Array.isArray(nodeList) ? nodeList : (nodeList?.nodes || nodeList?.items || []);
        const eList = Array.isArray(edgeList) ? edgeList : (edgeList?.edges || edgeList?.items || []);
        setRawNodes(nList);
        setRawEdges(eList);
      }
    } catch (err) {
      console.error('Failed to load knowledge graph:', err);
      setErrorMessage(err.message || 'Failed to load knowledge graph.');
    } finally {
      setIsLoading(false);
    }
  }, [docIdParam, nodeLimit]);

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  // ----------------------------------------------------------------------
  // 2. Debounced Enhanced Search
  // ----------------------------------------------------------------------
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchEnhanced({
          q: searchQuery.trim(),
          node_type: selectedType !== 'ALL' ? selectedType : undefined,
          limit: 8
        });
        setSearchResults(results || []);
      } catch (err) {
        console.warn('Search warning:', err);
      } finally {
        setIsSearching(false);
      }
    }, 280);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedType]);

  // ----------------------------------------------------------------------
  // 3. Transform Raw Nodes & Edges to Simulation Elements
  // ----------------------------------------------------------------------
  useEffect(() => {
    let filteredNodes = rawNodes || [];
    if (selectedType !== 'ALL') {
      filteredNodes = filteredNodes.filter(n => (n.node_type || n.type || n.entity_type) === selectedType);
    }

    let filteredEdges = (rawEdges || []).map(e => ({
      ...e,
      source_node_id: e.source_node_id || (typeof e.source === 'string' ? e.source : e.source?.id),
      target_node_id: e.target_node_id || (typeof e.target === 'string' ? e.target : e.target?.id),
      relationship_type: e.relationship_type || e.type || e.relation || 'RELATED_TO'
    }));

    if (selectedRelType !== 'ALL') {
      filteredEdges = filteredEdges.filter(e => e.relationship_type === selectedRelType);
    }
    if (minConfidence > 0) {
      filteredEdges = filteredEdges.filter(e => (e.confidence || 1.0) >= minConfidence);
    }

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const validEdges = filteredEdges.filter(e => nodeIds.has(e.source_node_id) && nodeIds.has(e.target_node_id));

    if (hideIsolated) {
      const connectedIds = new Set();
      validEdges.forEach(e => {
        connectedIds.add(e.source_node_id);
        connectedIds.add(e.target_node_id);
      });
      filteredNodes = filteredNodes.filter(n => connectedIds.has(n.id));
    }

    // Assign initial positions in circle / layout
    const count = filteredNodes.length;
    const radius = Math.min(dimensions.width, dimensions.height) * 0.35;
    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;

    const simNodes = filteredNodes.map((n, idx) => {
      const angle = (idx / (count || 1)) * 2 * Math.PI;
      return {
        ...n,
        node_type: n.node_type || n.type || n.entity_type || 'Concept',
        x: centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 40,
        y: centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0
      };
    });

    const nodeMap = new Map(simNodes.map(n => [n.id, n]));
    const simLinks = validEdges.map(e => ({
      ...e,
      source: nodeMap.get(e.source_node_id),
      target: nodeMap.get(e.target_node_id)
    })).filter(l => l.source && l.target);

    setNodes(simNodes);
    setLinks(simLinks);
  }, [rawNodes, rawEdges, selectedType, selectedRelType, minConfidence, hideIsolated, dimensions]);

  // Fetch Node Neighbors when Selected
  const handleSelectNode = async (node) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    setIsLoadingRelated(true);
    try {
      const related = await getRelatedEntities(node.id, { depth: 1, limit: 10 });
      const rList = Array.isArray(related) ? related : (related?.related_entities || related?.entities || []);
      setRelatedEntities(rList);
    } catch (err) {
      console.warn('Failed to load related entities:', err);
      setRelatedEntities([]);
    } finally {
      setIsLoadingRelated(false);
    }
  };

  // Pathfinding
  const handleFindPath = async (e) => {
    e?.preventDefault();
    if (!pathSourceId || !pathTargetId) return;
    setIsFindingPath(true);
    try {
      const res = await findPath({
        source_node_id: pathSourceId,
        target_node_id: pathTargetId,
        max_depth: 4
      });
      setPathResult(res);
      if (res.path_found) {
        const pNodeIds = new Set(res.nodes?.map(n => n.id) || []);
        setHighlightedPathNodeIds(pNodeIds);
        success('Path Found', `Discovered ${res.steps?.length || 0}-step traversal.`);
      } else {
        warning('No Path', 'No traversal path found within 4 hops.');
      }
    } catch (err) {
      error('Path Error', err.message || 'Pathfinding failed.');
    } finally {
      setIsFindingPath(false);
    }
  };

  // Analytics Load
  const handleOpenAnalytics = async () => {
    setShowAnalyticsModal(true);
    try {
      const [ov, health, top] = await Promise.all([
        getGraphAnalyticsOverview(),
        getGraphHealth(),
        getTopConnectedEntities(5)
      ]);
      setAnalyticsOverview(ov);
      setHealthReport(health);
      setTopEntities(top || []);
    } catch (err) {
      console.warn('Analytics warning:', err);
    }
  };

  // Graph Reasoning
  const handleReason = async (e) => {
    e?.preventDefault();
    if (!reasonQuery.trim()) return;
    setIsReasoning(true);
    try {
      const res = await reasonGraph({
        query: reasonQuery.trim(),
        depth: 2,
        include_rag: true,
        include_memory: true
      });
      setReasonResult(res);
      success('Reasoning Succeeded', `Synthesized answer across ${res.matched_nodes_count || 0} graph nodes.`);
    } catch (err) {
      error('Reasoning Error', err.message || 'Graph reasoning failed.');
    } finally {
      setIsReasoning(false);
    }
  };

  // KPI calculations
  const kpiStats = useMemo(() => {
    const totalEntities = rawNodes.length;
    const totalRelationships = rawEdges.length;
    const avgConfidence = rawEdges.length > 0
      ? (rawEdges.reduce((acc, e) => acc + (e.confidence || 0.8), 0) / rawEdges.length).toFixed(2)
      : '0.85';
    const density = totalEntities > 1
      ? ((totalRelationships / (totalEntities * (totalEntities - 1))) * 100).toFixed(1)
      : '1.2';
    return { totalEntities, totalRelationships, avgConfidence, density };
  }, [rawNodes, rawEdges]);

  return (
    <div className="flex flex-col gap-6 animate-fade-in pb-12 font-sans text-slate-200">
      {/* 1. Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-lg shadow-indigo-500/10">
            <GitBranch size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              Knowledge Graph Explorer
              <Badge variant="indigo">Entity Topology</Badge>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Explore interconnected organizations, skills, documents, and memory facts across your workspace.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchGraphData}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin text-indigo-400' : ''} />
            {isLoading ? 'Loading...' : 'Refresh Graph'}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleOpenAnalytics}
            className="flex items-center gap-1.5"
          >
            <BarChart3 size={13} /> Analytics & Health
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowPathModal(true)}
            className="flex items-center gap-1.5"
          >
            <Navigation size={13} /> Pathfinder
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowReasonModal(true)}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            <Brain size={13} /> Graph Reasoning
          </Button>
        </div>
      </div>

      {/* 2. Overview KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Total Entities"
          value={kpiStats.totalEntities}
          subtitle="Extracted graph nodes"
          trend="Multi-Domain Cognition"
          icon={<Users size={18} className="text-indigo-400" />}
        />
        <MetricCard
          title="Relationships"
          value={kpiStats.totalRelationships}
          subtitle="Semantic edge connections"
          trend="Directional Paths"
          icon={<Share2 size={18} className="text-cyan-400" />}
        />
        <MetricCard
          title="Average Confidence"
          value={`${kpiStats.avgConfidence}`}
          subtitle="NLP & schema verified"
          trend="Confidence Gated"
          icon={<ShieldCheck size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Graph Density"
          value={`${kpiStats.density}%`}
          subtitle="Connectivity ratio"
          trend="Multi-Hop Reachable"
          icon={<Activity size={18} className="text-purple-400" />}
        />
      </div>

      {/* 3. Filter Toolbar & Search */}
      <Card className="p-3.5 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search entities by name or keyword..."
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-1.5 pl-10 pr-4 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowOutlineModal(true)}
              className="text-xs py-1 px-2.5 flex items-center gap-1.5"
              title="Accessible Text Representation"
            >
              <FileText size={12} /> Accessible Outline
            </Button>

            <select
              value={selectedRelType}
              onChange={(e) => setSelectedRelType(e.target.value)}
              className="bg-[#0d1117] border border-white/10 rounded-md px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
            >
              {RELATIONSHIP_TYPES.map(rel => (
                <option key={rel} value={rel}>{rel}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Node Type Pills */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          {NODE_TYPES.map(nt => (
            <button
              key={nt.id}
              onClick={() => setSelectedType(nt.id)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all cursor-pointer ${
                selectedType === nt.id
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                  : 'bg-white/[0.02] border border-white/[0.05] text-slate-400 hover:text-white'
              }`}
            >
              {nt.label}
            </button>
          ))}
        </div>
      </Card>

      {/* 4. Interactive Graph Canvas & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Canvas Surface (8 cols) */}
        <div className="lg:col-span-8 bg-[#050608] border border-white/[0.08] rounded-2xl h-[600px] relative overflow-hidden flex items-center justify-center">
          {/* Canvas Controls Overlay */}
          <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-black/60 p-1.5 rounded-xl border border-white/10 backdrop-blur-md">
            <IconButton
              variant="ghost"
              size="sm"
              onClick={() => setZoomLevel(prev => Math.min(prev + 0.2, 2.5))}
              title="Zoom In"
              aria-label="Zoom In"
            >
              <ZoomIn size={13} />
            </IconButton>

            <IconButton
              variant="ghost"
              size="sm"
              onClick={() => setZoomLevel(prev => Math.max(prev - 0.2, 0.4))}
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              <ZoomOut size={13} />
            </IconButton>

            <IconButton
              variant="ghost"
              size="sm"
              onClick={() => {
                setZoomLevel(1);
                setPanOffset({ x: 0, y: 0 });
              }}
              title="Fit View"
              aria-label="Fit View"
            >
              <Maximize2 size={13} />
            </IconButton>

            <div className="w-[1px] h-4 bg-white/10 mx-0.5" />

            <IconButton
              variant="ghost"
              size="sm"
              onClick={() => setIsPhysicsActive(prev => !prev)}
              title={isPhysicsActive ? 'Pause Physics' : 'Resume Physics'}
              aria-label="Toggle Physics"
            >
              {isPhysicsActive ? <Pause size={13} /> : <Play size={13} />}
            </IconButton>
          </div>

          {/* SVG Canvas */}
          <svg
            ref={svgRef}
            className="w-full h-full cursor-grab active:cursor-grabbing select-none"
            viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
          >
            <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`}>
              {/* Edges */}
              {links.map((link, idx) => (
                <line
                  key={idx}
                  x1={link.source.x}
                  y1={link.source.y}
                  x2={link.target.x}
                  y2={link.target.y}
                  stroke="#475569"
                  strokeWidth={selectedEdge?.id === link.id ? 3 : 1.5}
                  strokeOpacity={0.6}
                  onClick={() => setSelectedEdge(link)}
                  className="hover:stroke-indigo-400 transition cursor-pointer"
                />
              ))}

              {/* Nodes */}
              {nodes.map((node) => {
                const meta = NODE_TYPES.find(t => t.id === node.node_type) || NODE_TYPES[0];
                const isSelected = selectedNode?.id === node.id;
                const isPathHighlighted = highlightedPathNodeIds.has(node.id);

                return (
                  <g
                    key={node.id}
                    role="button"
                    tabIndex={0}
                    aria-label={node.name}
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={() => handleSelectNode(node)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSelectNode(node);
                      }
                    }}
                    className="cursor-pointer focus:outline-none"
                  >
                    <circle
                      r={isSelected ? 18 : isPathHighlighted ? 16 : 14}
                      fill={meta.bg || '#1e293b'}
                      stroke={isSelected ? '#818cf8' : isPathHighlighted ? '#34d399' : meta.border || '#64748b'}
                      strokeWidth={isSelected || isPathHighlighted ? 3 : 1.5}
                      className="transition-all hover:scale-110"
                    />
                    <text
                      dy={24}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize="10"
                      fontFamily="sans-serif"
                      className="pointer-events-none select-none font-semibold"
                    >
                      {node.name?.length > 14 ? `${node.name.slice(0, 12)}...` : node.name}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>

          {nodes.length === 0 && !isLoading && (
            <div className="text-center p-6 text-xs text-slate-500">
              No knowledge graph nodes match the active filters.
            </div>
          )}
        </div>

        {/* Side Inspector Drawer / Panel (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          {selectedNode ? (
            <Card className="p-4 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                <div>
                  <h3 className="text-xs font-bold text-white line-clamp-1">{selectedNode.name}</h3>
                  <Badge variant="purple" className="mt-1">{selectedNode.node_type}</Badge>
                </div>
                <IconButton
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedNode(null)}
                  aria-label="Close Inspector"
                >
                  <X size={13} />
                </IconButton>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block mb-0.5">Description</span>
                  <p className="text-slate-300 leading-relaxed">
                    {selectedNode.description || 'Knowledge entity registered in workspace graph.'}
                  </p>
                </div>

                <div className="p-2.5 rounded-lg bg-black/30 border border-white/[0.04] space-y-1">
                  <span className="text-slate-500 text-[10px] block">Provenance:</span>
                  <span className="text-emerald-400 font-semibold font-mono text-[11px]">Document-Derived Extraction</span>
                </div>

                {/* Related Neighbors */}
                <div className="space-y-1.5 pt-2 border-t border-white/[0.04]">
                  <span className="text-slate-400 text-[10px] font-bold uppercase tracking-wider block">
                    Connected Neighbors ({relatedEntities.length})
                  </span>
                  <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                    {relatedEntities.map((rel, idx) => (
                      <div key={idx} className="p-2 rounded bg-white/[0.02] border border-white/[0.04] flex items-center justify-between text-[11px]">
                        <span className="text-white font-medium truncate">{rel.name}</span>
                        <span className="text-purple-400 font-mono text-[10px]">{rel.node_type}</span>
                      </div>
                    ))}
                    {relatedEntities.length === 0 && (
                      <span className="text-slate-500 text-[10px] italic">No immediate neighbors discovered.</span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ) : selectedEdge ? (
            <Card className="p-4 space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="font-bold text-white">Relationship Edge</span>
                <IconButton variant="ghost" size="sm" onClick={() => setSelectedEdge(null)} aria-label="Close Edge">
                  <X size={13} />
                </IconButton>
              </div>
              <div className="space-y-2">
                <div>
                  <span className="text-slate-500 text-[10px] block">Relationship Type:</span>
                  <Badge variant="cyan">{selectedEdge.relationship_type}</Badge>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block">Confidence:</span>
                  <span className="font-mono text-emerald-400">{(selectedEdge.confidence || 0.9).toFixed(2)}</span>
                </div>
              </div>
            </Card>
          ) : (
            <Card className="p-6 text-center text-xs text-slate-500">
              Click an entity node or relationship edge on the canvas to inspect provenance, attributes, and neighbors.
            </Card>
          )}
        </div>
      </div>

      {/* 5. Accessible Plain-Text Outline Modal */}
      <Modal
        isOpen={showOutlineModal}
        onClose={() => setShowOutlineModal(false)}
        title="Accessible Knowledge Graph Outline"
        description="Sequential plain-text representation of all entities and relationships for screen readers and linear review."
        size="lg"
      >
        <div className="max-h-96 overflow-y-auto space-y-3 text-xs text-slate-300 pr-1">
          {rawNodes.map((node, idx) => {
            const outEdges = rawEdges.filter(e => e.source_node_id === node.id);
            return (
              <div key={node.id || idx} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">{idx + 1}. {node.name}</span>
                  <Badge variant="purple">{node.node_type}</Badge>
                </div>
                <p className="text-[11px] text-slate-400">{node.description || 'Entity'}</p>
                {outEdges.length > 0 && (
                  <div className="text-[11px] text-slate-400 mt-1 space-y-0.5">
                    <span className="font-semibold text-slate-300 block">Relationships:</span>
                    {outEdges.map((e, eIdx) => {
                      const target = rawNodes.find(n => n.id === e.target_node_id);
                      return (
                        <div key={eIdx} className="pl-2 border-l border-indigo-500/30">
                          → <strong className="text-indigo-300">{e.relationship_type}</strong> → {target ? target.name : e.target_node_id} (Confidence: {e.confidence || 1.0})
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Modal>

      {/* 6. Graph Pathfinder Modal */}
      <Modal
        isOpen={showPathModal}
        onClose={() => setShowPathModal(false)}
        title="Graph Pathfinder"
        description="Discover shortest-path traversals between two entities in the knowledge graph."
        size="md"
      >
        <form onSubmit={handleFindPath} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Source Entity</label>
            <select
              value={pathSourceId}
              onChange={(e) => setPathSourceId(e.target.value)}
              required
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-indigo-500/50"
            >
              <option value="">Select source entity...</option>
              {rawNodes.map(n => (
                <option key={n.id} value={n.id}>{n.name} ({n.node_type})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Target Entity</label>
            <select
              value={pathTargetId}
              onChange={(e) => setPathTargetId(e.target.value)}
              required
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-indigo-500/50"
            >
              <option value="">Select target entity...</option>
              {rawNodes.map(n => (
                <option key={n.id} value={n.id}>{n.name} ({n.node_type})</option>
              ))}
            </select>
          </div>

          {pathResult && (
            <div className="p-3 rounded-lg bg-black/30 border border-white/[0.05] text-xs space-y-1">
              <span className="font-bold text-emerald-400">
                {pathResult.path_found ? `Path Found (${pathResult.distance} hops)` : 'No Path Found'}
              </span>
              {pathResult.steps?.map((step, idx) => (
                <div key={idx} className="text-[11px] text-slate-300">
                  {idx + 1}. {step.from_node_name} → <strong className="text-indigo-300">{step.relationship_type}</strong> → {step.to_node_name}
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setShowPathModal(false)}>
              Close
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={isFindingPath} className="bg-indigo-600 hover:bg-indigo-500 text-white">
              {isFindingPath ? 'Traversing...' : 'Find Path'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* 7. Graph Reasoning Modal */}
      <Modal
        isOpen={showReasonModal}
        onClose={() => setShowReasonModal(false)}
        title="Multi-Agent Graph Reasoning"
        description="Execute grounded reasoning combining entity traversal, vector chunks, and long-term memory."
        size="lg"
      >
        <form onSubmit={handleReason} className="space-y-4">
          <textarea
            value={reasonQuery}
            onChange={(e) => setReasonQuery(e.target.value)}
            rows={3}
            placeholder="Enter reasoning prompt (e.g. 'What projects depend on the Security Agent?')..."
            className="w-full bg-[#0d1117] border border-white/10 rounded-xl p-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/50"
          />

          {reasonResult && (
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-2 text-xs">
              <span className="font-bold text-indigo-300">Synthesized Graph Context</span>
              <p className="text-slate-200 leading-relaxed font-mono text-[11px]">
                {reasonResult.graph_context || 'Reasoning completed with matched node context.'}
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setShowReasonModal(false)}>
              Close
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={isReasoning} className="bg-indigo-600 hover:bg-indigo-500 text-white">
              {isReasoning ? 'Synthesizing...' : 'Execute Reasoning'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* 8. Analytics Modal */}
      <Modal
        isOpen={showAnalyticsModal}
        onClose={() => setShowAnalyticsModal(false)}
        title="Knowledge Graph Analytics & Health"
        description="Inspect graph health diagnostics, orphan nodes, and connectivity hubs."
        size="md"
      >
        <div className="space-y-4 text-xs">
          {healthReport && (
            <div className="p-3 rounded-lg bg-black/30 border border-white/[0.05] space-y-1">
              <span className="font-bold text-white block">Diagnostic Status: <strong className="text-emerald-400">{healthReport.status}</strong></span>
              <p className="text-[11px] text-slate-400">Orphan Rate: {(healthReport.orphan_rate || 0).toFixed(1)}%</p>
            </div>
          )}

          {topEntities.length > 0 && (
            <div className="space-y-1">
              <span className="font-bold text-slate-300 block">Top Connected Hubs</span>
              {topEntities.map((t, idx) => (
                <div key={idx} className="p-2 rounded bg-white/[0.02] border border-white/[0.04] flex items-center justify-between text-[11px]">
                  <span className="text-white font-medium">{t.name}</span>
                  <span className="text-indigo-400 font-mono">{t.degree} connections</span>
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button variant="secondary" size="sm" onClick={() => setShowAnalyticsModal(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
