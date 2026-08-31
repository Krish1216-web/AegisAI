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

  // Graph Data
  const [rawNodes, setRawNodes] = useState([]);
  const [rawEdges, setRawEdges] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [links, setLinks] = useState([]);

  // Loading & Error States
  const [isLoading, setIsLoading] = useState(true);
  const [isExpanding, setIsExpanding] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

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
  const [hoveredNode, setHoveredNode] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [relatedEntities, setRelatedEntities] = useState([]);
  const [isLoadingRelated, setIsLoadingRelated] = useState(false);

  // Pathfinding Modal & Highlight
  const [showPathModal, setShowPathModal] = useState(false);
  const [pathSourceId, setPathSourceId] = useState('');
  const [pathTargetId, setPathTargetId] = useState('');
  const [pathResult, setPathResult] = useState(null);
  const [isFindingPath, setIsFindingPath] = useState(false);
  const [highlightedPathNodeIds, setHighlightedPathNodeIds] = useState(new Set());
  const [highlightedPathEdgeKeys, setHighlightedPathEdgeKeys] = useState(new Set());

  // Graph Context Modal
  const [showContextModal, setShowContextModal] = useState(false);
  const [graphContextText, setGraphContextText] = useState('');
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [copiedContext, setCopiedContext] = useState(false);

  // Analytics Drawer / Modal
  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false);
  const [analyticsOverview, setAnalyticsOverview] = useState(null);
  const [healthReport, setHealthReport] = useState(null);
  const [topEntities, setTopEntities] = useState([]);
  const [orphanList, setOrphanList] = useState([]);
  const [duplicateList, setDuplicateList] = useState([]);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);

  // Multi-Agent Graph Reasoning Modal
  const [showReasonModal, setShowReasonModal] = useState(false);
  const [reasonQuery, setReasonQuery] = useState('');
  const [reasonDepth, setReasonDepth] = useState(2);
  const [reasonResult, setReasonResult] = useState(null);
  const [isReasoning, setIsReasoning] = useState(false);

  // Canvas Viewport & Physics
  const svgRef = useRef(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [draggedNode, setDraggedNode] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 1000, height: 650 });

  // Update canvas size on window resize
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

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

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
        setRawNodes(docNodes || []);
        setRawEdges(docEdges || []);
      } else {
        const [nodeList, edgeList] = await Promise.all([
          listNodes({ limit: nodeLimit }),
          listEdges({ limit: nodeLimit * 2 })
        ]);
        setRawNodes(nodeList || []);
        setRawEdges(edgeList || []);
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
          query: searchQuery.trim(),
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
    let filteredNodes = rawNodes;
    if (selectedType !== 'ALL') {
      filteredNodes = rawNodes.filter(n => n.node_type === selectedType);
    }

    const nodeIdsWithEdges = new Set();
    rawEdges.forEach(e => {
      if (e.confidence >= minConfidence) {
        nodeIdsWithEdges.add(e.source_node_id);
        nodeIdsWithEdges.add(e.target_node_id);
      }
    });

    if (hideIsolated) {
      filteredNodes = filteredNodes.filter(n => nodeIdsWithEdges.has(n.id));
    }

    const validNodeIds = new Set(filteredNodes.map(n => n.id));

    let filteredEdges = rawEdges.filter(e => 
      validNodeIds.has(e.source_node_id) && 
      validNodeIds.has(e.target_node_id) &&
      e.confidence >= minConfidence
    );

    if (selectedRelType !== 'ALL') {
      filteredEdges = filteredEdges.filter(e => e.relationship_type === selectedRelType);
    }

    // Preserve existing node positions across simulation updates
    const prevPosMap = new Map(nodes.map(n => [n.id, { x: n.x, y: n.y, vx: n.vx, vy: n.vy }]));
    const cx = dimensions.width / 2;
    const cy = dimensions.height / 2;

    const simNodes = filteredNodes.map((n, i) => {
      const prev = prevPosMap.get(n.id);
      const angle = (i / (filteredNodes.length || 1)) * 2 * Math.PI;
      const radius = 130 + (i % 3) * 60;
      return {
        ...n,
        x: prev ? prev.x : cx + radius * Math.cos(angle) + (Math.random() - 0.5) * 40,
        y: prev ? prev.y : cy + radius * Math.sin(angle) + (Math.random() - 0.5) * 40,
        vx: prev ? prev.vx : 0,
        vy: prev ? prev.vy : 0
      };
    });

    const simLinks = filteredEdges.map(e => ({
      ...e,
      source: e.source_node_id,
      target: e.target_node_id
    }));

    setNodes(simNodes);
    setLinks(simLinks);
  }, [rawNodes, rawEdges, selectedType, selectedRelType, minConfidence, hideIsolated, dimensions]);

  // ----------------------------------------------------------------------
  // 4. Force Physics Simulation Loop
  // ----------------------------------------------------------------------
  useEffect(() => {
    if (!isPhysicsActive || nodes.length === 0) return;

    let frameId;
    const tick = () => {
      setNodes(prevNodes => {
        const nextNodes = prevNodes.map(n => ({ ...n, vx: (n.vx || 0) * 0.86, vy: (n.vy || 0) * 0.86 }));
        const cx = dimensions.width / 2;
        const cy = dimensions.height / 2;

        // Node repulsion
        for (let i = 0; i < nextNodes.length; i++) {
          const nodeA = nextNodes[i];
          for (let j = i + 1; j < nextNodes.length; j++) {
            const nodeB = nextNodes[j];
            const dx = nodeB.x - nodeA.x;
            const dy = nodeB.y - nodeA.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const minDist = 145;

            if (dist < minDist) {
              const force = (minDist - dist) / dist * 0.15;
              const fx = dx * force;
              const fy = dy * force;

              if (nodeA.id !== draggedNode?.id) { nodeA.vx -= fx; nodeA.vy -= fy; }
              if (nodeB.id !== draggedNode?.id) { nodeB.vx += fx; nodeB.vy += fy; }
            }
          }

          // Center gravity
          if (nodeA.id !== draggedNode?.id) {
            nodeA.vx += (cx - nodeA.x) * 0.003;
            nodeA.vy += (cy - nodeA.y) * 0.003;
          }
        }

        // Link spring attraction
        const nodeMap = new Map(nextNodes.map(n => [n.id, n]));
        for (const link of links) {
          const src = nodeMap.get(link.source);
          const tgt = nodeMap.get(link.target);
          if (src && tgt) {
            const dx = tgt.x - src.x;
            const dy = tgt.y - src.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const targetDist = 120;
            const force = (dist - targetDist) * 0.035;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (src.id !== draggedNode?.id) { src.vx += fx; src.vy += fy; }
            if (tgt.id !== draggedNode?.id) { tgt.vx -= fx; tgt.vy -= fy; }
          }
        }

        // Apply velocities & boundary limits
        return nextNodes.map(n => {
          if (n.id === draggedNode?.id) return n;
          const nextX = Math.max(50, Math.min(dimensions.width - 50, n.x + n.vx));
          const nextY = Math.max(50, Math.min(dimensions.height - 50, n.y + n.vy));
          return { ...n, x: nextX, y: nextY };
        });
      });

      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [isPhysicsActive, links, draggedNode, dimensions]);

  // ----------------------------------------------------------------------
  // 5. Canvas Navigation & Drag Interactions
  // ----------------------------------------------------------------------
  const handleZoom = (delta) => {
    setZoomLevel(prev => Math.min(3.0, Math.max(0.25, prev + delta)));
  };

  const handleResetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  const handleCenterGraph = () => {
    if (nodes.length === 0) return;
    const avgX = nodes.reduce((acc, n) => acc + n.x, 0) / nodes.length;
    const avgY = nodes.reduce((acc, n) => acc + n.y, 0) / nodes.length;
    setPanOffset({
      x: dimensions.width / 2 - avgX * zoomLevel,
      y: dimensions.height / 2 - avgY * zoomLevel
    });
  };

  const handleMouseDownSvg = (e) => {
    if (e.target.tagName === 'svg' || e.target.id === 'graph-bg') {
      setIsPanning(true);
      setPanStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMoveSvg = (e) => {
    if (isPanning) {
      setPanOffset({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    } else if (draggedNode) {
      const rect = svgRef.current.getBoundingClientRect();
      const rawX = (e.clientX - rect.left - panOffset.x) / zoomLevel;
      const rawY = (e.clientY - rect.top - panOffset.y) / zoomLevel;
      setNodes(prev => prev.map(n => n.id === draggedNode.id ? { ...n, x: rawX, y: rawY, vx: 0, vy: 0 } : n));
    }
  };

  const handleMouseUpSvg = () => {
    setIsPanning(false);
    setDraggedNode(null);
  };

  // Focus and select node
  const handleSelectNode = async (node) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    setIsLoadingRelated(true);
    try {
      const related = await getRelatedEntities(node.id, { depth: 2, max_entities: 6 });
      setRelatedEntities(related?.related_entities || []);
    } catch (err) {
      console.warn('Failed to load related entities:', err);
    } finally {
      setIsLoadingRelated(false);
    }
  };

  // Expand node neighbors dynamically
  const handleExpandNeighbors = async (node) => {
    if (!node) return;
    setIsExpanding(true);
    try {
      const res = await getNeighbors(node.id);
      const neighborItems = res?.neighbors || [];
      const newNodesMap = new Map(rawNodes.map(n => [n.id, n]));
      const newEdgesMap = new Map(rawEdges.map(e => [e.id, e]));

      neighborItems.forEach(item => {
        if (!newNodesMap.has(item.node.id)) {
          newNodesMap.set(item.node.id, item.node);
        }
        if (!newEdgesMap.has(item.edge_id)) {
          newEdgesMap.set(item.edge_id, {
            id: item.edge_id,
            source_node_id: item.direction === 'outgoing' ? node.id : item.node.id,
            target_node_id: item.direction === 'outgoing' ? item.node.id : node.id,
            relationship_type: item.relationship_type,
            confidence: item.confidence,
            properties: {}
          });
        }
      });

      setRawNodes(Array.from(newNodesMap.values()));
      setRawEdges(Array.from(newEdgesMap.values()));
      showToast(`Expanded ${neighborItems.length} neighbors for ${node.name}`);
    } catch (err) {
      console.error('Failed to expand neighbors:', err);
      showToast('Error expanding neighbors');
    } finally {
      setIsExpanding(false);
    }
  };

  // Sync Graph Node into Agent Memory
  const handleSyncNodeToMemory = async (node) => {
    if (!node) return;
    try {
      const res = await syncGraphNodeToMemory(node.id);
      showToast(`Synced ${node.name} into Agent Memory`);
    } catch (err) {
      console.error('Failed to sync node to memory:', err);
      showToast(err.message || 'Failed to sync node to memory');
    }
  };

  // Pathfinding execution
  const handleFindPath = async () => {
    if (!pathSourceId || !pathTargetId) return;
    setIsFindingPath(true);
    setPathResult(null);
    try {
      const res = await findPath({
        source_node_id: pathSourceId,
        target_node_id: pathTargetId,
        max_depth: 5
      });
      setPathResult(res);

      if (res.path_found && res.steps) {
        const nodeIds = new Set();
        const edgeKeys = new Set();
        res.steps.forEach(s => {
          nodeIds.add(s.from_node_id);
          nodeIds.add(s.to_node_id);
          edgeKeys.add(`${s.from_node_id}->${s.to_node_id}`);
          edgeKeys.add(`${s.to_node_id}->${s.from_node_id}`);
        });
        setHighlightedPathNodeIds(nodeIds);
        setHighlightedPathEdgeKeys(edgeKeys);
      }
    } catch (err) {
      console.error('Path finding error:', err);
      setPathResult({ path_found: false, error: err.message });
    } finally {
      setIsFindingPath(false);
    }
  };

  const handleClearPath = () => {
    setPathResult(null);
    setHighlightedPathNodeIds(new Set());
    setHighlightedPathEdgeKeys(new Set());
  };

  // Graph context retrieval
  const handleGenerateContext = async (node) => {
    setIsLoadingContext(true);
    setShowContextModal(true);
    setGraphContextText('');
    setCopiedContext(false);
    try {
      const res = await getGraphContext({
        node_ids: node ? [node.id] : undefined,
        max_entities: 15,
        depth: 2
      });
      setGraphContextText(res?.formatted_context || 'No graph context generated.');
    } catch (err) {
      console.error('Context generation error:', err);
      setGraphContextText('Failed to generate context.');
    } finally {
      setIsLoadingContext(false);
    }
  };

  // Fetch full graph analytics
  const handleOpenAnalytics = async () => {
    setShowAnalyticsModal(true);
    setIsLoadingAnalytics(true);
    try {
      const [overview, health, top, orphans, duplicates] = await Promise.all([
        getGraphAnalyticsOverview(),
        getGraphHealth(),
        getTopConnectedEntities(8),
        getOrphanNodes(15),
        getDuplicateCandidates(0.85)
      ]);
      setAnalyticsOverview(overview);
      setHealthReport(health);
      setTopEntities(top || []);
      setOrphanList(orphans || []);
      setDuplicateList(duplicates || []);
    } catch (err) {
      console.error('Failed to load graph analytics:', err);
      showToast('Failed to load graph analytics');
    } finally {
      setIsLoadingAnalytics(false);
    }
  };

  // Execute Multi-Agent Graph Reasoning
  const handleExecuteReasoning = async () => {
    if (!reasonQuery.trim()) return;
    setIsReasoning(true);
    setReasonResult(null);
    try {
      const res = await reasonGraph({
        query: reasonQuery.trim(),
        depth: reasonDepth,
        include_rag: true,
        include_memory: true
      });
      setReasonResult(res);
    } catch (err) {
      console.error('Graph reasoning failed:', err);
      showToast('Graph reasoning failed: ' + (err.message || 'Error'));
    } finally {
      setIsReasoning(false);
    }
  };

  const getNodeColor = (type) => {
    const found = NODE_TYPES.find(t => t.id === type);
    return found ? found.color : '#94a3b8';
  };

  const getNodeBg = (type) => {
    const found = NODE_TYPES.find(t => t.id === type);
    return found ? found.bg : 'rgba(148, 163, 184, 0.15)';
  };

  const getNodeBorder = (type) => {
    const found = NODE_TYPES.find(t => t.id === type);
    return found ? found.border : 'rgba(148, 163, 184, 0.4)';
  };

  // Connected node IDs for highlighting
  const connectedNodeIds = useMemo(() => {
    if (!selectedNode) return new Set();
    const ids = new Set([selectedNode.id]);
    links.forEach(l => {
      if (l.source === selectedNode.id) ids.add(l.target);
      if (l.target === selectedNode.id) ids.add(l.source);
    });
    return ids;
  }, [selectedNode, links]);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-950 text-slate-100 overflow-hidden select-none font-sans relative">
      
      {/* Toast Notification */}
      {toastMessage && (
        <div className="absolute top-4 right-4 z-50 bg-indigo-600 text-white text-xs px-3.5 py-2 rounded-lg shadow-xl flex items-center gap-2 animate-fade-in border border-indigo-400/30">
          <Sparkles className="w-3.5 h-3.5" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Graph Top Bar */}
      <header className="px-5 py-3 border-b border-slate-800 bg-slate-900/60 backdrop-blur flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <GitBranch className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white tracking-wide">Knowledge Graph Explorer</h1>
            <p className="text-[11px] text-slate-400">
              {nodes.length} entities • {links.length} relationships
              {docIdParam && <span className="ml-2 px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px]">Document Filter Active</span>}
            </p>
          </div>
        </div>

        {/* Search & Actions Toolbar */}
        <div className="flex items-center gap-3">
          
          {/* Debounced Search Bar */}
          <div className="relative w-64 md:w-80">
            <div className="relative flex items-center">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
              <input
                type="text"
                placeholder="Search entities, technologies, documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-800/60 border border-slate-700/60 rounded-lg pl-9 pr-8 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 placeholder-slate-500"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-2.5 text-slate-400 hover:text-white">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Search Autocomplete Dropdown */}
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 w-full mt-1.5 bg-slate-900 border border-slate-800 rounded-lg shadow-2xl overflow-hidden z-50">
                <div className="p-1.5 space-y-1">
                  {searchResults.map((res) => (
                    <button
                      key={res.node_id}
                      onClick={() => {
                        const targetNode = nodes.find(n => n.id === res.node_id);
                        if (targetNode) {
                          handleSelectNode(targetNode);
                          setPanOffset({
                            x: dimensions.width / 2 - targetNode.x * zoomLevel,
                            y: dimensions.height / 2 - targetNode.y * zoomLevel
                          });
                        }
                        setSearchQuery('');
                        setSearchResults([]);
                      }}
                      className="w-full text-left px-3 py-2 rounded-md hover:bg-slate-800/80 flex items-center justify-between text-xs transition"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getNodeColor(res.node_type) }} />
                        <span className="font-medium text-slate-200">{res.name}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {res.node_type}
                        </span>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowReasonModal(true)}
              className="px-3 py-1.5 rounded-lg bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-500/40 text-xs font-medium text-emerald-300 flex items-center gap-1.5 transition shadow-sm"
            >
              <Bot className="w-3.5 h-3.5 text-emerald-400" />
              Ask Graph
            </button>
            <button
              onClick={handleOpenAnalytics}
              className="px-3 py-1.5 rounded-lg bg-indigo-950/60 hover:bg-indigo-900/60 border border-indigo-500/40 text-xs font-medium text-indigo-300 flex items-center gap-1.5 transition"
            >
              <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
              Analytics & Health
            </button>
            <button
              onClick={() => setShowPathModal(true)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/60 text-xs font-medium text-slate-200 flex items-center gap-1.5 transition"
            >
              <Navigation className="w-3.5 h-3.5 text-emerald-400" />
              Pathfinder
            </button>
            <button
              onClick={() => handleGenerateContext(selectedNode)}
              className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white flex items-center gap-1.5 transition shadow-sm"
            >
              <Brain className="w-3.5 h-3.5" />
              Graph Context
            </button>
            <button
              onClick={fetchGraphData}
              title="Refresh Graph"
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/60 text-slate-300 transition"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </header>

        {/* Filter Toolbar */}
        <div className="px-5 py-2.5 border-b border-slate-800/60 bg-slate-900/30 flex items-center justify-between text-xs gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            {/* Node Type Selector */}
            <div className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
              >
                {NODE_TYPES.map(t => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Relationship Type Selector */}
            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={selectedRelType}
                onChange={(e) => setSelectedRelType(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
              >
                {RELATIONSHIP_TYPES.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            {/* Confidence Slider */}
            <div className="flex items-center gap-2 ml-2">
              <span className="text-slate-400">Min Conf:</span>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="w-20 accent-indigo-500 h-1 bg-slate-700 rounded-lg cursor-pointer"
              />
              <span className="font-mono text-slate-300 w-8">{minConfidence.toFixed(2)}</span>
            </div>

            {/* Hide Isolated Nodes */}
            <button
              onClick={() => setHideIsolated(prev => !prev)}
              className={`px-2 py-1 rounded border text-xs flex items-center gap-1 transition ${
                hideIsolated 
                  ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300' 
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {hideIsolated ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              <span>Hide Isolated</span>
            </button>
          </div>

          {/* Canvas Controls */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsPhysicsActive(prev => !prev)}
              className={`p-1.5 rounded border text-xs transition ${
                isPhysicsActive ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400' : 'bg-slate-800 border-slate-700 text-slate-400'
              }`}
              title={isPhysicsActive ? 'Pause Physics' : 'Resume Physics'}
            >
              {isPhysicsActive ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
            <button onClick={() => handleZoom(0.15)} className="p-1.5 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300">
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button onClick={() => handleZoom(-0.15)} className="p-1.5 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300">
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button onClick={handleCenterGraph} className="p-1.5 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300" title="Center View">
              <Target className="w-3.5 h-3.5" />
            </button>
            <button onClick={handleResetView} className="p-1.5 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300" title="Reset Zoom">
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Main Content Area: Canvas + Inspector */}
        <div className="flex-1 flex relative overflow-hidden">
          {/* SVG Canvas */}
          <div className="flex-1 w-full h-full relative bg-slate-950 overflow-hidden cursor-crosshair">
            <svg
            ref={svgRef}
            id="graph-bg"
            className="w-full h-full"
            onMouseDown={handleMouseDownSvg}
            onMouseMove={handleMouseMoveSvg}
            onMouseUp={handleMouseUpSvg}
          >
            <defs>
              <marker
                id="arrowhead"
                viewBox="0 0 10 10"
                refX="22"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
              </marker>
              <marker
                id="arrowhead-path"
                viewBox="0 0 10 10"
                refX="22"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
              </marker>
            </defs>

            <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`}>
              
              {/* Edges */}
              {links.map((link) => {
                const srcNode = nodes.find(n => n.id === link.source);
                const tgtNode = nodes.find(n => n.id === link.target);
                if (!srcNode || !tgtNode) return null;

                const isSelected = selectedEdge?.id === link.id;
                const isPathEdge = highlightedPathEdgeKeys.has(`${srcNode.id}->${tgtNode.id}`);
                const isConnectedToSelected = selectedNode && (srcNode.id === selectedNode.id || tgtNode.id === selectedNode.id);
                const isDimmed = (selectedNode && !isConnectedToSelected) || (highlightedPathNodeIds.size > 0 && !isPathEdge);

                const strokeColor = isPathEdge ? '#10b981' : isSelected ? '#38bdf8' : isConnectedToSelected ? '#818cf8' : '#334155';
                const strokeWidth = isPathEdge ? 3 : isSelected ? 2.5 : isConnectedToSelected ? 2 : Math.max(1, (link.confidence || 0.8) * 1.8);

                const midX = (srcNode.x + tgtNode.x) / 2;
                const midY = (srcNode.y + tgtNode.y) / 2;

                return (
                  <g key={link.id} className="cursor-pointer" onClick={() => { setSelectedEdge(link); setSelectedNode(null); }}>
                    <line
                      x1={srcNode.x}
                      y1={srcNode.y}
                      x2={tgtNode.x}
                      y2={tgtNode.y}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeOpacity={isDimmed ? 0.2 : 0.85}
                      markerEnd={isPathEdge ? "url(#arrowhead-path)" : "url(#arrowhead)"}
                      className="transition-colors duration-200"
                    />
                    {/* Edge Label */}
                    <text
                      x={midX}
                      y={midY - 4}
                      fill={isPathEdge ? '#10b981' : isSelected ? '#38bdf8' : '#64748b'}
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                      opacity={isDimmed ? 0.2 : 0.8}
                    >
                      {link.relationship_type}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {nodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                const isHovered = hoveredNode?.id === node.id;
                const isPathNode = highlightedPathNodeIds.has(node.id);
                const isConnected = connectedNodeIds.has(node.id);
                const isDimmed = (selectedNode && !isConnected) || (highlightedPathNodeIds.size > 0 && !isPathNode);

                const nodeColor = getNodeColor(node.node_type);
                const nodeBg = getNodeBg(node.node_type);
                const nodeBorder = getNodeBorder(node.node_type);

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    className="cursor-pointer transition-opacity duration-200"
                    opacity={isDimmed ? 0.25 : 1}
                    onMouseEnter={() => setHoveredNode(node)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onMouseDown={(e) => {
                      e.stopPropagation();
                      setDraggedNode(node);
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectNode(node);
                    }}
                  >
                    {/* Glowing Selection Halo */}
                    {(isSelected || isPathNode) && (
                      <circle
                        r="26"
                        fill="none"
                        stroke={isPathNode ? '#10b981' : '#38bdf8'}
                        strokeWidth="3"
                        strokeDasharray={isPathNode ? '4 2' : 'none'}
                        className="animate-pulse"
                      />
                    )}

                    {/* Main Node Circle */}
                    <circle
                      r="18"
                      fill={nodeBg}
                      stroke={isSelected ? '#38bdf8' : nodeBorder}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                    />

                    {/* Inner Badge dot */}
                    <circle r="5" fill={nodeColor} />

                    {/* Node Text Label */}
                    <text
                      y="30"
                      textAnchor="middle"
                      fill={isSelected ? '#ffffff' : '#cbd5e1'}
                      fontSize="11"
                      fontWeight={isSelected ? '600' : '400'}
                      className="pointer-events-none drop-shadow"
                    >
                      {node.name.length > 16 ? `${node.name.slice(0, 14)}…` : node.name}
                    </text>
                  </g>
                );
              })}

            </g>
          </svg>

          {/* Active Pathfinder Clear Banner */}
          {highlightedPathNodeIds.size > 0 && (
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-emerald-950/90 border border-emerald-500/40 text-emerald-300 px-4 py-1.5 rounded-full text-xs flex items-center gap-3 backdrop-blur shadow-xl z-20">
              <Navigation className="w-3.5 h-3.5 text-emerald-400" />
              <span>Active Path ({highlightedPathNodeIds.size} nodes)</span>
              <button
                onClick={handleClearPath}
                className="text-emerald-400 hover:text-white underline font-medium ml-2"
              >
                Clear
              </button>
            </div>
          )}
        </div>

        {/* Node & Edge Inspector Side Panel */}
        <aside className="w-96 border-l border-slate-800 bg-slate-900/90 backdrop-blur-md flex flex-col h-full z-20 overflow-y-auto">
        
        {selectedNode ? (
          <div className="p-5 flex-1 flex flex-col space-y-5">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <span
                  className="text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded border uppercase"
                  style={{
                    color: getNodeColor(selectedNode.node_type),
                    backgroundColor: getNodeBg(selectedNode.node_type),
                    borderColor: getNodeBorder(selectedNode.node_type)
                  }}
                >
                  {selectedNode.node_type}
                </span>
                <h2 className="text-lg font-bold text-white mt-2 leading-tight">{selectedNode.name}</h2>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Description */}
            {selectedNode.description && (
              <div className="p-3 bg-slate-800/40 rounded-lg border border-slate-700/50 text-xs text-slate-300 leading-relaxed">
                {selectedNode.description}
              </div>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleExpandNeighbors(selectedNode)}
                disabled={isExpanding}
                className="px-3 py-2 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-medium flex items-center justify-center gap-1.5 transition"
              >
                <Plus className={`w-3.5 h-3.5 ${isExpanding ? 'animate-spin' : ''}`} />
                <span>Expand Neighbors</span>
              </button>
              <button
                onClick={() => handleSyncNodeToMemory(selectedNode)}
                className="px-3 py-2 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 text-xs font-medium flex items-center justify-center gap-1.5 transition"
              >
                <Brain className="w-3.5 h-3.5" />
                <span>Sync to Memory</span>
              </button>
            </div>

            {/* Node Metadata & Provenance */}
            <div className="space-y-2 text-xs">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Node Details</h3>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-2 font-mono text-[11px]">
                <div className="flex justify-between text-slate-400">
                  <span>ID:</span>
                  <span className="text-slate-200">{selectedNode.id.slice(0, 13)}…</span>
                </div>
                {selectedNode.external_id && (
                  <div className="flex justify-between text-slate-400">
                    <span>External ID:</span>
                    <span className="text-slate-200">{selectedNode.external_id}</span>
                  </div>
                )}
                <div className="flex justify-between text-slate-400">
                  <span>Connections:</span>
                  <span className="text-indigo-400 font-semibold">{connectedNodeIds.size - 1}</span>
                </div>
              </div>
            </div>

            {/* Related Entities Multi-Hop Section */}
            <div className="space-y-2 text-xs flex-1">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Multi-Hop Related Entities</span>
                {isLoadingRelated && <RefreshCw className="w-3 h-3 animate-spin text-indigo-400" />}
              </h3>
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                {relatedEntities.length === 0 && !isLoadingRelated ? (
                  <p className="text-xs text-slate-500 italic p-2">No multi-hop entities found.</p>
                ) : (
                  relatedEntities.map((rel) => (
                    <div
                      key={rel.node_id}
                      onClick={() => {
                        const target = nodes.find(n => n.id === rel.node_id);
                        if (target) handleSelectNode(target);
                      }}
                      className="p-2.5 rounded-lg bg-slate-800/40 hover:bg-slate-800 border border-slate-700/40 cursor-pointer flex items-center justify-between transition"
                    >
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-slate-200">{rel.name}</span>
                          <span className="text-[9px] px-1 py-0.5 rounded bg-slate-700/60 text-slate-400">
                            {rel.node_type}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {rel.relationship_path.join(' → ')}
                        </p>
                      </div>
                      <span className="text-[10px] font-mono text-emerald-400">
                        {Math.round(rel.relevance_score * 100)}%
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        ) : selectedEdge ? (
          <div className="p-5 flex-1 flex flex-col space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 uppercase">
                  Relationship
                </span>
                <h2 className="text-lg font-bold text-white mt-2">{selectedEdge.relationship_type}</h2>
              </div>
              <button onClick={() => setSelectedEdge(null)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Confidence:</span>
                <span className="text-emerald-400 font-bold">{Math.round((selectedEdge.confidence || 1) * 100)}%</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Source Node:</span>
                <span className="text-slate-200">{nodes.find(n => n.id === selectedEdge.source)?.name || selectedEdge.source}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Target Node:</span>
                <span className="text-slate-200">{nodes.find(n => n.id === selectedEdge.target)?.name || selectedEdge.target}</span>
              </div>
            </div>

            {selectedEdge.properties && Object.keys(selectedEdge.properties).length > 0 && (
              <div className="space-y-1.5 text-xs">
                <h3 className="font-semibold text-slate-400 uppercase tracking-wider">Provenance & Attributes</h3>
                <pre className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(selectedEdge.properties, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 flex-1 flex flex-col items-center justify-center text-center space-y-3">
            <div className="p-3 rounded-full bg-slate-800/80 border border-slate-700 text-slate-400">
              <Info className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">No Element Selected</h3>
            <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
              Click any node or relationship edge in the graph canvas to inspect its semantic properties, provenance, and multi-hop connections.
            </p>
          </div>
        )}

      </aside>
    </div>

      {/* Pathfinder Modal */}
      {showPathModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Navigation className="w-4 h-4 text-emerald-400" />
                Shortest-Path Discovery
              </h2>
              <button onClick={() => setShowPathModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Source Entity</label>
                <select
                  value={pathSourceId}
                  onChange={(e) => setPathSourceId(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select source node...</option>
                  {nodes.map(n => (
                    <option key={n.id} value={n.id}>{n.name} [{n.node_type}]</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Target Entity</label>
                <select
                  value={pathTargetId}
                  onChange={(e) => setPathTargetId(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select target node...</option>
                  {nodes.map(n => (
                    <option key={n.id} value={n.id}>{n.name} [{n.node_type}]</option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleFindPath}
                disabled={isFindingPath || !pathSourceId || !pathTargetId}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-medium rounded-lg transition flex items-center justify-center gap-2 mt-2"
              >
                {isFindingPath ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Navigation className="w-4 h-4" />}
                <span>Calculate Shortest Path</span>
              </button>
            </div>

            {pathResult && (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-2">
                {pathResult.path_found ? (
                  <>
                    <div className="flex items-center justify-between text-emerald-400 font-semibold">
                      <span>Path Found!</span>
                      <span>{pathResult.distance} Hops</span>
                    </div>
                    <div className="space-y-1 font-mono text-[11px] text-slate-300">
                      {pathResult.steps.map((step, idx) => (
                        <div key={idx} className="flex items-center gap-1.5">
                          <span className="text-slate-400">{step.from_node_name}</span>
                          <span className="text-indigo-400 font-bold">--[{step.relationship_type}]--&gt;</span>
                          <span className="text-emerald-300 font-medium">{step.to_node_name}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-rose-400">{pathResult.error || 'No path exists between the selected entities.'}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Graph Context Modal */}
      {showContextModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Brain className="w-4 h-4 text-indigo-400" />
                Structured Knowledge Graph Context
              </h2>
              <button onClick={() => setShowContextModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="relative">
              {isLoadingContext ? (
                <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
                  <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
                  <span className="text-xs">Generating graph context topology...</span>
                </div>
              ) : (
                <pre className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-200 max-h-96 overflow-y-auto whitespace-pre-wrap font-mono">
                  {graphContextText}
                </pre>
              )}
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(graphContextText);
                  setCopiedContext(true);
                  setTimeout(() => setCopiedContext(false), 2500);
                }}
                disabled={isLoadingContext || !graphContextText}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition"
              >
                {copiedContext ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedContext ? 'Copied to Clipboard!' : 'Copy Context'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Analytics & Health Modal */}
      {showAnalyticsModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 space-y-5 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    Knowledge Graph Analytics & Diagnostics
                  </h2>
                  <p className="text-xs text-slate-400">Structural metrics, degree connectivity, health diagnostics, and provenance breakdown.</p>
                </div>
              </div>
              <button onClick={() => setShowAnalyticsModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {isLoadingAnalytics ? (
              <div className="py-16 flex flex-col items-center justify-center text-slate-400 space-y-3">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
                <span className="text-xs">Computing topological metrics and health diagnostics...</span>
              </div>
            ) : analyticsOverview ? (
              <div className="space-y-6">
                
                {/* Metric Summary Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 space-y-1">
                    <span className="text-[11px] text-slate-400 font-medium">Total Entities</span>
                    <p className="text-xl font-bold text-white font-mono">{analyticsOverview.total_nodes}</p>
                    <span className="text-[10px] text-indigo-400">{analyticsOverview.connected_nodes_count} connected</span>
                  </div>

                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 space-y-1">
                    <span className="text-[11px] text-slate-400 font-medium">Relationships</span>
                    <p className="text-xl font-bold text-white font-mono">{analyticsOverview.total_edges}</p>
                    <span className="text-[10px] text-emerald-400">{Math.round(analyticsOverview.average_confidence * 100)}% avg conf</span>
                  </div>

                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 space-y-1">
                    <span className="text-[11px] text-slate-400 font-medium">Average Degree</span>
                    <p className="text-xl font-bold text-white font-mono">{analyticsOverview.average_degree}</p>
                    <span className="text-[10px] text-slate-400">max {analyticsOverview.max_degree} links</span>
                  </div>

                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 space-y-1">
                    <span className="text-[11px] text-slate-400 font-medium">Graph Health</span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {healthReport?.status === 'HEALTHY' ? (
                        <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                      )}
                      <span className={`text-base font-bold font-mono ${
                        healthReport?.status === 'HEALTHY' ? 'text-emerald-400' : 'text-amber-400'
                      }`}>
                        {healthReport?.status || 'HEALTHY'}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400">{analyticsOverview.isolated_nodes_count} isolated nodes</span>
                  </div>
                </div>

                {/* Health Diagnostics Banner */}
                {healthReport?.diagnostic_messages?.length > 0 && (
                  <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80 space-y-1.5">
                    <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 text-indigo-400" />
                      Diagnostic Summary
                    </span>
                    <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                      {healthReport.diagnostic_messages.map((msg, i) => (
                        <li key={i}>{msg}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Entity & Relationship Breakdown */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Entity Types */}
                  <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2.5">
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Entities by Type</h3>
                    <div className="space-y-2">
                      {Object.entries(analyticsOverview.nodes_by_type || {}).map(([type, count]) => (
                        <div key={type} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-300 font-medium">{type}</span>
                            <span className="text-slate-400 font-mono">{count}</span>
                          </div>
                          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${Math.min(100, (count / (analyticsOverview.total_nodes || 1)) * 100)}%`,
                                backgroundColor: getNodeColor(type)
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Relationship Types */}
                  <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2.5">
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Relationships by Type</h3>
                    <div className="space-y-2">
                      {Object.entries(analyticsOverview.edges_by_type || {}).map(([type, count]) => (
                        <div key={type} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-300 font-medium">{type}</span>
                            <span className="text-slate-400 font-mono">{count}</span>
                          </div>
                          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-indigo-500 h-full rounded-full"
                              style={{
                                width: `${Math.min(100, (count / (analyticsOverview.total_edges || 1)) * 100)}%`
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Top Connected Entities */}
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Top Connected Hub Entities</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {topEntities.map((ent) => (
                      <div
                        key={ent.node_id}
                        onClick={() => {
                          const target = nodes.find(n => n.id === ent.node_id);
                          if (target) {
                            handleSelectNode(target);
                            setPanOffset({
                              x: dimensions.width / 2 - target.x * zoomLevel,
                              y: dimensions.height / 2 - target.y * zoomLevel
                            });
                            setShowAnalyticsModal(false);
                          }
                        }}
                        className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 hover:border-indigo-500/50 cursor-pointer flex items-center justify-between text-xs transition"
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getNodeColor(ent.node_type) }} />
                          <span className="font-medium text-slate-200">{ent.name}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            {ent.node_type}
                          </span>
                        </div>
                        <span className="font-mono text-indigo-400 font-semibold">{ent.degree} links</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Duplicate Review Candidates */}
                {duplicateList.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Potential Duplicate Entity Review ({duplicateList.length})
                    </h3>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {duplicateList.map((dup, i) => (
                        <div key={i} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs flex items-center justify-between">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="text-slate-200 font-medium">{dup.source_name}</span>
                              <span className="text-slate-500">↔</span>
                              <span className="text-slate-200 font-medium">{dup.target_name}</span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{dup.entity_type}</span>
                            </div>
                            <p className="text-[10px] text-slate-400">{dup.reason}</p>
                          </div>
                          <span className="font-mono text-amber-400 font-semibold text-xs">
                            {Math.round(dup.similarity_score * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Multi-Agent "Ask Graph" Reasoning Modal */}
      {showReasonModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 space-y-5 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    Multi-Agent Knowledge Graph Reasoning
                  </h2>
                  <p className="text-xs text-slate-400">Ask topological, dependency, and multi-hop questions directly against the knowledge graph.</p>
                </div>
              </div>
              <button onClick={() => setShowReasonModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Input Form */}
            <div className="space-y-3">
              <label className="text-xs font-medium text-slate-300">Natural Language Reasoning Query</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. How does AegisAI Core connect to PostgreSQL Engine?"
                  value={reasonQuery}
                  onChange={(e) => setReasonQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleExecuteReasoning(); }}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 placeholder-slate-600"
                />
                <button
                  onClick={handleExecuteReasoning}
                  disabled={isReasoning || !reasonQuery.trim()}
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-xl flex items-center gap-2 transition shadow-md"
                >
                  {isReasoning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  <span>{isReasoning ? 'Reasoning...' : 'Ask Graph'}</span>
                </button>
              </div>
            </div>

            {/* Results Display */}
            {reasonResult && (
              <div className="space-y-4 pt-2 border-t border-slate-800/80">
                {/* Result Metrics */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-center">
                    <span className="text-[10px] text-slate-400">Matched Entities</span>
                    <p className="text-sm font-bold text-emerald-400 font-mono">{reasonResult.matched_nodes_count}</p>
                  </div>
                  <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-center">
                    <span className="text-[10px] text-slate-400">Connected Edges</span>
                    <p className="text-sm font-bold text-indigo-400 font-mono">{reasonResult.matched_edges_count}</p>
                  </div>
                  <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-center">
                    <span className="text-[10px] text-slate-400">Confidence</span>
                    <p className="text-sm font-bold text-white font-mono">{Math.round(reasonResult.confidence * 100)}%</p>
                  </div>
                </div>

                {/* Graph Context */}
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold text-slate-300">Grounded Graph Topology</span>
                  <pre className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-200 whitespace-pre-wrap font-mono max-h-56 overflow-y-auto">
                    {reasonResult.graph_context || 'No explicit topological path detected for query.'}
                  </pre>
                </div>

                {/* Graph Citations */}
                {reasonResult.citations?.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-slate-300">Attributed Graph Citations ({reasonResult.citations.length})</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {reasonResult.citations.map((cite, i) => (
                        <div
                          key={i}
                          onClick={() => {
                            if (cite.node_id) {
                              const target = nodes.find(n => n.id === cite.node_id);
                              if (target) {
                                handleSelectNode(target);
                                setPanOffset({
                                  x: dimensions.width / 2 - target.x * zoomLevel,
                                  y: dimensions.height / 2 - target.y * zoomLevel
                                });
                                setShowReasonModal(false);
                              }
                            }
                          }}
                          className="p-2 bg-slate-950 rounded-lg border border-slate-800 hover:border-emerald-500/50 cursor-pointer flex items-center justify-between text-xs transition"
                        >
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-400" />
                            <span className="text-slate-200 font-medium">{cite.node_name || cite.relationship_type}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                              {cite.source_type}
                            </span>
                          </div>
                          <span className="text-[10px] font-mono text-emerald-400">{Math.round(cite.confidence * 100)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}

          </div>
        </div>
      )}

    </div>
  );
}

