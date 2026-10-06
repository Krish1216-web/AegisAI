import React from 'react';
import { FileText, Database, ShieldCheck, GitBranch, ExternalLink } from 'lucide-react';
import { DEMO_KNOWLEDGE_GRAPH } from '../../data/demoScenarios';

export function DemoEvidenceViewer({ evidence, showGraph = true }) {
  return (
    <div className="flex flex-col gap-4">
      {/* Evidence Citations */}
      <div className="p-4 rounded-xl border border-white/10 bg-[#0d1017] flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <ShieldCheck size={14} className="text-emerald-400" />
            Grounding Evidence & Citations ({evidence ? evidence.length : 0})
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-bold">
            100% VERIFIABLE
          </span>
        </div>

        {(!evidence || evidence.length === 0) ? (
          <div className="py-6 text-center text-xs text-slate-500 italic">
            No active evidence items in current step.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {evidence.map((item) => (
              <div
                key={item.id}
                className="p-3.5 rounded-lg border border-white/10 bg-white/[0.02] flex flex-col justify-between gap-2.5 hover:border-cyan-500/30 transition-all"
              >
                <div className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-cyan-300 truncate">
                      {item.source}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-400 font-mono">
                      {item.type}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {item.section}
                  </span>
                  <p className="text-xs text-slate-300 italic border-l-2 border-cyan-500/40 pl-2.5 mt-1 leading-relaxed">
                    "{item.excerpt}"
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-white/[0.06] text-[10px] text-slate-400 font-mono">
                  <span>Confidence: {(item.confidence * 100).toFixed(1)}%</span>
                  <span className="text-emerald-400 flex items-center gap-1">
                    <ShieldCheck size={11} />
                    Verified Hash
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Synthetic Knowledge Graph Visualizer */}
      {showGraph && (
        <div className="p-4 rounded-xl border border-white/10 bg-[#0a0d14] flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <GitBranch size={14} className="text-teal-400" />
              Synthetic Knowledge Graph (Triples Explorer)
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/20 font-mono">
              7 NODES :: 7 EDGES
            </span>
          </div>

          {/* Render Responsive SVG Graph */}
          <div className="relative w-full h-56 rounded-lg bg-[#07090e] border border-white/5 overflow-hidden flex items-center justify-center">
            <svg className="w-full h-full" viewBox="0 0 550 320">
              {/* Render Edges */}
              {DEMO_KNOWLEDGE_GRAPH.edges.map((edge, i) => {
                const source = DEMO_KNOWLEDGE_GRAPH.nodes.find(n => n.id === edge.from);
                const target = DEMO_KNOWLEDGE_GRAPH.nodes.find(n => n.id === edge.to);
                if (!source || !target) return null;
                const midX = (source.x + target.x) / 2;
                const midY = (source.y + target.y) / 2;
                return (
                  <g key={`edge-${i}`}>
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke="rgba(255,255,255,0.15)"
                      strokeWidth="1.5"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={midX}
                      y={midY - 4}
                      fill="#64748b"
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {edge.label}
                    </text>
                  </g>
                );
              })}

              {/* Render Nodes */}
              {DEMO_KNOWLEDGE_GRAPH.nodes.map((node) => (
                <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                  <circle
                    r="16"
                    fill="#0d1017"
                    stroke={node.color}
                    strokeWidth="2.5"
                    className="transition-all hover:scale-110"
                  />
                  <circle r="4" fill={node.color} />
                  <text
                    y="26"
                    fill="#cbd5e1"
                    fontSize="9.5"
                    fontWeight="600"
                    fontFamily="sans-serif"
                    textAnchor="middle"
                  >
                    {node.label}
                  </text>
                  <text
                    y="36"
                    fill="#64748b"
                    fontSize="7.5"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    [{node.type}]
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}
