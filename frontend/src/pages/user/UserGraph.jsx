import React, { useState, useEffect, useRef } from 'react';
import { GitBranch, Info, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

const initialNodes = [
  { id: '1', label: 'FastAPI', type: 'technology', desc: 'Main backend Python API engine.' },
  { id: '2', label: 'React', type: 'technology', desc: 'Modern user interface library.' },
  { id: '3', label: 'AegisAI OS', type: 'concept', desc: 'Central orchestrator agent OS.' },
  { id: '4', label: 'SQLite', type: 'technology', desc: 'Relational storage mapping user relationships.' },
  { id: '5', label: 'ChromaDB', type: 'technology', desc: 'Vector database storing semantic memory.' },
  { id: '6', label: 'Handshake stdio', type: 'concept', desc: 'JSON-RPC pipe protocols.' }
];

const initialLinks = [
  { source: '3', target: '1' },
  { source: '3', target: '2' },
  { source: '3', target: '4' },
  { source: '3', target: '5' },
  { source: '1', target: '4' },
  { source: '2', target: '1' },
  { source: '3', target: '6' }
];

export default function UserGraph() {
  const [nodes, setNodes] = useState([]);
  const [links, setLinks] = useState(initialLinks);
  const [selectedNode, setSelectedNode] = useState(null);
  const [draggedNode, setDraggedNode] = useState(null);
  const svgRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 680, height: 400 });

  // Initialize node positions randomly
  useEffect(() => {
    const initializedNodes = initialNodes.map(n => ({
      ...n,
      x: Math.random() * 300 + 150,
      y: Math.random() * 200 + 100,
      vx: 0,
      vy: 0
    }));
    setNodes(initializedNodes);
  }, []);

  // Force-directed simulation physics loop
  useEffect(() => {
    if (nodes.length === 0) return;

    let frameId;
    const tick = () => {
      setNodes(prevNodes => {
        const nextNodes = prevNodes.map(n => ({ ...n, vx: 0, vy: 0 }));

        // Repulsion between node pairs (charge force)
        for (let i = 0; i < nextNodes.length; i++) {
          const nodeA = nextNodes[i];
          for (let j = i + 1; j < nextNodes.length; j++) {
            const nodeB = nextNodes[j];
            const dx = nodeB.x - nodeA.x;
            const dy = nodeB.y - nodeA.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            
            if (dist < 160) {
              const force = (160 - dist) / dist * 0.12;
              const fx = dx * force;
              const fy = dy * force;
              
              if (nodeA.id !== draggedNode?.id) { nodeA.vx -= fx; nodeA.vy -= fy; }
              if (nodeB.id !== draggedNode?.id) { nodeB.vx += fx; nodeB.vy += fy; }
            }
          }
        }

        // Attraction along link paths (spring force)
        links.forEach(link => {
          const source = nextNodes.find(n => n.id === link.source);
          const target = nextNodes.find(n => n.id === link.target);
          if (!source || !target) return;

          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const desiredDist = 110;
          const k = 0.02; // spring strength
          
          const force = (dist - desiredDist) * k;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (source.id !== draggedNode?.id) { source.vx += fx; source.vy += fy; }
          if (target.id !== draggedNode?.id) { target.vx -= fx; target.vy -= fy; }
        });

        // Center gravity pulling towards canvas center
        const cx = dimensions.width / 2;
        const cy = dimensions.height / 2;
        nextNodes.forEach(node => {
          if (node.id === draggedNode?.id) return;
          
          node.vx += (cx - node.x) * 0.003;
          node.vy += (cy - node.y) * 0.003;
          
          node.x += node.vx;
          node.y += node.vy;
          
          // Apply bounds dampening
          node.x = Math.max(30, Math.min(dimensions.width - 30, node.x));
          node.y = Math.max(30, Math.min(dimensions.height - 30, node.y));
        });

        return nextNodes;
      });

      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [nodes, links, draggedNode]);

  // Drag operations handlers
  const handleMouseDown = (node, e) => {
    setDraggedNode(node);
    setSelectedNode(node);
  };

  const handleMouseMove = (e) => {
    if (!draggedNode || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setNodes(prev => prev.map(n => n.id === draggedNode.id ? { ...n, x, y } : n));
  };

  const handleMouseUp = () => {
    setDraggedNode(null);
  };

  const handleResetLayout = () => {
    setNodes(prev => prev.map(n => ({
      ...n,
      x: Math.random() * 300 + 150,
      y: Math.random() * 200 + 100
    })));
  };

  const getNodeColor = (type) => {
    switch (type) {
      case 'technology': return '#00f0ff';
      case 'concept': return '#bd00ff';
      default: return '#00ffaa';
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in h-[calc(100vh-12rem)] overflow-hidden">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] pb-4 shrink-0">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <GitBranch size={20} className="text-purple-400" />
            Knowledge Graph SQLite Network
          </h2>
          <p className="text-xs text-slate-400 mt-1">Interactive network mapping personal concepts, technology dependencies, and preferences.</p>
        </div>
        <button 
          onClick={handleResetLayout}
          className="btn-secondary text-xs flex items-center gap-2 cursor-pointer"
        >
          <RotateCcw size={12} /> RESET_LAYOUT
        </button>
      </div>

      {/* Main split: SVG canvas + details sidebar */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* SVG Canvas Board */}
        <div className="flex-1 glass-panel bg-black/30 border-purple-500/10 rounded-xl relative overflow-hidden flex items-center justify-center">
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="w-full h-full select-none cursor-grab active:cursor-grabbing"
          >
            {/* Draw Links */}
            {links.map((link, idx) => {
              const source = nodes.find(n => n.id === link.source);
              const target = nodes.find(n => n.id === link.target);
              if (!source || !target) return null;
              const isLinkedToSelected = selectedNode && (selectedNode.id === source.id || selectedNode.id === target.id);
              return (
                <line
                  key={idx}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={isLinkedToSelected ? 'rgba(0, 240, 255, 0.4)' : 'rgba(255,255,255,0.06)'}
                  strokeWidth={isLinkedToSelected ? 2 : 1}
                  strokeDasharray={isLinkedToSelected ? '4 2' : 'none'}
                />
              );
            })}

            {/* Draw Nodes */}
            {nodes.map(node => {
              const isSelected = selectedNode?.id === node.id;
              const strokeColor = getNodeColor(node.type);
              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onMouseDown={(e) => handleMouseDown(node, e)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Outer glowing halo on select */}
                  {isSelected && (
                    <circle r="22" fill="none" stroke={strokeColor} strokeWidth="1.5" strokeOpacity="0.4" className="animate-ping" />
                  )}
                  {/* Node Circle */}
                  <circle
                    r="14"
                    fill="#0f131a"
                    stroke={isSelected ? '#fff' : strokeColor}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                  />
                  {/* Node Initial Label */}
                  <text
                    dy="3"
                    textAnchor="middle"
                    fill="#fff"
                    fontSize="9px"
                    fontWeight="bold"
                    fontFamily="var(--font-mono)"
                  >
                    {node.label.substring(0, 2).toUpperCase()}
                  </text>
                  {/* Node Text Label */}
                  <text
                    y="24"
                    textAnchor="middle"
                    fill={isSelected ? '#fff' : 'var(--color-text-primary)'}
                    fontSize="9px"
                    fontWeight={500}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* SVG Help hints */}
          <div className="absolute bottom-3 left-4 text-[10px] text-slate-500">
            [Drag nodes to organize • Select vertices to audit schemas]
          </div>
        </div>

        {/* Node inspector panel side */}
        <div className="w-80 glass-panel p-5 flex flex-col gap-4 bg-[#0d1017ab]">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
            <Info size={14} className="text-purple-400 animate-pulse" />
            Vertex Inspector
          </h4>

          {selectedNode ? (
            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-white">{selectedNode.label}</span>
                <span className="badge badge-cyan text-[9px] capitalize">{selectedNode.type}</span>
              </div>
              <div className="text-xs text-slate-300 leading-relaxed bg-black/20 p-3 rounded-lg border border-[rgba(255,255,255,0.04)]">
                {selectedNode.desc}
              </div>
              
              <div className="flex flex-col gap-1 mt-2 text-[10px] text-slate-500">
                <span>DATABASE: sqlite3</span>
                <span>TABLE: entities</span>
                <span>STRENGTH WEIGHT: 1.0</span>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 text-xs gap-2 py-10">
              <span>Select a node on the graph to audit SQLite details.</span>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
