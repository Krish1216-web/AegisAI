import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Bot,
  Database,
  Server,
  LogOut,
  LayoutDashboard,
  Workflow,
  FileText,
  GitBranch,
  ListTodo,
  TrendingUp,
  Sun,
  Moon,
  Users,
  ShieldAlert,
  BrainCircuit,
  Plus
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function CommandPalette({ onClose, role }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const allCommands = [
    {
      id: 'nav-dashboard',
      label: 'Open Dashboard',
      subtitle: 'Navigate to system analytics and overview',
      category: 'Navigation',
      icon: <LayoutDashboard size={16} className="text-cyan-400" />,
      action: () => navigate(role === 'admin' || role === 'super admin' ? '/admin/dashboard' : '/user/dashboard'),
      roles: ['user', 'admin', 'super admin']
    },
    {
      id: 'nav-platform',
      label: 'Open Platform Engine',
      subtitle: 'Execute multi-agent workflows and inspect execution logs',
      category: 'Workspace',
      icon: <BrainCircuit size={16} className="text-cyan-400" />,
      action: () => navigate('/user/platform'),
      roles: ['user']
    },
    {
      id: 'nav-chat',
      label: 'Open AI Workspace',
      subtitle: 'Engage with autonomous multi-agent copilot',
      category: 'Workspace',
      icon: <Bot size={16} className="text-purple-400" />,
      action: () => navigate('/user/chat'),
      roles: ['user']
    },
    {
      id: 'nav-workflows',
      label: 'Open Workflow Builder',
      subtitle: 'Design visual DAG agent automation workflows',
      category: 'Workspace',
      icon: <Workflow size={16} className="text-indigo-400" />,
      action: () => navigate('/user/workflows'),
      roles: ['user']
    },
    {
      id: 'nav-documents',
      label: 'Open Documents Hub',
      subtitle: 'Manage indexed files, embeddings, and RAG knowledge',
      category: 'Knowledge',
      icon: <FileText size={16} className="text-blue-400" />,
      action: () => navigate('/user/documents'),
      roles: ['user']
    },
    {
      id: 'nav-memory',
      label: 'Open Memory Vault',
      subtitle: 'Inspect cognitive long-term episodic & semantic memories',
      category: 'Knowledge',
      icon: <Database size={16} className="text-emerald-400" />,
      action: () => navigate('/user/memory'),
      roles: ['user']
    },
    {
      id: 'nav-graph',
      label: 'Open Knowledge Graph',
      subtitle: 'Explore entity relationships and multi-hop graph triples',
      category: 'Knowledge',
      icon: <GitBranch size={16} className="text-teal-400" />,
      action: () => navigate('/user/graph'),
      roles: ['user']
    },
    {
      id: 'nav-mcp',
      label: 'Open MCP Marketplace',
      subtitle: 'Manage Model Context Protocol server capabilities',
      category: 'Integrations',
      icon: <Server size={16} className="text-amber-400" />,
      action: () => navigate(role === 'admin' || role === 'super admin' ? '/admin/mcp' : '/user/mcp-marketplace'),
      roles: ['user', 'admin', 'super admin']
    },
    {
      id: 'nav-teams',
      label: 'Open Teams & Collaboration',
      subtitle: 'Manage collaborative projects, teams, and resource access',
      category: 'Collaboration',
      icon: <Users size={16} className="text-sky-400" />,
      action: () => navigate('/user/teams'),
      roles: ['user']
    },
    {
      id: 'nav-admin-security',
      label: 'Open Security & Audit Logs',
      subtitle: 'Inspect tamper-evident cryptographic security audit trails',
      category: 'Administration',
      icon: <ShieldAlert size={16} className="text-rose-400" />,
      action: () => navigate('/admin/security'),
      roles: ['admin', 'super admin']
    },
    {
      id: 'action-theme',
      label: `Switch Theme to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`,
      subtitle: 'Toggle user interface appearance',
      category: 'Preferences',
      icon: theme === 'dark' ? <Sun size={16} className="text-amber-400" /> : <Moon size={16} className="text-cyan-400" />,
      action: () => toggleTheme(),
      roles: ['user', 'admin', 'super admin']
    },
    {
      id: 'action-logout',
      label: 'Lock Node (Log Out)',
      subtitle: 'Safely terminate active session and purge tokens',
      category: 'Session',
      icon: <LogOut size={16} className="text-rose-400" />,
      action: () => {
        localStorage.removeItem('aegis_access_token');
        localStorage.removeItem('aegis_auth_logged');
        localStorage.removeItem('aegis_auth_role');
        window.location.reload();
      },
      roles: ['user', 'admin', 'super admin']
    }
  ];

  const filtered = allCommands
    .filter(c => c.roles.includes(role || 'user'))
    .filter(c =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.subtitle.toLowerCase().includes(query.toLowerCase()) ||
      c.category.toLowerCase().includes(query.toLowerCase())
    );

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (filtered.length ? (prev + 1) % filtered.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (filtered.length ? (prev - 1 + filtered.length) % filtered.length : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
        onClose();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command Palette"
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-start justify-center pt-[12vh] p-4 animate-fade-in"
      onKeyDown={handleKeyDown}
    >
      <div
        ref={containerRef}
        className="w-full max-w-xl bg-[#0d1017] border border-white/15 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[70vh] animate-scale-up"
      >
        {/* Search Bar Input */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/[0.08] bg-white/[0.02]">
          <Search size={18} className="text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={filtered.length > 0}
            aria-autocomplete="list"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            placeholder="Type a command or search workspace... (e.g. Workflow, Theme, Memory)"
            className="flex-1 bg-transparent border-none text-sm text-slate-100 outline-none placeholder:text-slate-500"
          />
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-400 font-mono border border-white/10">
            ESC
          </span>
        </div>

        {/* Command list results */}
        <div role="listbox" className="overflow-y-auto p-2 divide-y divide-white/[0.02]">
          {filtered.length === 0 ? (
            <div className="py-10 text-center text-xs text-slate-500">
              No matching commands found for "{query}"
            </div>
          ) : (
            filtered.map((cmd, index) => {
              const active = selectedIndex === index;
              return (
                <div
                  key={cmd.id}
                  role="option"
                  aria-selected={active}
                  onClick={() => { cmd.action(); onClose(); }}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all duration-100 ${
                    active ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20' : 'text-slate-300 hover:bg-white/[0.03] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 rounded-lg bg-white/[0.04] border border-white/[0.06] shrink-0">
                      {cmd.icon}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-100 truncate">{cmd.label}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/[0.06] text-slate-400 font-medium">
                          {cmd.category}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400 truncate mt-0.5">{cmd.subtitle}</span>
                    </div>
                  </div>

                  {active && (
                    <span className="text-[10px] font-mono text-cyan-400 shrink-0 ml-2">
                      ENTER ↵
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
