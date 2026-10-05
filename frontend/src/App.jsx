import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate, Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { ToastProvider, useToast } from './context/ToastContext';

// User Portal Pages
import UserDashboard from './pages/user/UserDashboard';
import UserChat from './pages/user/UserChat';
import UserMemory from './pages/user/UserMemory';
import UserGraph from './pages/user/UserGraph';
import UserTasks from './pages/user/UserTasks';
import UserWorkflows from './pages/user/UserWorkflows';
import UserWorkflowEditor from './pages/user/UserWorkflowEditor';
import UserMcpMarket from './pages/user/UserMcpMarket';
import UserAiMarket from './pages/user/UserAiMarket';
import UserDocuments from './pages/user/UserDocuments';
import UserReports from './pages/user/UserReports';
import UserPlatform from './pages/user/UserPlatform';
import UserTeams from './pages/user/UserTeams';
import UserProjects from './pages/user/UserProjects';
import UserNotifications from './pages/user/UserNotifications';
import UserCollaborationAnalytics from './pages/user/UserCollaborationAnalytics';

// Admin Portal Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminUsers from './pages/admin/AdminUsers';
import AdminAgents from './pages/admin/AdminAgents';
import AdminMcp from './pages/admin/AdminMcp';
import AdminAnalytics from './pages/admin/AdminAnalytics';
import AdminSecurity from './pages/admin/AdminSecurity';

// Shared Components
import CommandPalette from './components/CommandPalette';
import ConsoleTicker from './components/ConsoleTicker';
import { Breadcrumb } from './components/ui/Breadcrumb';

import {
  Bot,
  Cpu,
  Database,
  Server,
  BrainCircuit,
  Workflow,
  LayoutDashboard,
  MessageSquare,
  Bookmark,
  GitBranch,
  ListTodo,
  TrendingUp,
  Settings,
  User as UserIcon,
  LogOut,
  Bell,
  Search,
  Users,
  ShieldAlert,
  Activity,
  Sliders,
  Play,
  Clock,
  FileText,
  Sun,
  Moon,
  ChevronRight,
  FolderTree
} from 'lucide-react';

// Authentication & Core State Provider Component
export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <AppContent />
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

function AppContent() {
  const { isAuthenticated, role, logout, isLoading } = useAuth();
  const { success, info } = useToast();

  const auth = { loggedIn: isAuthenticated, role };
  const handleLogout = logout;

  const [logs, setLogs] = useState([
    { timestamp: '16:10:02', agent: 'SYS', text: 'AegisAI OS handshake secure. Security check clear.', status: 'success' },
    { timestamp: '16:10:03', agent: 'Memory', text: 'Entity mapping database loaded successfully.', status: 'success' }
  ]);

  const [showCommandPalette, setShowCommandPalette] = useState(false);

  // Trigger floating notifications
  const triggerNotification = (title, message) => {
    info(title, message);
  };

  const addLog = (agent, text, status = 'success') => {
    const time = new Date().toTimeString().split(' ')[0];
    setLogs(prev => [...prev, { timestamp: time, agent, text, status }]);
  };

  // Keyboard shortcut listener for Command Palette (Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#06070a] flex flex-col items-center justify-center text-slate-400 gap-4">
        <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin"></div>
        <span className="text-xs uppercase tracking-widest font-semibold font-mono text-cyan-400">Decrypting secure node...</span>
      </div>
    );
  }

  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/login"
          element={
            auth.loggedIn ? (
              <Navigate to={auth.role === 'admin' || auth.role === 'super admin' ? '/admin/dashboard' : '/user/dashboard'} replace />
            ) : (
              <LoginPage />
            )
          }
        />

        {/* User Portal Routes */}
        <Route
          element={
            auth.loggedIn && auth.role === 'user' ? (
              <UserLayout auth={auth} onLogout={handleLogout} logs={logs} addLog={addLog} triggerNotification={triggerNotification} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        >
          <Route path="/user" element={<Navigate to="/user/dashboard" replace />} />
          <Route path="/user/dashboard" element={<UserDashboard triggerNotification={triggerNotification} />} />
          <Route path="/user/chat" element={<UserChat logs={logs} addLog={addLog} triggerNotification={triggerNotification} />} />
          <Route path="/user/memory" element={<UserMemory />} />
          <Route path="/user/graph" element={<UserGraph />} />
          <Route path="/user/knowledge-graph" element={<UserGraph />} />
          <Route path="/user/tasks" element={<UserTasks triggerNotification={triggerNotification} />} />
          <Route path="/user/workflows" element={<UserWorkflows triggerNotification={triggerNotification} />} />
          <Route path="/user/workflows/:workflowId/edit" element={<UserWorkflowEditor triggerNotification={triggerNotification} />} />
          <Route path="/user/mcp-marketplace" element={<UserMcpMarket triggerNotification={triggerNotification} />} />
          <Route path="/user/ai-marketplace" element={<UserAiMarket triggerNotification={triggerNotification} />} />
          <Route path="/user/documents" element={<UserDocuments triggerNotification={triggerNotification} />} />
          <Route path="/user/reports" element={<UserReports triggerNotification={triggerNotification} />} />
          <Route path="/user/platform" element={<UserPlatform triggerNotification={triggerNotification} />} />
          <Route path="/user/teams" element={<UserTeams triggerNotification={triggerNotification} />} />
          <Route path="/user/projects" element={<UserProjects triggerNotification={triggerNotification} />} />
          <Route path="/user/notifications" element={<UserNotifications triggerNotification={triggerNotification} />} />
          <Route path="/user/collaboration-analytics" element={<UserCollaborationAnalytics triggerNotification={triggerNotification} />} />
          <Route path="/platform" element={<Navigate to="/user/platform" replace />} />
        </Route>

        {/* Admin Portal Routes */}
        <Route
          element={
            auth.loggedIn && (auth.role === 'admin' || auth.role === 'super admin') ? (
              <AdminLayout auth={auth} onLogout={handleLogout} logs={logs} addLog={addLog} triggerNotification={triggerNotification} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        >
          <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/agents" element={<AdminAgents addLog={addLog} />} />
          <Route path="/admin/mcp" element={<AdminMcp addLog={addLog} />} />
          <Route path="/admin/analytics" element={<AdminAnalytics />} />
          <Route path="/admin/security" element={<AdminSecurity />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* Command Palette Overlay */}
      {showCommandPalette && (
        <CommandPalette onClose={() => setShowCommandPalette(false)} role={auth.role} />
      )}
    </HashRouter>
  );
}

// ========================================================
// USER PORTAL LAYOUT FRAME
// ========================================================
function UserLayout({ auth, onLogout, logs, addLog, triggerNotification }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  // Navigation grouping
  const navigationGroups = [
    {
      group: 'Workspace',
      items: [
        { path: '/user/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
        { path: '/user/platform', label: 'Platform Engine', icon: <BrainCircuit size={16} /> },
        { path: '/user/chat', label: 'AI Workspace', icon: <Bot size={16} /> },
        { path: '/user/workflows', label: 'Workflow Builder', icon: <Workflow size={16} /> },
      ]
    },
    {
      group: 'Knowledge & RAG',
      items: [
        { path: '/user/documents', label: 'Documents Hub', icon: <FileText size={16} /> },
        { path: '/user/memory', label: 'Memory Vault', icon: <Bookmark size={16} /> },
        { path: '/user/graph', label: 'Knowledge Graph', icon: <GitBranch size={16} /> },
        { path: '/user/reports', label: 'Reports Compiler', icon: <TrendingUp size={16} /> },
      ]
    },
    {
      group: 'Ecosystem & Collab',
      items: [
        { path: '/user/mcp-marketplace', label: 'MCP Marketplace', icon: <Server size={16} /> },
        { path: '/user/ai-marketplace', label: 'Agent Center', icon: <Cpu size={16} /> },
        { path: '/user/teams', label: 'Teams & Collab', icon: <Users size={16} /> },
        { path: '/user/tasks', label: 'Tasks Board', icon: <ListTodo size={16} /> },
      ]
    }
  ];

  // Helper to generate dynamic breadcrumb
  const currentPath = location.pathname;
  const breadcrumbItems = [
    { label: 'Workspace', to: '/user/dashboard' },
    { label: currentPath.split('/').pop().replace(/-/g, ' ').toUpperCase() }
  ];

  return (
    <div className="flex h-screen bg-[#07080a] text-slate-100 overflow-hidden font-sans">

      {/* Sidebar navigation */}
      <aside className={`border-r border-white/[0.08] bg-[#0d1017] flex flex-col justify-between transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
        <div className="flex flex-col h-full overflow-hidden">
          {/* Logo Brand */}
          <div className="h-14 border-b border-white/[0.08] flex items-center px-4 gap-3 shrink-0">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-400 to-indigo-500 flex items-center justify-center shadow-md shadow-cyan-500/10 shrink-0">
              <BrainCircuit size={16} className="text-black font-bold" />
            </div>
            {!collapsed && (
              <span className="font-bold text-sm tracking-wider bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                AEGIS_AI
              </span>
            )}
          </div>

          {/* Workspace Switcher */}
          {!collapsed && (
            <div className="p-3 border-b border-white/[0.06] bg-white/[0.01] flex flex-col gap-1 shrink-0">
              <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Workspace Context</span>
              <select
                defaultValue="Personal Workspace"
                onChange={(e) => triggerNotification('Workspace Switched', `Active scope: ${e.target.value}`)}
                className="bg-[#161b22] border border-white/10 rounded px-2 py-1 text-xs text-cyan-400 font-medium outline-none w-full cursor-pointer"
              >
                <option value="Personal Workspace">Personal Workspace</option>
                <option value="Engineering Team">Engineering Team</option>
                <option value="Enterprise Global">Enterprise Global</option>
              </select>
            </div>
          )}

          {/* Grouped menu links */}
          <nav className="p-3 flex-1 overflow-y-auto space-y-4">
            {navigationGroups.map((group) => (
              <div key={group.group} className="space-y-1">
                {!collapsed && (
                  <span className="px-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                    {group.group}
                  </span>
                )}
                {group.items.map((item) => {
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      title={collapsed ? item.label : undefined}
                      className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 group ${
                        active
                          ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                          : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-100 border border-transparent'
                      }`}
                    >
                      <div className={`transition-transform duration-150 ${active ? 'text-cyan-400' : 'text-slate-400 group-hover:text-cyan-300'}`}>
                        {item.icon}
                      </div>
                      {!collapsed && <span>{item.label}</span>}
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>
        </div>

        {/* User profile actions */}
        <div className="p-3 border-t border-white/[0.08] flex items-center justify-between shrink-0 bg-white/[0.01]">
          <button
            onClick={onLogout}
            className="flex items-center gap-2 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 p-2 rounded-lg transition-all cursor-pointer w-full"
          >
            <LogOut size={15} />
            {!collapsed && <span className="font-semibold">Lock Node</span>}
          </button>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Navbar */}
        <header className="h-14 border-b border-white/[0.08] bg-[#090b10] flex items-center justify-between px-6 shrink-0 z-20">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setCollapsed(!collapsed)}
              aria-label="Toggle sidebar collapse"
              className="text-slate-400 hover:text-white p-1 rounded bg-white/5 border border-white/10 hover:border-white/20 transition-colors cursor-pointer text-xs"
            >
              {collapsed ? '▶' : '◀'}
            </button>
            <Breadcrumb items={breadcrumbItems} />
          </div>

          <div className="flex items-center gap-3">
            {/* Global search trigger */}
            <button
              onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', {ctrlKey: true, key: 'k'}))}
              className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
            >
              <Search size={13} />
              <span className="hidden sm:inline">Search (Ctrl+K)</span>
            </button>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              aria-label="Toggle dark/light theme"
              className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 text-slate-400 hover:text-white transition-all cursor-pointer"
            >
              {theme === 'dark' ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-cyan-400" />}
            </button>

            {/* Notifications link */}
            <button
              onClick={() => navigate('/user/notifications')}
              aria-label="View notifications"
              className="relative p-1.5 text-slate-400 hover:text-white rounded-lg bg-white/5 border border-white/10 hover:border-white/20 cursor-pointer transition-all"
            >
              <Bell size={15} />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            </button>

            {/* Node Operator Status */}
            <div className="flex items-center gap-2 pl-2 border-l border-white/10">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[11px] font-mono text-slate-300 font-semibold uppercase">OPERATOR</span>
            </div>
          </div>
        </header>

        {/* Content Render view */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#07080a]">
          <Outlet />
        </div>

        {/* Bottom Console Ticker */}
        <ConsoleTicker logs={logs} />
      </div>
    </div>
  );
}

// ========================================================
// ADMIN PORTAL LAYOUT FRAME
// ========================================================
function AdminLayout({ auth, onLogout, logs, addLog, triggerNotification }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const menuItems = [
    { path: '/admin/dashboard', label: 'Enterprise Dashboard', icon: <LayoutDashboard size={16} /> },
    { path: '/admin/users', label: 'User Operations', icon: <Users size={16} /> },
    { path: '/admin/agents', label: 'Agent Monitoring', icon: <Sliders size={16} /> },
    { path: '/admin/mcp', label: 'MCP Registry', icon: <Server size={16} /> },
    { path: '/admin/analytics', label: 'System Telemetry', icon: <TrendingUp size={16} /> },
    { path: '/admin/security', label: 'Security & Audit Logs', icon: <ShieldAlert size={16} /> }
  ];

  return (
    <div className="flex h-screen bg-[#060709] text-slate-200 overflow-hidden font-sans">

      {/* Sidebar navigation */}
      <aside className={`border-r border-white/[0.08] bg-[#0a0d13] flex flex-col justify-between transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
        <div>
          {/* Logo Brand */}
          <div className="h-14 border-b border-white/[0.08] flex items-center px-4 gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-purple-500 to-rose-500 flex items-center justify-center shadow-md shadow-purple-500/10 shrink-0">
              <Bot size={16} className="text-black font-bold" />
            </div>
            {!collapsed && (
              <span className="font-bold text-sm tracking-wider bg-gradient-to-r from-purple-400 to-rose-400 bg-clip-text text-transparent">
                AEGIS_CORE
              </span>
            )}
          </div>

          {/* Menu links */}
          <nav className="p-3 flex flex-col gap-1.5">
            {menuItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  title={collapsed ? item.label : undefined}
                  className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-all duration-150 group ${
                    active
                      ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                      : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-100 border border-transparent'
                  }`}
                >
                  <div className={`transition-transform duration-150 ${active ? 'text-purple-400' : 'text-slate-400 group-hover:text-purple-300'}`}>
                    {item.icon}
                  </div>
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Admin actions */}
        <div className="p-3 border-t border-white/[0.08] flex flex-col gap-2">
          <button
            onClick={onLogout}
            className="flex items-center gap-2 text-xs text-rose-400 hover:bg-rose-500/10 p-2 rounded-lg transition-all cursor-pointer w-full"
          >
            <LogOut size={15} />
            {!collapsed && <span className="font-semibold">Lock Node</span>}
          </button>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Navbar */}
        <header className="h-14 border-b border-white/[0.08] bg-[#0b0f19] flex items-center justify-between px-6 shrink-0 z-20">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setCollapsed(!collapsed)}
              aria-label="Toggle sidebar collapse"
              className="text-slate-400 hover:text-white p-1 rounded bg-white/5 border border-white/10 hover:border-white/20 transition-colors cursor-pointer text-xs"
            >
              {collapsed ? '▶' : '◀'}
            </button>
            <span className="text-xs font-mono text-purple-300 font-semibold tracking-wide">
              ADMINISTRATION :: ROOT_SYSADMIN
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', {ctrlKey: true, key: 'k'}))}
              className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
            >
              <Search size={13} />
              <span className="hidden sm:inline">Search (Ctrl+K)</span>
            </button>

            <button
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 text-slate-400 hover:text-white transition-all cursor-pointer"
            >
              {theme === 'dark' ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-purple-400" />}
            </button>

            <button
              onClick={() => triggerNotification('Telemetry Alert', 'Memory DB query queues flushed. Cache integrity: 100%.')}
              aria-label="View alerts"
              className="relative p-1.5 text-slate-400 hover:text-white rounded-lg bg-white/5 border border-white/10 hover:border-white/20 cursor-pointer"
            >
              <Bell size={15} />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-purple-400"></span>
            </button>
          </div>
        </header>

        {/* Content Render view */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#060709]">
          <Outlet />
        </div>

        {/* Bottom Console Ticker */}
        <ConsoleTicker logs={logs} />
      </div>
    </div>
  );
}
