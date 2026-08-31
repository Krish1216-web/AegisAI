import React from 'react';
import { X, Trash2, GitCommit, Sliders, Activity } from 'lucide-react';

export default function WorkflowEdgeEditor({
  selectedEdge,
  allNodes,
  onUpdateEdge,
  onDeleteEdge,
  onClose
}) {
  if (!selectedEdge) return null;

  const sourceNode = allNodes.find((n) => n.id === selectedEdge.source);
  const targetNode = allNodes.find((n) => n.id === selectedEdge.target);

  const priority = selectedEdge.data?.priority || 1;
  const condition = selectedEdge.data?.condition || '';

  const handlePriorityChange = (val) => {
    onUpdateEdge(selectedEdge.id, {
      ...selectedEdge.data,
      priority: parseInt(val, 10) || 1
    });
  };

  const handleConditionChange = (val) => {
    onUpdateEdge(selectedEdge.id, {
      ...selectedEdge.data,
      condition: val
    });
  };

  return (
    <aside className="w-80 bg-slate-950/90 border-l border-slate-800 flex flex-col h-full overflow-hidden select-none z-10 backdrop-blur-md">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Edge Connection
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onDeleteEdge(selectedEdge.id)}
            className="p-1 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
            title="Delete Connection"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-4 text-xs">
        {/* Source -> Target Connection Info */}
        <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80 space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-medium">Source Node:</span>
            <span className="font-mono text-indigo-300 font-semibold truncate max-w-[130px]">
              {sourceNode?.data?.name || sourceNode?.data?.node_key || selectedEdge.source}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-medium">Target Node:</span>
            <span className="font-mono text-cyan-300 font-semibold truncate max-w-[130px]">
              {targetNode?.data?.name || targetNode?.data?.node_key || selectedEdge.target}
            </span>
          </div>
        </div>

        {/* Priority */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
            Execution Priority
          </label>
          <input
            type="number"
            min="1"
            max="100"
            value={priority}
            onChange={(e) => handlePriorityChange(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          />
          <p className="text-[10px] text-slate-500">
            Higher priority branches execute first during parallel transitions.
          </p>
        </div>

        {/* Optional Condition Expression */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
            Conditional Guard (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. {{nodes.cond_1.output.result}} == true"
            value={typeof condition === 'string' ? condition : JSON.stringify(condition)}
            onChange={(e) => handleConditionChange(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 font-mono text-[11px] text-yellow-300 focus:outline-none focus:border-yellow-500"
          />
        </div>
      </div>
    </aside>
  );
}
