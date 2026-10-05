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
  Copy,
  Calendar,
  FileText
} from 'lucide-react';
import {
  Button,
  IconButton,
  Badge,
  StatusBadge
} from '../ui';

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
  onOpenOutline,
  onUpdateMetadata
}) {
  const navigate = useNavigate();
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [title, setTitle] = useState(workflow?.name || '');

  const status = workflow?.status || 'draft';

  return (
    <header className="h-14 bg-slate-950/90 border-b border-white/[0.08] px-4 flex items-center justify-between gap-3 select-none z-20 backdrop-blur-md">
      {/* Left: Back & Title */}
      <div className="flex items-center gap-3">
        <IconButton
          variant="secondary"
          size="sm"
          onClick={() => navigate('/user/workflows')}
          title="Back to Workflows"
          aria-label="Back to Workflows"
        >
          <ArrowLeft size={14} />
        </IconButton>

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
              className="bg-[#0d1117] border border-indigo-500 rounded-lg px-2.5 py-1 text-xs font-bold text-white focus:outline-none"
            />
          ) : (
            <h2
              onClick={() => {
                setTitle(workflow?.name || '');
                setIsEditingTitle(true);
              }}
              className="text-xs font-bold text-white hover:text-indigo-300 cursor-pointer transition flex items-center gap-1.5"
              title="Click to rename workflow"
            >
              {workflow?.name || 'Untitled Workflow'}
            </h2>
          )}

          <Badge variant="slate" className="font-mono text-[10px]">
            v{workflow?.version || 1}
          </Badge>

          <StatusBadge status={status} label={status.toUpperCase()} />

          {isDirty && (
            <span className="text-[10px] font-semibold text-amber-400 flex items-center gap-1">
              • Unsaved changes
            </span>
          )}
        </div>
      </div>

      {/* Middle: Canvas Tools */}
      <div className="hidden md:flex items-center gap-1 bg-black/40 p-1 rounded-xl border border-white/[0.06]">
        <IconButton
          variant="ghost"
          size="sm"
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo"
          aria-label="Undo"
        >
          <Undo2 size={13} />
        </IconButton>

        <IconButton
          variant="ghost"
          size="sm"
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo"
          aria-label="Redo"
        >
          <Redo2 size={13} />
        </IconButton>

        <div className="w-[1px] h-4 bg-white/10 mx-1" />

        <IconButton
          variant="ghost"
          size="sm"
          onClick={onAutoLayout}
          title="Auto Layout (Topological)"
          aria-label="Auto Layout"
        >
          <Layers size={13} />
        </IconButton>

        <IconButton
          variant="ghost"
          size="sm"
          onClick={onFitView}
          title="Fit View"
          aria-label="Fit View"
        >
          <Maximize2 size={13} />
        </IconButton>

        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenVariables}
          className="text-xs py-1 px-2 flex items-center gap-1 text-slate-300 hover:text-amber-300"
          title="Workflow Variables"
        >
          <Variable size={13} />
          <span>Variables</span>
        </Button>

        <IconButton
          variant="ghost"
          size="sm"
          onClick={onOpenOutline}
          title="Accessible Text Outline"
          aria-label="Accessible Text Outline"
        >
          <FileText size={13} />
        </IconButton>

        <IconButton
          variant="ghost"
          size="sm"
          onClick={onCloneWorkflow}
          title="Clone Workflow"
          aria-label="Clone Workflow"
        >
          <Copy size={13} />
        </IconButton>
      </div>

      {/* Right: Primary Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={onValidate}
          disabled={isValidating}
          className="text-xs py-1.5 px-3 flex items-center gap-1.5"
        >
          <CheckCircle2 size={13} className={isValidating ? 'animate-spin text-indigo-400' : 'text-slate-400'} />
          Validate
        </Button>

        {status === 'active' ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={onToggleStatus}
            className="text-xs py-1.5 px-2.5 text-amber-300 border-amber-500/30 hover:bg-amber-500/10 flex items-center gap-1"
          >
            <Pause size={12} />
            Pause
          </Button>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={onToggleStatus}
            className="text-xs py-1.5 px-2.5 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/10 flex items-center gap-1"
          >
            <Play size={12} />
            Activate
          </Button>
        )}

        <Button
          variant="primary"
          size="sm"
          onClick={onRunWorkflow}
          className="text-xs py-1.5 px-3 flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white"
        >
          <Play size={12} />
          Run
        </Button>

        <Button
          variant="primary"
          size="sm"
          onClick={onSave}
          disabled={isSaving}
          className="text-xs py-1.5 px-3.5 flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
        >
          <Save size={13} className={isSaving ? 'animate-spin' : ''} />
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </header>
  );
}
