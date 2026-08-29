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
  AlertCircle
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
  getDocumentRelationships
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

  // States
  const [isLoading, setIsLoading] = useState(true);
  const [isExpanding, setIsExpanding] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedType, setSelectedType] = useState('ALL');
  const [selectedRelType, setSelectedRelType] = useState('ALL');
  const [depthLimit, setDepthLimit] = useState(2);
  const [nodeLimit, setNodeLimit] = useState(50);
  const [isPhysicsActive, setIsPhysicsActive] = useState(true);

  // Interaction States
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [relatedEntities, setRelatedEntities] = useState([]);
  const [isLoadingRelated, setIsLoadingRelated] = useState(false);

  // Modals & Panels
  const [showPathModal, setShowPathModal] = useState(false);
  const [pathSourceId, setPathSourceId] = useState('');
  const [pathTargetId, setPathTargetId] = useState('');
  const [pathResult, setPathResult] = useState(null);
  const [isFindingPath, setIsFindingPath] = useState(false);

  const [showContextModal, setShowContextModal] = useState(false);
  const [graphContextText, setGraphContextText] = useState('');
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [copiedContext, setCopiedContext] = useState(false);

  // Canvas & Physics
  const svgRef = useRef(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [draggedNode, setDraggedNode] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 900, height: 600 });

  // Update canvas size on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (svgRef.current) {
        const { clientWidth, clientHeight } = svgRef.current;
        setDimensions({ width: clientWidth || 900, height: clientHeight || 600 });
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
        // Document-specific subgraph
        const [docNodes, docEdges] = await Promise.all([
          getDocumentEntities(docIdParam),
          getDocumentRelationships(docIdParam)
        ]);
        setRawNodes(docNodes || []);
        setRawEdges(docEdges || []);
      } else {
        // General workspace graph
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
  // 2. Transform Raw Nodes & Edges to Simulation Elements
  // ----------------------------------------------------------------------
  useEffect(() => {
    let filteredNodes = rawNodes;
    if (selectedType !== 'ALL') {
      filteredNodes = rawNodes.filter(n => n.node_type === selectedType);
    }

    const validNodeIds = new Set(filteredNodes.map(n => n.id));

    let filteredEdges = rawEdges.filter(e => 
      validNodeIds.has(e.source_node_id) && validNodeIds.has(e.target_node_id)
    );

    if (selectedRelType !== 'ALL') {
      filteredEdges = filteredEdges.filter(e => e.relationship_type === selectedRelType);
    }

    // Preserve existing node positions if present
    const prevPosMap = new Map(nodes.map(n => [n.id, { x: n.x, y: n.y, vx: n.vx, vy: n.vy }]));

    const cx = dimensions.width / 2;
    const cy = dimensions.height / 2;

    const simNodes = filteredNodes.map((n, i) => {
      const prev = prevPosMap.get(n.id);
      const angle = (i / (filteredNodes.length || 1)) * 2 * Math.PI;
      const radius = 120 + (i % 3) * 60;
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
  }, [rawNodes, rawEdges, selectedType, selectedRelType, dimensions]);

  // ----------------------------------------------------------------------
  // 3. Force Physics Simulation Loop
  // ----------------------------------------------------------------------
  useEffect(() => {
    if (!isPhysicsActive || nodes.length === 0) return;

    let frameId;
    let iterations = 0;

    const tick = () => {
      setNodes(prevNodes => {
        const nextNodes = prevNodes.map(n => ({ ...n, vx: (n.vx || 0) * 0.85, vy: (n.vy || 0) * 0.85 }));
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
            const minDist = 140;

            if (dist < minDist) {
              const force = (minDist - dist) / dist * 0.15;
              const fx = dx * force;
              const fy = dy * force;

              if (nodeA.id !== draggedNode?.id) { nodeA.vx -= fx; nodeA.vy -= fy; }
              if (nodeB.id !== draggedNode?.id) { nodeB.vx += fx; nodeB.vy += fy; }
            }
          }
        }

        // Link spring attraction
        links.forEach(link => {
          const source = nextNodes.find(n => n.id === link.source);
          const target = nextNodes.find(n => n.id === link.target);
          if (!source || !target) return;

          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const desiredDist = 120;
          const k = 0.03;

          const force = (dist - desiredDist) * k;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (source.id !== draggedNode?.id) { source.vx += fx; source.vy += fy; }
          if (target.id !== draggedNode?.id) { target.vx -= fx; target.vy -= fy; }
        });

        // Center gravity
        nextNodes.forEach(node => {
          if (node.id === draggedNode?.id) return;
          node.vx += (cx - node.x) * 0.003;
          node.vy += (cy - node.y) * 0.003;

          node.x += node.vx;
          node.y += node.vy;
        });

        return nextNodes;
      });

      iterations++;
      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [isPhysicsActive, links, dimensions, draggedNode]);

  // ----------------------------------------------------------------------
  // 4. Node Selection & Related Entity Lookup
  // ----------------------------------------------------------------------
  const handleSelectNode = async (node) => {
    setSelectedNode(node);
    setPathSourceId(node.id);
    setIsLoadingRelated(true);
    try {
      const relResp = await getRelatedEntities(node.id, { depth: depthLimit, limit: 15 });
      setRelatedEntities(relResp.related_entities || []);
    } catch (err) {
      console.warn('Could not load related entities:', err);
      setRelatedEntities([]);
    } finally {
      setIsLoadingRelated(false);
    }
  };

  // Expand Neighbors (Lazy expansion)
  const handleExpandNeighbors = async (nodeId) => {
    setIsExpanding(true);
    try {
      const neighbors = await getNeighbors(nodeId);
      const newNodes = [];
      const newEdges = [];

      neighbors.forEach(item => {
        if (!rawNodes.some(n => n.id === item.node.id)) {
          newNodes.push(item.node);
        }
        const edgeId = item.edge_id;
        const exists = rawEdges.some(e => e.id === edgeId);
        if (!exists) {
          newEdges.push({
            id: edgeId,
            source_node_id: item.direction === 'outgoing' ? nodeId : item.node.id,
            target_node_id: item.direction === 'outgoing' ? item.node.id : nodeId,
            relationship_type: item.relationship_type,
            confidence: item.confidence
          });
        }
      });

      if (newNodes.length > 0) setRawNodes(prev => [...prev, ...newNodes]);
      if (newEdges.length > 0) setRawEdges(prev => [...prev, ...newEdges]);
    } catch (err) {
      console.error('Failed to expand neighbors:', err);
    } finally {
      setIsExpanding(false);
    }
  };

  // ----------------------------------------------------------------------
  // 5. Enhanced Live Search
  // ----------------------------------------------------------------------
  useEffect(() => {
    if (!searchQuery || searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchEnhanced({ q: searchQuery.trim(), limit: 10 });
        setSearchResults(results || []);
      } catch (err) {
        console.warn('Search failed:', err);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSelectSearchResult = (result) => {
    const existing = nodes.find(n => n.id === result.node_id);
    if (existing) {
      handleSelectNode(existing);
      // Center canvas on this node
      setPanOffset({
        x: dimensions.width / 2 - existing.x * zoomLevel,
        y: dimensions.height / 2 - existing.y * zoomLevel
      });
    } else {
      // Fetch node and add to graph
      getNode(result.node_id).then(nodeData => {
        setRawNodes(prev => [...prev, nodeData]);
        handleSelectNode(nodeData);
      });
    }
    setSearchResults([]);
  };

  // ----------------------------------------------------------------------
  // 6. Path Finding
  // ----------------------------------------------------------------------
  const handleFindPath = async () => {
    if (!pathSourceId || !pathTargetId) return;
    setIsFindingPath(true);
    setPathResult(null);
    try {
      const resp = await findPath({
        source_node_id: pathSourceId,
        target_node_id: pathTargetId,
        max_depth: depthLimit
      });
      setPathResult(resp);

      // Merge path nodes & edges into graph if not present
      if (resp.nodes && resp.nodes.length > 0) {
        const missingNodes = resp.nodes.filter(n => !rawNodes.some(rn => rn.id === n.id));
        if (missingNodes.length > 0) setRawNodes(prev => [...prev, ...missingNodes]);
      }
    } catch (err) {
      console.error('Path finding failed:', err);
      setPathResult({ path_found: false, distance: 0, steps: [] });
    } finally {
      setIsFindingPath(false);
    }
  };

  // ----------------------------------------------------------------------
  // 7. Graph Context Generation
  // ----------------------------------------------------------------------
  const handleOpenGraphContext = async () => {
    setShowContextModal(true);
    setIsLoadingContext(true);
    setCopiedContext(false);
    try {
      const activeIds = selectedNode ? [selectedNode.id] : nodes.slice(0, 5).map(n => n.id);
      const resp = await getGraphContext({
        node_ids: activeIds,
        depth: depthLimit,
        max_entities: 30
      });
      setGraphContextText(resp.formatted_context || 'No graph context generated.');
    } catch (err) {
      setGraphContextText('Failed to generate graph context: ' + (err.message || 'Unknown error'));
    } finally {
      setIsLoadingContext(false);
    }
  };

  const handleCopyContext = () => {
    navigator.clipboard.writeText(graphContextText);
    setCopiedContext(true);
    setTimeout(() => setCopiedContext(false), 2000);
  };

  // ----------------------------------------------------------------------
  // 8. Pan & Zoom & Drag Handlers
  // ----------------------------------------------------------------------
  const handleMouseDown = (e) => {
    if (e.target.tagName === 'svg' || e.target.id === 'canvas-bg') {
      setIsPanning(true);
      setPanStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isPanning) {
      setPanOffset({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    } else if (draggedNode) {
      const svgRect = svgRef.current.getBoundingClientRect();
      const mouseX = (e.clientX - svgRect.left - panOffset.x) / zoomLevel;
      const mouseY = (e.clientY - svgRect.top - panOffset.y) / zoomLevel;

      setNodes(prev => prev.map(n => n.id === draggedNode.id ? { ...n, x: mouseX, y: mouseY, vx: 0, vy: 0 } : n));
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggedNode(null);
  };

  const handleResetLayout = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
    setSelectedNode(null);
    setPathResult(null);
    fetchGraphData();
  };

  // Node Color Helper
  const getNodeColor = (type) => {
    const found = NODE_TYPES.find(t => t.id === type);
    return found ? found.color : '#94a3b8';
  };

  const getNodeBg = (type) => {
    const found = NODE_TYPES.find(t => t.id === type);
    return found ? found.bg : 'rgba(148, 163, 184, 0.15)';
  };

  // Highlighted path node/edge IDs
  const pathNodeIds = useMemo(() => {
    if (!pathResult || !pathResult.steps) return new Set();
    const ids = new Set();
    pathResult.steps.forEach(s => {
      ids.add(s.from_node_id);
      ids.add(s.to_node_id);
    });
    return ids;
  }, [pathResult]);

  return (
    <div className="flex flex-col h-[calc(100vh-4.5rem)] bg-[#0b0f17] text-slate-200 overflow-hidden select-none">
      
      {/* Top Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 border-b border-slate-800/80 bg-[#0d131f]/90 backdrop-blur-md z-20">
        
        {/* Left: Title & Quick Stats */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <GitBranch size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white tracking-wide">Knowledge Graph Explorer</h1>
              {docIdParam && (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Document Subgraph
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              {nodes.length} entities • {links.length} relationships
            </p>
          </div>
        </div>

        {/* Center: Live Enhanced Search */}
        <div className="relative w-72">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-700/80 focus-within:border-cyan-500 transition-colors">
            <Search size={15} className="text-slate-400" />
            <input
              type="text"
              placeholder="Search entities or concepts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs bg-transparent text-white placeholder-slate-500 focus:outline-none"
            />
            {isSearching && <RefreshCw size={13} className="animate-spin text-cyan-400" />}
          </div>

          {/* Autocomplete Dropdown */}
          {searchResults.length > 0 && (
            <div className="absolute left-0 right-0 top-full mt-1.5 max-h-60 overflow-y-auto bg-slate-900 border border-slate-700 rounded-lg shadow-2xl z-50 divide-y divide-slate-800">
              {searchResults.map((res) => (
                <button
                  key={res.node_id}
                  onClick={() => handleSelectSearchResult(res)}
                  className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-slate-800 transition-colors"
                >
                  <div>
                    <div className="text-xs font-medium text-white">{res.name}</div>
                    <div className="text-[10px] text-slate-400">{res.node_type} • Score: {(res.relevance_score * 100).toFixed(0)}%</div>
                  </div>
                  <ChevronRight size={14} className="text-slate-500" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Type Filters & Actions */}
        <div className="flex items-center gap-2">
          {/* Node Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg bg-slate-900 border border-slate-700 text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            {NODE_TYPES.map(t => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </select>

          {/* Relationship Filter */}
          <select
            value={selectedRelType}
            onChange={(e) => setSelectedRelType(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg bg-slate-900 border border-slate-700 text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            {RELATIONSHIP_TYPES.map(r => (
              <option key={r} value={r}>{r === 'ALL' ? 'All Relationships' : r}</option>
            ))}
          </select>

          {/* Path Finding Trigger */}
          <button
            onClick={() => setShowPathModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 transition-colors"
          >
            <Navigation size={14} />
            <span>Find Path</span>
          </button>

          {/* Graph Context Trigger */}
          <button
            onClick={handleOpenGraphContext}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 transition-colors"
          >
            <Code size={14} />
            <span>Graph Context</span>
          </button>

          {/* Refresh / Rebuild */}
          <button
            onClick={fetchGraphData}
            title="Refresh graph"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Main Content Area: Graph Canvas + Details Sidebar */}
      <div className="relative flex-1 flex overflow-hidden">
        
        {/* SVG Interactive Canvas */}
        <div 
          className="relative flex-1 bg-[#070a10] overflow-hidden cursor-grab active:cursor-grabbing"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          {isLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#070a10]/80 z-30">
              <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin"></div>
              <span className="text-xs font-medium text-cyan-400">Loading graph topology...</span>
            </div>
          ) : nodes.length === 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-500 z-10">
              <GitBranch size={48} className="text-slate-700 stroke-1" />
              <p className="text-sm font-medium">No knowledge graph entities found.</p>
              <p className="text-xs text-slate-600 max-w-sm text-center">
                Upload and process documents to automatically generate knowledge graph entities and relationships.
              </p>
            </div>
          ) : null}

          <svg
            ref={svgRef}
            id="canvas-bg"
            className="w-full h-full"
            style={{ touchAction: 'none' }}
          >
            <defs>
              {/* Arrow Marker definition */}
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="22"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
              </marker>
              <marker
                id="arrow-active"
                viewBox="0 0 10 10"
                refX="22"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#06b6d4" />
              </marker>
              <marker
                id="arrow-path"
                viewBox="0 0 10 10"
                refX="22"
                refY="5"
                markerWidth="8"
                markerHeight="8"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#ec4899" />
              </marker>
            </defs>

            <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`}>
              
              {/* Relationship Links */}
              {links.map((link, i) => {
                const source = nodes.find(n => n.id === link.source);
                const target = nodes.find(n => n.id === link.target);
                if (!source || !target) return null;

                const isConnectedToSelected = selectedNode && (selectedNode.id === source.id || selectedNode.id === target.id);
                const isPathEdge = pathNodeIds.has(source.id) && pathNodeIds.has(target.id);

                let strokeColor = '#334155';
                let markerId = 'arrow';
                let strokeWidth = 1.5;

                if (isPathEdge) {
                  strokeColor = '#ec4899';
                  markerId = 'arrow-path';
                  strokeWidth = 2.5;
                } else if (isConnectedToSelected) {
                  strokeColor = '#06b6d4';
                  markerId = 'arrow-active';
                  strokeWidth = 2;
                }

                // Midpoint for label
                const midX = (source.x + target.x) / 2;
                const midY = (source.y + target.y) / 2;

                return (
                  <g key={`link-${link.id || i}`}>
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeDasharray={link.relationship_type === 'DEPENDS_ON' ? '4 3' : undefined}
                      markerEnd={`url(#${markerId})`}
                      className="transition-colors duration-200"
                    />
                    {(isConnectedToSelected || isPathEdge || zoomLevel > 1.2) && (
                      <text
                        x={midX}
                        y={midY - 4}
                        fill={isPathEdge ? '#f472b6' : isConnectedToSelected ? '#67e8f9' : '#64748b'}
                        fontSize="9"
                        textAnchor="middle"
                        className="pointer-events-none font-mono"
                      >
                        {link.relationship_type}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Entity Nodes */}
              {nodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                const isHovered = hoveredNode?.id === node.id;
                const isPathNode = pathNodeIds.has(node.id);
                const color = getNodeColor(node.node_type);
                const bg = getNodeBg(node.node_type);

                return (
                  <g
                    key={`node-${node.id}`}
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectNode(node);
                    }}
                    onMouseEnter={() => setHoveredNode(node)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onMouseDown={(e) => {
                      e.stopPropagation();
                      setDraggedNode(node);
                    }}
                    className="cursor-pointer group"
                  >
                    {/* Pulsing ring on selected/path node */}
                    {(isSelected || isPathNode) && (
                      <circle
                        r={24}
                        fill="none"
                        stroke={isPathNode ? '#ec4899' : '#06b6d4'}
                        strokeWidth="2"
                        strokeOpacity="0.8"
                        className="animate-ping"
                      />
                    )}

                    {/* Node Circle Outer Glow */}
                    <circle
                      r={18}
                      fill={bg}
                      stroke={isSelected ? '#38bdf8' : isPathNode ? '#f472b6' : color}
                      strokeWidth={isSelected || isPathNode ? 2.5 : 1.5}
                      className="transition-all duration-200 shadow-lg"
                    />

                    {/* Node Center Badge */}
                    <circle
                      r={6}
                      fill={color}
                    />

                    {/* Node Label */}
                    <text
                      y={28}
                      textAnchor="middle"
                      fill={isSelected ? '#38bdf8' : isPathNode ? '#f472b6' : '#e2e8f0'}
                      fontSize={isSelected ? '12' : '11'}
                      fontWeight={isSelected ? 'bold' : 'normal'}
                      className="pointer-events-none drop-shadow-md select-none"
                    >
                      {node.name.length > 20 ? `${node.name.slice(0, 18)}...` : node.name}
                    </text>

                    {/* Node Type Pill Subtext */}
                    {(isSelected || isHovered) && (
                      <text
                        y={40}
                        textAnchor="middle"
                        fill="#94a3b8"
                        fontSize="9"
                        className="pointer-events-none font-mono"
                      >
                        {node.node_type}
                      </text>
                    )}
                  </g>
                );
              })}

            </g>
          </svg>

          {/* Floating Canvas Controls (Bottom Left) */}
          <div className="absolute bottom-4 left-4 flex items-center gap-1.5 p-1.5 rounded-xl bg-slate-900/90 border border-slate-800 shadow-xl backdrop-blur-md z-10">
            <button
              onClick={() => setZoomLevel(prev => Math.min(prev + 0.2, 2.5))}
              title="Zoom in"
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 transition-colors"
            >
              <ZoomIn size={16} />
            </button>
            <button
              onClick={() => setZoomLevel(prev => Math.max(prev - 0.2, 0.4))}
              title="Zoom out"
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 transition-colors"
            >
              <ZoomOut size={16} />
            </button>
            <button
              onClick={handleResetLayout}
              title="Fit to center / Reset"
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 transition-colors"
            >
              <RotateCcw size={16} />
            </button>
            <div className="w-[1px] h-4 bg-slate-800 mx-1" />
            <button
              onClick={() => setIsPhysicsActive(prev => !prev)}
              title={isPhysicsActive ? 'Pause physics simulation' : 'Resume physics simulation'}
              className={`p-1.5 rounded-lg transition-colors ${
                isPhysicsActive ? 'text-cyan-400 bg-cyan-500/10' : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              {isPhysicsActive ? <Pause size={16} /> : <Play size={16} />}
            </button>
          </div>
        </div>

        {/* Selected Node Details Drawer (Right Panel) */}
        {selectedNode && (
          <div className="w-80 border-l border-slate-800 bg-[#0d131f] flex flex-col z-20 shadow-2xl overflow-y-auto">
            
            {/* Header */}
            <div className="p-4 border-b border-slate-800 flex items-start justify-between gap-2">
              <div>
                <span 
                  className="inline-block px-2 py-0.5 text-[10px] font-bold rounded-full mb-1 uppercase tracking-wider"
                  style={{
                    backgroundColor: getNodeBg(selectedNode.node_type),
                    color: getNodeColor(selectedNode.node_type)
                  }}
                >
                  {selectedNode.node_type}
                </span>
                <h2 className="text-sm font-bold text-white break-words">{selectedNode.name}</h2>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            {/* Content Body */}
            <div className="p-4 space-y-4 flex-1">
              
              {/* Description */}
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Description</label>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  {selectedNode.description || 'No description provided.'}
                </p>
              </div>

              {/* Actions */}
              <div className="space-y-2">
                <button
                  onClick={() => handleExpandNeighbors(selectedNode.id)}
                  disabled={isExpanding}
                  className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 transition-colors disabled:opacity-50"
                >
                  {isExpanding ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
                  <span>Expand Connected Neighbors</span>
                </button>

                <button
                  onClick={() => {
                    setPathSourceId(selectedNode.id);
                    setShowPathModal(true);
                  }}
                  className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                >
                  <Navigation size={14} />
                  <span>Find Path From Here</span>
                </button>
              </div>

              {/* Multi-Hop Related Entities */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Related Entities ({relatedEntities.length})</label>
                  {isLoadingRelated && <RefreshCw size={12} className="animate-spin text-cyan-400" />}
                </div>

                {relatedEntities.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No multi-hop entities discovered within {depthLimit} hops.</p>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {relatedEntities.map((rel, i) => (
                      <div
                        key={rel.node_id || i}
                        onClick={() => {
                          const existing = nodes.find(n => n.id === rel.node_id);
                          if (existing) handleSelectNode(existing);
                        }}
                        className="p-2 rounded-lg bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800/80 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-slate-200">{rel.name}</span>
                          <span className="text-[10px] font-mono text-cyan-400">{(rel.relevance_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="text-[10px] text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>{rel.node_type}</span>
                          <span>•</span>
                          <span>{rel.distance} hop{rel.distance > 1 ? 's' : ''}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Provenance Metadata */}
              {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Provenance & Metadata</label>
                  <pre className="text-[10px] font-mono text-slate-400 mt-1 bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 overflow-x-auto max-h-36">
                    {JSON.stringify(selectedNode.metadata, null, 2)}
                  </pre>
                </div>
              )}

            </div>
          </div>
        )}

      </div>

      {/* Path Finding Modal */}
      {showPathModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0f172a] border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Navigation size={18} className="text-cyan-400" />
                <span>Bounded Shortest Path Search</span>
              </h3>
              <button onClick={() => setShowPathModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-400">Source Entity</label>
                <select
                  value={pathSourceId}
                  onChange={(e) => setPathSourceId(e.target.value)}
                  className="w-full mt-1 p-2 text-xs rounded-lg bg-slate-900 border border-slate-700 text-white focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Select source entity...</option>
                  {rawNodes.map(n => (
                    <option key={`src-${n.id}`} value={n.id}>{n.name} ({n.node_type})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-400">Target Entity</label>
                <select
                  value={pathTargetId}
                  onChange={(e) => setPathTargetId(e.target.value)}
                  className="w-full mt-1 p-2 text-xs rounded-lg bg-slate-900 border border-slate-700 text-white focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Select target entity...</option>
                  {rawNodes.map(n => (
                    <option key={`tgt-${n.id}`} value={n.id}>{n.name} ({n.node_type})</option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleFindPath}
                disabled={!pathSourceId || !pathTargetId || isFindingPath}
                className="w-full py-2 text-xs font-semibold rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isFindingPath && <RefreshCw size={14} className="animate-spin" />}
                <span>Calculate Shortest Pathway</span>
              </button>
            </div>

            {/* Path Result Display */}
            {pathResult && (
              <div className="mt-4 p-3 rounded-lg bg-slate-950 border border-slate-800">
                {pathResult.path_found ? (
                  <div>
                    <div className="flex items-center justify-between text-xs font-semibold text-emerald-400 mb-2">
                      <span>Path Found!</span>
                      <span>{pathResult.distance} hop{pathResult.distance > 1 ? 's' : ''}</span>
                    </div>
                    <div className="space-y-2">
                      {pathResult.steps.map((step, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs text-slate-300">
                          <span className="font-semibold text-white">{step.from_node_name}</span>
                          <ArrowRight size={12} className="text-cyan-400" />
                          <span className="px-1.5 py-0.5 text-[10px] font-mono bg-cyan-500/20 text-cyan-300 rounded">
                            {step.relationship_type}
                          </span>
                          <ArrowRight size={12} className="text-cyan-400" />
                          <span className="font-semibold text-white">{step.to_node_name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-rose-400">No relationship pathway found within {depthLimit} hops.</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Graph Context Modal */}
      {showContextModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0f172a] border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Code size={18} className="text-purple-400" />
                <span>Generated Hierarchical Graph Context</span>
              </h3>
              <button onClick={() => setShowContextModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <p className="text-xs text-slate-400">
              Formatted graph context tree generated for LLM prompt augmentation and RAG reasoning.
            </p>

            <div className="relative">
              {isLoadingContext ? (
                <div className="h-48 flex items-center justify-center gap-2 text-purple-400 text-xs">
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Formatting hierarchical graph context...</span>
                </div>
              ) : (
                <pre className="h-64 overflow-y-auto p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {graphContextText}
                </pre>
              )}

              <button
                onClick={handleCopyContext}
                disabled={isLoadingContext}
                className="absolute top-3 right-3 px-3 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors"
              >
                {copiedContext ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                <span>{copiedContext ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
