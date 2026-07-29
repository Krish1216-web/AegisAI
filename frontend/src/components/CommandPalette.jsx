import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Bot, Database, Server, Key, LogOut, Terminal, Info } from 'lucide-react';

export default function CommandPalette({ onClose, role }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Close command palette on clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.ref?.current && !containerRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // List of commands based on roles
  const allCommands = [
    {
      id: 'nav-dashboard',
      label: 'Navigate: Dashboard',
      subtitle: 'Open primary workspace telemetry metrics',
      icon: <Terminal size={14} className="text-cyan-400" />,
      action: () => navigate(role === 'admin' ? '/admin/dashboard' : '/user/dashboard'),
      roles: ['user', 'admin']
    },
    {
      id: 'nav-workspace',
      label: role === 'admin' ? 'Navigate: Agent Monitoring' : 'Navigate: AI Chat Workspace',
      subtitle: 'Inspect running agents and model workflows',
      icon: <Bot size={14} className="text-purple-400" />,
      action: () => navigate(role === 'admin' ? '/admin/agents' : '/user/chat'),
      roles: ['user', 'admin']
    },
    {
      id: 'nav-memory',
      label: role === 'admin' ? 'Navigate: Security Audit Logs' : 'Navigate: Memory Explorer',
      subtitle: 'View cognitive profiles and audit files',
      icon: <Database size={14} className="text-green-400" />,
      action: () => navigate(role === 'admin' ? '/admin/security' : '/user/memory'),
      roles: ['user', 'admin']
    },
    {
      id: 'nav-mcp',
      label: 'Navigate: MCP Servers list',
      subtitle: 'Configure external tool connections',
      icon: <Server size={14} className="text-yellow-400" />,
      action: () => navigate(role === 'admin' ? '/admin/mcp' : '/user/dashboard'),
      roles: ['user', 'admin']
    },
    {
      id: 'sys-reboot',
      label: 'System Action: Reboot Aegis Core',
      subtitle: 'Flushes cache buffers and re-runs system schemas',
      icon: <Info size={14} className="text-red-400 animate-pulse" />,
      action: () => {
        alert('System Reboot sequence initiated. Reloading node...');
        window.location.reload();
      },
      roles: ['admin']
    },
    {
      id: 'sys-lock',
      label: 'System Action: Lock Node Terminal',
      subtitle: 'Terminate active session and return to decrypt portal',
      icon: <LogOut size={14} className="text-rose-400" />,
      action: () => {
        localStorage.removeItem('aegis_auth_logged');
        localStorage.removeItem('aegis_auth_role');
        window.location.reload();
      },
      roles: ['user', 'admin']
    }
  ];

  // Filter commands by query and role permissions
  const filtered = allCommands
    .filter(c => c.roles.includes(role))
    .filter(c => c.label.toLowerCase().includes(query.toLowerCase()) || c.subtitle.toLowerCase().includes(query.toLowerCase()));

  // Handle keys (up, down, enter, escape)
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filtered.length) % filtered.length);
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
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.65)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'start',
      justifyContent: 'center',
      paddingTop: '15vh',
      zIndex: 100
    }}
    onKeyDown={handleKeyDown}
    >
      <div 
        ref={containerRef}
        className="glass-panel-glow" 
        style={{
          width: '100%',
          maxWidth: '540px',
          backgroundColor: '#0a0d14ea',
          border: '1px solid rgba(0, 240, 255, 0.2)',
          boxShadow: '0 0 35px rgba(0, 240, 255, 0.08)',
          borderRadius: '12px',
          overflow: 'hidden'
        }}
      >
        {/* Search Bar Input */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          backgroundColor: 'rgba(0, 0, 0, 0.2)'
        }}>
          <Search size={18} className="text-slate-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            placeholder="Type a command or file path..."
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#fff',
              fontSize: '0.9rem',
              fontFamily: 'var(--font-sans)'
            }}
          />
          <span style={{
            fontSize: '0.65rem',
            padding: '2px 6px',
            backgroundColor: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '4px',
            color: 'var(--text-secondary)'
          }}>
            ESC
          </span>
        </div>

        {/* Command list results */}
        <div style={{ maxHeight: '320px', overflowY: 'auto', padding: '8px' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              No console matches found for: "{query}"
            </div>
          ) : (
            filtered.map((cmd, index) => {
              const active = selectedIndex === index;
              return (
                <div
                  key={cmd.id}
                  onClick={() => { cmd.action(); onClose(); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    backgroundColor: active ? 'rgba(0, 240, 255, 0.05)' : 'transparent',
                    border: `1px solid ${active ? 'rgba(0, 240, 255, 0.15)' : 'transparent'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div className="flex-center" style={{
                      width: '28px',
                      height: '28px',
                      borderRadius: '6px',
                      backgroundColor: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.04)'
                    }}>
                      {cmd.icon}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: active ? '#fff' : 'var(--text-primary)' }}>{cmd.label}</span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{cmd.subtitle}</span>
                    </div>
                  </div>
                  
                  {active && (
                    <span style={{
                      fontSize: '0.7rem',
                      color: 'var(--neon-cyan)',
                      fontFamily: 'var(--font-mono)'
                    }}>
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
