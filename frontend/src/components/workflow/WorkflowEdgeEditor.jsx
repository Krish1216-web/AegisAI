import React, { useState, useEffect } from 'react';
import { X, Trash2, GitCommit, Plus, Split, CheckCircle2, AlertCircle } from 'lucide-react';

const COMPARISON_OPERATORS = [
  { value: 'equals', label: 'equals (==)' },
  { value: 'not_equals', label: 'not_equals (!=)' },
  { value: 'greater_than', label: 'greater_than (>)' },
  { value: 'less_than', label: 'less_than (<)' },
  { value: 'greater_or_equal', label: 'greater_or_equal (>=)' },
  { value: 'less_or_equal', label: 'less_or_equal (<=)' },
  { value: 'contains', label: 'contains' },
  { value: 'not_contains', label: 'not_contains' },
  { value: 'in', label: 'in list' },
  { value: 'not_in', label: 'not_in list' },
  { value: 'starts_with', label: 'starts_with' },
  { value: 'ends_with', label: 'ends_with' },
  { value: 'exists', label: 'exists (not empty)' },
  { value: 'not_exists', label: 'not_exists (is empty)' }
];

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
  const rawCondition = selectedEdge.data?.condition || null;

  // Determine mode: 'none' | 'default' | 'single' | 'group'
  const getInitialMode = () => {
    if (!rawCondition) return 'none';
    if (rawCondition.is_default === true) return 'default';
    if (rawCondition.logic || Array.isArray(rawCondition.conditions)) return 'group';
    return 'single';
  };

  const [mode, setMode] = useState(getInitialMode);

  // Synchronize state on edge selection change
  useEffect(() => {
    setMode(getInitialMode());
  }, [selectedEdge.id]);

  const handlePriorityChange = (val) => {
    onUpdateEdge(selectedEdge.id, {
      ...selectedEdge.data,
      priority: parseInt(val, 10) || 1
    });
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    if (newMode === 'none') {
      onUpdateEdge(selectedEdge.id, { ...selectedEdge.data, condition: null });
    } else if (newMode === 'default') {
      onUpdateEdge(selectedEdge.id, { ...selectedEdge.data, condition: { is_default: true } });
    } else if (newMode === 'single') {
      onUpdateEdge(selectedEdge.id, {
        ...selectedEdge.data,
        condition: {
          left: '{{input.value}}',
          operator: 'equals',
          right: 'true'
        }
      });
    } else if (newMode === 'group') {
      onUpdateEdge(selectedEdge.id, {
        ...selectedEdge.data,
        condition: {
          logic: 'AND',
          conditions: [
            { left: '{{input.value}}', operator: 'equals', right: 'true' }
          ]
        }
      });
    }
  };

  // Update single condition field
  const updateSingleField = (field, value) => {
    const current = typeof rawCondition === 'object' && rawCondition ? { ...rawCondition } : {};
    delete current.is_default;
    delete current.logic;
    delete current.conditions;
    current[field] = value;
    onUpdateEdge(selectedEdge.id, {
      ...selectedEdge.data,
      condition: current
    });
  };

  // Update group condition
  const updateGroupLogic = (logic) => {
    const current = typeof rawCondition === 'object' && rawCondition ? { ...rawCondition } : {};
    onUpdateEdge(selectedEdge.id, {
      ...selectedEdge.data,
      condition: {
        ...current,
        logic,
        conditions: current.conditions || []
      }
    });
  };

  const addGroupRule = () => {
    const current = typeof rawCondition === 'object' && rawCondition ? { ...rawCondition } : {};
    const conditions = Array.isArray(current.conditions) ? [...current.conditions] : [];
    conditions.push({ left: '{{input.x}}', operator: 'equals', right: '' });
    onUpdateEdge(selectedEdge.id, {
      ...selectedEdge.data,
      condition: {
        logic: current.logic || 'AND',
        conditions
      }
    });
  };

  const updateGroupRule = (index, field, value) => {
    const current = typeof rawCondition === 'object' && rawCondition ? { ...rawCondition } : {};
    const conditions = Array.isArray(current.conditions) ? [...current.conditions] : [];
    if (conditions[index]) {
      conditions[index] = { ...conditions[index], [field]: value };
      onUpdateEdge(selectedEdge.id, {
        ...selectedEdge.data,
        condition: {
          ...current,
          conditions
        }
      });
    }
  };

  const removeGroupRule = (index) => {
    const current = typeof rawCondition === 'object' && rawCondition ? { ...rawCondition } : {};
    const conditions = Array.isArray(current.conditions) ? [...current.conditions] : [];
    conditions.splice(index, 1);
    onUpdateEdge(selectedEdge.id, {
      ...selectedEdge.data,
      condition: {
        ...current,
        conditions
      }
    });
  };

  return (
    <aside className="w-84 bg-slate-950/95 border-l border-slate-800 flex flex-col h-full overflow-hidden select-none z-10 backdrop-blur-md">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Split className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Edge Branch Router
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

      <div className="p-4 space-y-4 text-xs overflow-y-auto flex-1 custom-scrollbar">
        {/* Source -> Target Connection Info */}
        <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80 space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-medium">Source:</span>
            <span className="font-mono text-indigo-300 font-semibold truncate max-w-[130px]">
              {sourceNode?.data?.name || sourceNode?.data?.node_key || selectedEdge.source}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-medium">Target:</span>
            <span className="font-mono text-cyan-300 font-semibold truncate max-w-[130px]">
              {targetNode?.data?.name || targetNode?.data?.node_key || selectedEdge.target}
            </span>
          </div>
        </div>

        {/* Priority */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
            Branch Priority
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={priority}
            onChange={(e) => handlePriorityChange(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          />
          <p className="text-[10px] text-slate-500">
            Higher priority branches are evaluated first during multi-way routing.
          </p>
        </div>

        {/* Routing Type Selector */}
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
            Routing Guard Type
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            <button
              onClick={() => handleModeChange('none')}
              className={`py-1.5 px-2 rounded-lg text-[10px] font-medium border text-center transition ${
                mode === 'none'
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
              }`}
            >
              Always Run
            </button>
            <button
              onClick={() => handleModeChange('default')}
              className={`py-1.5 px-2 rounded-lg text-[10px] font-medium border text-center transition ${
                mode === 'default'
                  ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
              }`}
            >
              Default Fallback
            </button>
            <button
              onClick={() => handleModeChange('single')}
              className={`py-1.5 px-2 rounded-lg text-[10px] font-medium border text-center transition ${
                mode === 'single'
                  ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
              }`}
            >
              Single Rule
            </button>
            <button
              onClick={() => handleModeChange('group')}
              className={`py-1.5 px-2 rounded-lg text-[10px] font-medium border text-center transition ${
                mode === 'group'
                  ? 'bg-purple-500/20 border-purple-500/50 text-purple-300'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
              }`}
            >
              Condition Group
            </button>
          </div>
        </div>

        {/* DEFAULT FALLBACK EXPLANATION */}
        {mode === 'default' && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300/90 text-[11px] leading-relaxed space-y-1">
            <div className="font-semibold flex items-center gap-1.5 text-amber-400">
              <CheckCircle2 className="w-3.5 h-3.5" /> Default Fallback Branch
            </div>
            <p>
              This branch will execute automatically if none of the other conditional branches from the source node evaluate to true.
            </p>
          </div>
        )}

        {/* SINGLE CONDITION BUILDER */}
        {mode === 'single' && (
          <div className="space-y-3 p-3 bg-slate-900/70 border border-slate-800 rounded-xl">
            <div>
              <label className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                Left Operand
              </label>
              <input
                type="text"
                placeholder="e.g. {{nodes.agent_1.output.score}}"
                value={rawCondition?.left || ''}
                onChange={(e) => updateSingleField('left', e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-[11px] text-yellow-300 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                Operator
              </label>
              <select
                value={rawCondition?.operator || 'equals'}
                onChange={(e) => updateSingleField('operator', e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
              >
                {COMPARISON_OPERATORS.map((op) => (
                  <option key={op.value} value={op.value}>
                    {op.label}
                  </option>
                ))}
              </select>
            </div>

            {!['exists', 'not_exists'].includes(rawCondition?.operator) && (
              <div>
                <label className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                  Right Operand
                </label>
                <input
                  type="text"
                  placeholder="e.g. 0.8 or approved"
                  value={rawCondition?.right !== undefined ? String(rawCondition.right) : ''}
                  onChange={(e) => updateSingleField('right', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-[11px] text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            )}
          </div>
        )}

        {/* CONDITION GROUP BUILDER */}
        {mode === 'group' && (
          <div className="space-y-3 p-3 bg-slate-900/70 border border-slate-800 rounded-xl">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase text-slate-400">Match Logic</span>
              <div className="flex gap-1">
                {['AND', 'OR', 'NOT'].map((lg) => (
                  <button
                    key={lg}
                    onClick={() => updateGroupLogic(lg)}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                      (rawCondition?.logic || 'AND').toUpperCase() === lg
                        ? 'bg-purple-500 text-white'
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {lg}
                  </button>
                ))}
              </div>
            </div>

            {/* List of Rules */}
            <div className="space-y-2.5">
              {(rawCondition?.conditions || []).map((rule, idx) => (
                <div key={idx} className="p-2.5 bg-slate-950 border border-slate-800/80 rounded-lg space-y-2">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="font-bold text-slate-400">Rule #{idx + 1}</span>
                    <button
                      onClick={() => removeGroupRule(idx)}
                      className="text-slate-500 hover:text-rose-400"
                      title="Remove rule"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                  <input
                    type="text"
                    placeholder="Left (e.g. {{input.status}})"
                    value={rule.left || ''}
                    onChange={(e) => updateGroupRule(idx, 'left', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 font-mono text-[10px] text-yellow-300"
                  />
                  <select
                    value={rule.operator || 'equals'}
                    onChange={(e) => updateGroupRule(idx, 'operator', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded p-1 text-[10px] text-slate-200"
                  >
                    {COMPARISON_OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>
                        {op.label}
                      </option>
                    ))}
                  </select>
                  {!['exists', 'not_exists'].includes(rule.operator) && (
                    <input
                      type="text"
                      placeholder="Right (e.g. active)"
                      value={rule.right !== undefined ? String(rule.right) : ''}
                      onChange={(e) => updateGroupRule(idx, 'right', e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 font-mono text-[10px] text-slate-200"
                    />
                  )}
                </div>
              ))}
            </div>

            {/* Add Rule Button */}
            <button
              onClick={addGroupRule}
              className="w-full py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[10px] font-semibold flex items-center justify-center gap-1.5 transition"
            >
              <Plus className="w-3 h-3" /> Add Condition Rule
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
