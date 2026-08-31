import React, { useState } from 'react';
import { X, Plus, Trash2, Key, Eye, EyeOff, Variable } from 'lucide-react';

export default function WorkflowVariablesPanel({
  variables = [],
  onChangeVariables,
  onClose
}) {
  const [showSecrets, setShowSecrets] = useState({});

  const handleAdd = () => {
    const nextVar = {
      name: `var_${variables.length + 1}`,
      value_type: 'string',
      value: '',
      is_secret: false
    };
    onChangeVariables([...variables, nextVar]);
  };

  const handleUpdate = (index, field, val) => {
    const updated = [...variables];
    updated[index] = { ...updated[index], [field]: val };
    onChangeVariables(updated);
  };

  const handleRemove = (index) => {
    const updated = variables.filter((_, i) => i !== index);
    onChangeVariables(updated);
  };

  const toggleShowSecret = (index) => {
    setShowSecrets((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col p-6 shadow-2xl overflow-hidden select-none">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Variable className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">Workflow Variables</h3>
              <p className="text-xs text-slate-400">
                Variables referenced via {'{{variables.<name>}}'} across workflow nodes.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Variables List */}
        <div className="flex-1 overflow-y-auto py-4 space-y-3">
          {variables.map((v, idx) => (
            <div
              key={idx}
              className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center gap-3 text-xs"
            >
              {/* Name */}
              <div className="flex-1 min-w-[120px]">
                <label className="text-[10px] text-slate-500 block mb-0.5">Variable Name</label>
                <input
                  type="text"
                  value={v.name}
                  onChange={(e) => handleUpdate(idx, 'name', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 font-mono text-indigo-300 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Value Type */}
              <div className="w-28">
                <label className="text-[10px] text-slate-500 block mb-0.5">Type</label>
                <select
                  value={v.value_type || 'string'}
                  onChange={(e) => handleUpdate(idx, 'value_type', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="json">json</option>
                </select>
              </div>

              {/* Value */}
              <div className="flex-1 min-w-[140px] relative">
                <label className="text-[10px] text-slate-500 block mb-0.5">Default Value</label>
                <input
                  type={v.is_secret && !showSecrets[idx] ? 'password' : 'text'}
                  value={v.value || ''}
                  onChange={(e) => handleUpdate(idx, 'value', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                />
                {v.is_secret && (
                  <button
                    type="button"
                    onClick={() => toggleShowSecret(idx)}
                    className="absolute right-2 top-6 text-slate-500 hover:text-slate-300"
                  >
                    {showSecrets[idx] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>

              {/* Secret Flag */}
              <div className="flex flex-col items-center justify-center pt-3">
                <label className="text-[9px] text-slate-500 block mb-0.5">Secret</label>
                <input
                  type="checkbox"
                  checked={v.is_secret || false}
                  onChange={(e) => handleUpdate(idx, 'is_secret', e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-800"
                />
              </div>

              {/* Delete */}
              <div className="pt-3">
                <button
                  type="button"
                  onClick={() => handleRemove(idx)}
                  className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}

          {variables.length === 0 && (
            <div className="text-center py-8 text-slate-500 text-xs italic">
              No variables defined for this workflow yet.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={handleAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Variable
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
