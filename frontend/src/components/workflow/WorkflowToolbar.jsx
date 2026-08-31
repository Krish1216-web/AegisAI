import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  CheckCircle2,
  Play,
  Pause,
  Variable,
  Layers,
  Undo2,
  Redo2,
  Maximize2,
  RefreshCw,
  AlertCircle,
  Copy
} from 'lucide-react';

export default function WorkflowToolbar({
  workflow,
  isDirty,
  isSaving,
  isValidating,
  validationResult,
  onSave,
  onValidate,
  onToggleStatus,
  onOpenVariables,
  onAutoLayout,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  onFitView,
  onRunWorkflow,
  onCloneWorkflow,
  onUpdateMetadata
}) {
  const navigate = useNavigate();
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [title, setTitle] = useState(workflow?.name || '');

  const status = workflow?.status || 'draft';

  return (
    <header className="h-14 bg-slate-950/90 border-b border-slate-800 px-4 flex items-center justify-between gap-3 select-none z-20 backdrop-blur-md">
      {/* Left: Back & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/user/workflows')}
          className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-900 border border-slate-800 transition"
          title="Back to Workflows"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2">
          {isEditingTitle ? (
            <input
              type="text"
              value={title}
              autoFocus
              onBlur={() => {
                setIsEditingTitle(false);
                if (title.trim() && title !== workflow?.name) {
                  onUpdateMetadata({ name: title.trim() });
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setIsEditingTitle(false);
                  if (title.trim() && title !== workflow?.name) {
                    onUpdateMetadata({ name: title.trim() });
                  }
                } else if (e.key === 'Escape') {
                  setIsEditingTitle(false);
                  setTitle(workflow?.name || '');
                }
              }}
              onChange={(e) => setTitle(e.target.value)}
              className="bg-slate-900 border border-indigo-500 rounded-lg px-2.5 py-1 text-sm font-bold text-slate-100 focus:outline-none"
            />
          ) : (
            <h2
              onClick={() => {
                setTitle(workflow?.name || '');
                setIsEditingTitle(true);
              }}
              className="text-sm font-bold text-slate-100 hover:text-indigo-300 cursor-pointer transition flex items-center gap-2"
              title="Click to rename workflow"
            >
              {workflow?.name || 'Untitled Workflow'}
            </h2>
          )}

          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800">
            v{workflow?.version || 1}
          </span>

          <span
            className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
              status === 'active'
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : status === 'paused'
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                : 'bg-slate-900 text-slate-400 border border-slate-800'
            }`}
          >
            {status}
          </span>

          {isDirty && (
            <span className="text-[10px] font-semibold text-amber-400 flex items-center gap-1">
              • Unsaved changes
            </span>
          )}
        </div>
      </div>

      {/* Middle: Canvas Tools */}
      <div className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800/80">
        <button
          onClick={onUndo}
          disabled={!canUndo}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:hover:text-slate-400 hover:bg-slate-800 transition"
          title="Undo"
        >
          <Undo2 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:hover:text-slate-400 hover:bg-slate-800 transition"
          title="Redo"
        >
          <Redo2 className="w-3.5 h-3.5" />
        </button>
        <div className="w-[1px] h-4 bg-slate-800 mx-1" />
        <button
          onClick={onAutoLayout}
          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 transition"
          title="Auto Layout (Topological)"
        >
          <Layers className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onFitView}
          className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition"
          title="Fit View"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onOpenVariables}
          className="flex items-center gap-1 px-2 py-1 rounded-lg text-slate-300 hover:text-amber-300 hover:bg-slate-800 text-[11px] font-medium transition"
          title="Workflow Variables"
        >
          <Variable className="w-3.5 h-3.5" />
          <span>Variables</span>
        </button>
        <button
          onClick={onCloneWorkflow}
          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 transition"
          title="Clone Workflow"
        >
          <Copy className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onValidate}
          disabled={isValidating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 text-xs font-medium border border-slate-800 transition"
        >
          <CheckCircle2 className={`w-3.5 h-3.5 ${isValidating ? 'animate-spin text-indigo-400' : 'text-slate-400'}`} />
          Validate
        </button>

        {status === 'active' ? (
          <button
            onClick={onToggleStatus}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 text-xs font-semibold transition"
          >
            <Pause className="w-3.5 h-3.5" />
            Pause
          </button>
        ) : (
          <button
            onClick={onToggleStatus}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/20 text-xs font-semibold transition"
          >
            <Play className="w-3.5 h-3.5" />
            Activate
          </button>
        )}

        <button
          onClick={onRunWorkflow}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-600/20 transition"
        >
          <Play className="w-3.5 h-3.5" />
          Run
        </button>

        <button
          onClick={onSave}
          disabled={isSaving}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition"
        >
          <Save className={`w-3.5 h-3.5 ${isSaving ? 'animate-spin' : ''}`} />
          Save
        </button>
      </div>
    </header>
  );
}
