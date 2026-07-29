import React, { useState } from 'react';
import { ListTodo, CheckCircle, Clock, AlertCircle, Plus, Play, Sparkles } from 'lucide-react';

export default function UserTasks({ triggerNotification }) {
  const [tasks, setTasks] = useState([
    { id: '1', name: 'Extract project imports', column: 'completed', priority: 'high', agent: 'Research', time: '12s', deadline: 'Today' },
    { id: '2', name: 'Backup workspace files', column: 'running', priority: 'medium', agent: 'Executor', time: '34s', deadline: 'Today' },
    { id: '3', name: 'Vectorise user settings', column: 'pending', priority: 'low', agent: 'Memory', time: 'Pending', deadline: 'Tomorrow' },
    { id: '4', name: 'Re-run SQLite constraints', column: 'pending', priority: 'high', agent: 'Executor', time: 'Pending', deadline: 'Today' }
  ]);

  const handleCreateTask = () => {
    const newTask = {
      id: String(tasks.length + 1),
      name: `User custom task #${tasks.length + 1}`,
      column: 'pending',
      priority: 'medium',
      agent: 'Orchestrator',
      time: 'Pending',
      deadline: 'Tomorrow'
    };
    setTasks(prev => [...prev, newTask]);
    triggerNotification('Task Created', 'Added new task item to Pending queue.');
  };

  const moveTask = (taskId, nextCol) => {
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, column: nextCol, time: nextCol === 'running' ? '1s' : (nextCol === 'completed' ? '12s' : 'Pending') } : t));
    triggerNotification('Task Shifted', `Task #${taskId} moved to: ${nextCol.toUpperCase()}`);
  };

  const getPriorityColor = (prio) => {
    switch (prio) {
      case 'high': return 'text-rose-400 border-rose-500/20 bg-rose-500/5';
      case 'medium': return 'text-yellow-400 border-yellow-500/20 bg-yellow-500/5';
      default: return 'text-green-400 border-green-500/20 bg-green-500/5';
    }
  };

  const renderColumn = (colName, colTitle, icon) => {
    const colTasks = tasks.filter(t => t.column === colName);
    return (
      <div className="flex flex-col gap-4 flex-1">
        {/* Column Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] pb-3 px-1">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
            {icon}
            {colTitle}
          </div>
          <span className="text-[10px] text-slate-500 font-bold bg-white/5 border border-[rgba(255,255,255,0.08)] px-1.5 py-0.5 rounded">
            {colTasks.length}
          </span>
        </div>

        {/* Task Cards Stack */}
        <div className="flex flex-col gap-3 min-h-[300px] bg-white/1 rounded-xl p-3 border border-[rgba(255,255,255,0.02)]">
          {colTasks.map((t) => (
            <div key={t.id} className="p-4 rounded-lg bg-[#0d1017ab] border border-[rgba(255,255,255,0.04)] flex flex-col gap-3 hover:border-cyan-500/20 transition-all select-none">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-200">{t.name}</span>
                <span className={`text-[8px] font-bold uppercase tracking-wider border px-1.5 py-0.5 rounded ${getPriorityColor(t.priority)}`}>
                  {t.priority}
                </span>
              </div>

              {/* Specs */}
              <div className="flex justify-between items-center text-[10px] text-slate-500">
                <span>Agent: <strong className="text-slate-400">{t.agent}</strong></span>
                <span>Time: {t.time}</span>
              </div>

              {/* Actions & controls */}
              <div className="flex justify-between items-center border-t border-[rgba(255,255,255,0.03)] pt-2.5 mt-1">
                <span className="text-[8px] text-slate-500">Due: {t.deadline}</span>
                <div className="flex gap-1.5">
                  {colName === 'pending' && (
                    <button 
                      onClick={() => moveTask(t.id, 'running')}
                      className="text-[9px] text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 px-2 py-0.5 rounded cursor-pointer border border-cyan-500/20 font-semibold"
                    >
                      Run
                    </button>
                  )}
                  {colName === 'running' && (
                    <button 
                      onClick={() => moveTask(t.id, 'completed')}
                      className="text-[9px] text-green-400 bg-green-500/10 hover:bg-green-500/20 px-2 py-0.5 rounded cursor-pointer border border-green-500/20 font-semibold"
                    >
                      Finish
                    </button>
                  )}
                  {colName === 'completed' && (
                    <span className="text-[8px] text-green-400 font-semibold">Done ✓</span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {colTasks.length === 0 && (
            <div className="flex-1 flex items-center justify-center text-center text-slate-600 text-[10px] py-16">
              Column is empty.
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      
      {/* Header title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <ListTodo size={20} className="text-cyan-400" />
            Agent Task Queue Kanban
          </h2>
          <p className="text-xs text-slate-400 mt-1">Audit and organize agent priorities in the active execution queue.</p>
        </div>
        <button 
          onClick={handleCreateTask}
          className="btn-primary text-xs flex items-center gap-2 cursor-pointer shadow-lg shadow-cyan-500/10"
        >
          <Plus size={14} /> NEW_QUEUE_TASK
        </button>
      </div>

      {/* Board Columns list */}
      <div className="flex flex-col md:flex-row gap-5">
        {renderColumn('pending', 'Pending', <Clock size={12} className="text-yellow-400" />)}
        {renderColumn('running', 'Running', <Sparkles size={12} className="text-cyan-400 animate-pulse" />)}
        {renderColumn('completed', 'Completed', <CheckCircle size={12} className="text-green-400" />)}
      </div>

    </div>
  );
}
