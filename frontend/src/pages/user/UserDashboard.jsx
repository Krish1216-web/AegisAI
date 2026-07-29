import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bot, 
  CheckCircle, 
  Database, 
  Server, 
  Sparkles, 
  ArrowUpRight, 
  FileText, 
  Plus, 
  Bookmark, 
  Clock,
  TrendingUp,
  Workflow,
  Calendar,
  AlertCircle,
  Activity,
  Play,
  Settings,
  MessageSquare,
  HardDrive
} from 'lucide-react';

export default function UserDashboard({ triggerNotification }) {
  const navigate = useNavigate();

  // Daily goals state
  const [goals, setGoals] = useState([
    { id: '1', text: 'Audit python parser commit hooks', completed: true },
    { id: '2', text: 'Index database schema v4 vectors', completed: false },
    { id: '3', text: 'Map AWS Cloud MCP S3 buckets', completed: false }
  ]);

  const toggleGoal = (id) => {
    setGoals(prev => prev.map(g => {
      if (g.id === id) {
        const nextState = !g.completed;
        triggerNotification(nextState ? 'Goal Completed' : 'Goal Reset', `Goal "${g.text}" updated.`);
        return { ...g, completed: nextState };
      }
      return g;
    }));
  };

  const stats = [
    { label: 'AI Productivity Score', value: '94%', detail: 'Optimum efficiency rating', icon: <TrendingUp size={16} className="text-cyan-400" /> },
    { label: 'Active Co-Pilot Agents', value: '6 / 7', detail: 'Planner, Memory, Critic online', icon: <Bot size={16} className="text-purple-400" /> },
    { label: 'Memory & Storage', value: '34.2 MB', detail: 'ChromaDB local vector database', icon: <Database size={16} className="text-yellow-400" /> },
    { label: 'MCP Registry Link', value: '3 / 4', detail: 'GitHub, AWS, Notion synced', icon: <Server size={16} className="text-emerald-400" /> }
  ];

  const quickActions = [
    { label: 'New AI Chat', desc: 'Consult orchestration pipelines', path: '/user/chat', icon: <MessageSquare size={14} className="text-cyan-400" /> },
    { label: 'Upload Document', desc: 'Summarize & index PDF files', path: '/user/documents', icon: <FileText size={14} className="text-purple-400" /> },
    { label: 'Create Workflow', desc: 'n8n-style drag node builder', path: '/user/workflows', icon: <Workflow size={14} className="text-yellow-400" /> },
    { label: 'Generate Report', desc: 'CompileWeekly audits & XLS', path: '/user/reports', icon: <TrendingUp size={14} className="text-emerald-400" /> },
    { label: 'Connect MCP', desc: 'Integrate external servers', path: '/user/mcp-marketplace', icon: <Server size={14} className="text-pink-400" /> },
    { label: 'Search Memory', desc: 'Scan vector DB preferences', path: '/user/memory', icon: <Bookmark size={14} className="text-rose-400" /> }
  ];

  return (
    <div className="flex flex-col gap-6 animate-fade-in pb-10">
      
      {/* Welcome Card & Suggestions */}
      <div className="glass-panel p-6 bg-gradient-to-r from-[#0d1322ab] to-[#0a0d16ab] border-cyan-500/10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative overflow-hidden">
        <div className="relative z-10">
          <h2 className="text-2xl font-bold text-white tracking-wide">Welcome back, Operator</h2>
          <p className="text-sm text-slate-400 mt-1">AegisAI OS Handshake secure. 3 critical task alerts require planner execution.</p>
        </div>
        <div className="shrink-0 flex gap-2">
          <div className="badge badge-cyan">
            <Sparkles size={12} className="mr-1" /> ACTIVE NODE SECURE
          </div>
        </div>
      </div>

      {/* Stats Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="glass-panel p-5 flex items-center justify-between hover:-translate-y-0.5 transition-all">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">{stat.label}</span>
              <span className="text-xl font-bold text-white mt-1">{stat.value}</span>
              <span className="text-[9px] text-slate-500">{stat.detail}</span>
            </div>
            <div className="w-9 h-9 rounded-lg bg-white/3 flex items-center justify-center border border-white/5">
              {stat.icon}
            </div>
          </div>
        ))}
      </div>

      {/* Main Core Widgets Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Columns (Workspace stats, running tasks, workflows) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          {/* Quick Actions Panel */}
          <div className="glass-panel p-5">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
              <Sparkles size={12} className="text-cyan-400" /> Operational Quick Actions
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
              {quickActions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => navigate(action.path)}
                  className="p-4 rounded-lg bg-white/2 border border-white/3 hover:border-cyan-500/20 text-left hover:-translate-y-0.5 transition-all cursor-pointer flex flex-col gap-1.5"
                >
                  <div className="w-7 h-7 rounded-lg bg-white/3 flex items-center justify-center">
                    {action.icon}
                  </div>
                  <h5 className="text-xs font-bold text-white mt-1">{action.label}</h5>
                  <p className="text-[10px] text-slate-500 leading-normal">{action.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Running Tasks & Pipelines */}
          <div className="glass-panel p-5">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Activity size={12} className="text-cyan-400 animate-pulse" /> Active Task Queues
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Running tasks: 2</span>
            </h4>
            
            <div className="flex flex-col gap-3 mt-4">
              {[
                { name: 'PR Audit Loop: aegis-backend', progress: 75, time: '2m 14s', status: 'running', agent: 'Orchestrator' },
                { name: 'Index database schema v4 vectors', progress: 40, time: '42s', status: 'running', agent: 'Memory Agent' }
              ].map((task, idx) => (
                <div key={idx} className="p-3.5 rounded-lg bg-white/2 border border-white/3 flex items-center justify-between text-xs">
                  <div className="flex-1 pr-6">
                    <div className="flex justify-between items-center text-[11px] font-semibold text-white mb-2">
                      <span>{task.name}</span>
                      <span className="text-cyan-400 font-mono">{task.progress}%</span>
                    </div>
                    <div className="w-full bg-white/5 rounded-full h-1 overflow-hidden">
                      <div className="bg-cyan-400 h-full transition-all duration-300" style={{ width: `${task.progress}%` }}></div>
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-4 text-[10px] text-slate-500 font-mono">
                    <span>{task.agent}</span>
                    <span>{task.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Column (Goals, Resource Limits, Calendar) */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          
          {/* Daily Goals Checkbox */}
          <div className="glass-panel p-5">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
              <CheckCircle size={12} className="text-cyan-400" /> Daily Handshake Goals
            </h4>
            <div className="flex flex-col gap-3 mt-4">
              {goals.map((g) => (
                <div
                  key={g.id}
                  onClick={() => toggleGoal(g.id)}
                  className="flex items-center gap-3 p-3 rounded-lg bg-white/2 border border-white/3 hover:border-cyan-500/20 cursor-pointer transition-all"
                >
                  <input
                    type="checkbox"
                    checked={g.completed}
                    readOnly
                    className="rounded border-white/10 text-cyan-500 focus:ring-0 bg-transparent cursor-pointer"
                  />
                  <span className={`text-xs ${g.completed ? 'line-through text-slate-500 font-normal' : 'text-slate-300 font-semibold'}`}>{g.text}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Resources & Health diagnostics */}
          <div className="glass-panel p-5">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
              <HardDrive size={12} className="text-cyan-400" /> System Diagnostics
            </h4>
            <div className="flex flex-col gap-4 mt-4">
              {[
                { label: 'Memory Allocation', value: '42.8%', color: 'bg-cyan-400' },
                { label: 'Local Disk Storage', value: '18.4 GB / 100 GB', color: 'bg-purple-400' },
                { label: 'Sys CPU Thread Usage', value: '12.8%', color: 'bg-emerald-400' }
              ].map((res, idx) => (
                <div key={idx} className="flex flex-col gap-1.5 text-[11px]">
                  <div className="flex justify-between text-slate-400">
                    <span>{res.label}</span>
                    <span className="font-semibold text-white">{res.value}</span>
                  </div>
                  <div className="w-full bg-white/5 rounded-full h-1 overflow-hidden">
                    <div className={`h-full ${res.color}`} style={{ width: res.label.includes('Storage') ? '18.4%' : res.value }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Calendar Sync Widget */}
          <div className="glass-panel p-5">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
              <Calendar size={12} className="text-cyan-400" /> Operational Calendar
            </h4>
            
            <div className="mt-4 flex flex-col gap-3">
              {[
                { time: '11:00 AM', desc: 'Sync EC2 buckets onto SQLite', status: 'upcoming' },
                { time: '02:30 PM', desc: 'Orchestrator weekly audit log run', status: 'upcoming' }
              ].map((item, idx) => (
                <div key={idx} className="flex items-start gap-3 text-xs">
                  <span className="text-[10px] text-cyan-400 font-mono w-16 shrink-0 mt-0.5">{item.time}</span>
                  <div className="flex-1">
                    <h5 className="font-semibold text-white">{item.desc}</h5>
                    <span className="text-[9px] text-slate-500 block mt-0.5 capitalize">{item.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
