import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate, Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import { AuthProvider, useAuth } from './context/AuthContext';

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
  FileText
} from 'lucide-react';

// Authentication & Core State Provider Component
export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

function AppContent() {
  const { isAuthenticated, role, logout, isLoading } = useAuth();
  
  const auth = { loggedIn: isAuthenticated, role };
  const handleLogout = logout;

  const [logs, setLogs] = useState([
    { timestamp: '16:10:02', agent: 'SYS', text: 'AegisAI OS handshake secure. Security check clear.', status: 'success' },
    { timestamp: '16:10:03', agent: 'Memory', text: 'SQLite entity mapping database loaded successfully.', status: 'success' }
  ]);

  const [notification, setNotification] = useState(null);
  const [showCommandPalette, setShowCommandPalette] = useState(false);

  // Trigger floating notifications
  const triggerNotification = (title, message) => {
    setNotification({ title, message });
    setTimeout(() => setNotification(null), 4000);
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
        <span className="text-[10px] uppercase tracking-wider font-semibold text-cyan-400">Decrypting secure node...</span>
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
              <UserLayout auth={auth} onLogout={handleLogout} logs={logs} addLog={addLog} notification={notification} triggerNotification={triggerNotification} />
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
          <Route path="/platform" element={<Navigate to="/user/platform" replace />} />
        </Route>

        {/* Admin Portal Routes */}
        <Route 
          element={
            auth.loggedIn && (auth.role === 'admin' || auth.role === 'super admin') ? (
              <AdminLayout auth={auth} onLogout={handleLogout} logs={logs} addLog={addLog} notification={notification} triggerNotification={triggerNotification} />
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
function UserLayout({ auth, onLogout, logs, addLog, notification, triggerNotification }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems = [
    { path: '/user/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { path: '/user/platform', label: 'Platform Engine', icon: <BrainCircuit size={18} /> },
    { path: '/user/teams', label: 'Teams & Collab', icon: <Users size={18} /> },
    { path: '/user/collaboration-analytics', label: 'Collab Analytics', icon: <TrendingUp size={18} /> },
    { path: '/user/chat', label: 'AI Workspace', icon: <Bot size={18} /> },
    { path: '/user/workflows', label: 'Workflow Builder', icon: <Workflow size={18} /> },
    { path: '/user/mcp-marketplace', label: 'MCP Marketplace', icon: <Server size={18} /> },
    { path: '/user/ai-marketplace', label: 'AI Agent Center', icon: <Cpu size={18} /> },
    { path: '/user/documents', label: 'Documents Hub', icon: <FileText size={18} /> },
    { path: '/user/reports', label: 'Reports Compiler', icon: <TrendingUp size={18} /> },
    { path: '/user/memory', label: 'Memory Explorer', icon: <Bookmark size={18} /> },
    { path: '/user/graph', label: 'Knowledge Graph', icon: <GitBranch size={18} /> },
    { path: '/user/tasks', label: 'Tasks Board', icon: <ListTodo size={18} /> }
  ];

  return (
    <div className="flex h-screen bg-[#07080a] text-slate-100 overflow-hidden font-sans">
      
      {/* Sidebar navigation */}
      <aside className={`border-r border-[rgba(255,255,255,0.06)] bg-[#0d101780] backdrop-blur-md flex flex-col justify-between transition-all duration-300 ${collapsed ? 'w-20' : 'w-64'}`}>
        <div>
          {/* Logo Brand */}
          <div className="h-16 border-b border-[rgba(255,255,255,0.06)] flex items-center px-6 gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-400 to-indigo-500 flex items-center justify-center shadow-lg shadow-cyan-500/10 shrink-0">
              <BrainCircuit size={18} className="text-black" />
            </div>
            {!collapsed && (
              <span className="font-bold text-md tracking-wider bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">AEGIS_AI</span>
            )}
          </div>

          {/* Workspace Switcher */}
          {!collapsed && (
            <div className="p-4 border-b border-[rgba(255,255,255,0.04)] bg-white/1 flex flex-col gap-1 shrink-0">
              <span className="text-[8px] text-slate-500 uppercase tracking-wider font-bold">Workspace Scope</span>
              <select 
                defaultValue="Personal Workspace"
                onChange={(e) => triggerNotification('Workspace Scope Switched', `Active context redirected: ${e.target.value}`)}
                className="bg-transparent border-none text-xs text-cyan-400 font-semibold outline-none w-full cursor-pointer mt-0.5"
              >
                <option value="Personal Workspace" className="bg-[#0d1017]">Personal Workspace</option>
                <option value="Team Workspace" className="bg-[#0d1017]">Team Workspace</option>
                <option value="Organization Workspace" className="bg-[#0d1017]">Organization Workspace</option>
              </select>
            </div>
          )}

          {/* Menu links */}
          <nav className="p-4 flex flex-col gap-2 max-h-[calc(100vh-230px)] overflow-y-auto">
            {menuItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 p-3 rounded-lg text-sm transition-all group ${active ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-slate-400 hover:bg-white/5 hover:text-white border border-transparent'}`}
                >
                  <div className={`transition-transform duration-200 group-hover:scale-110 ${active ? 'text-cyan-400' : 'text-slate-400 group-hover:text-cyan-300'}`}>
                    {item.icon}
                  </div>
                  {!collapsed && <span className="font-medium">{item.label}</span>}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User profile actions */}
        <div className="p-4 border-t border-[rgba(255,255,255,0.06)]">
          <button 
            onClick={onLogout} 
            className="flex items-center gap-3 w-full p-3 rounded-lg text-sm text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all cursor-pointer"
          >
            <LogOut size={16} />
            {!collapsed && <span className="font-semibold">LOCK_NODE</span>}
          </button>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 border-b border-[rgba(255,255,255,0.06)] bg-[#090b10] flex items-center justify-between px-6 shrink-0 z-20">
          {/* Collapse sidebar button & Search shortcut */}
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setCollapsed(!collapsed)} 
              className="text-slate-400 hover:text-white text-xs px-2 py-1 bg-white/5 border border-[rgba(255,255,255,0.06)] rounded cursor-pointer"
            >
              {collapsed ? '▶' : '◀'}
            </button>
            <div className="relative group cursor-pointer" onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', {ctrlKey: true, key: 'k'}))}>
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search command center... (Ctrl+K)"
                readOnly
                className="bg-white/5 border border-[rgba(255,255,255,0.06)] rounded-lg py-1.5 pl-9 pr-4 text-xs text-slate-300 w-64 outline-none cursor-pointer group-hover:border-cyan-500/30 transition-all"
              />
            </div>
          </div>

          {/* User Telemetry & Roles */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
              <span className="text-xs font-semibold text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded bg-cyan-500/5">OPERATOR</span>
            </div>
            
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Clock size={12} />
              <span className="font-mono">TIME_SYNC</span>
            </div>

            <button 
              onClick={() => navigate('/user/notifications')}
              className="relative p-2 text-slate-400 hover:text-white rounded-lg bg-white/5 border border-[rgba(255,255,255,0.06)] cursor-pointer"
            >
              <Bell size={14} />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            </button>
          </div>
        </header>

        {/* Content Render view */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#07080a]">
          <Outlet />
        </div>

        {/* Bottom Console Ticker */}
        <ConsoleTicker logs={logs} />
      </div>

      {/* Floating alert notification toast */}
      {notification && (
        <div className="fixed bottom-12 right-6 glass-panel-glow border-cyan-500/30 p-4 w-80 z-50 flex items-start gap-3 bg-[#0d1017e0] animate-slide-up">
          <Activity size={18} className="text-cyan-400 mt-0.5 shrink-0 animate-pulse" />
          <div>
            <h5 className="text-xs font-bold uppercase tracking-wider text-cyan-400">{notification.title}</h5>
            <p className="text-xs text-slate-300 mt-1">{notification.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ========================================================
// ADMIN PORTAL LAYOUT FRAME
// ========================================================
function AdminLayout({ auth, onLogout, logs, addLog, notification, triggerNotification }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems = [
    { path: '/admin/dashboard', label: 'Enterprise Dashboard', icon: <LayoutDashboard size={18} /> },
    { path: '/admin/users', label: 'User Operations', icon: <Users size={18} /> },
    { path: '/admin/agents', label: 'AI Agent Monitoring', icon: <Sliders size={18} /> },
    { path: '/admin/mcp', label: 'MCP Registry Manager', icon: <Server size={18} /> },
    { path: '/admin/analytics', label: 'System Analytics', icon: <TrendingUp size={18} /> },
    { path: '/admin/security', label: 'Security & Audit Logs', icon: <ShieldAlert size={18} /> }
  ];

  return (
    <div className="flex h-screen bg-[#060709] text-slate-200 overflow-hidden font-sans">
      
      {/* Sidebar navigation */}
      <aside className={`border-r border-[rgba(255,255,255,0.06)] bg-[#0a0d13] flex flex-col justify-between transition-all duration-300 ${collapsed ? 'w-20' : 'w-64'}`}>
        <div>
          {/* Logo Brand */}
          <div className="h-16 border-b border-[rgba(255,255,255,0.06)] flex items-center px-6 gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-500 to-rose-500 flex items-center justify-center shadow-lg shadow-purple-500/10 shrink-0">
              <Bot size={18} className="text-black" />
            </div>
            {!collapsed && (
              <span className="font-bold text-sm tracking-wider bg-gradient-to-r from-purple-400 to-rose-400 bg-clip-text text-transparent">AEGIS_CORE</span>
            )}
          </div>

          {/* Menu links */}
          <nav className="p-4 flex flex-col gap-2">
            {menuItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 p-3 rounded-lg text-sm transition-all group ${active ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 'text-slate-400 hover:bg-white/5 hover:text-white border border-transparent'}`}
                >
                  <div className={`transition-transform duration-200 group-hover:scale-110 ${active ? 'text-purple-400' : 'text-slate-400 group-hover:text-purple-300'}`}>
                    {item.icon}
                  </div>
                  {!collapsed && <span className="font-medium">{item.label}</span>}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Admin actions */}
        <div className="p-4 border-t border-[rgba(255,255,255,0.06)] flex flex-col gap-2">
          <button 
            onClick={onLogout} 
            className="flex items-center gap-3 w-full p-3 rounded-lg text-sm text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all cursor-pointer"
          >
            <LogOut size={16} />
            {!collapsed && <span className="font-semibold">LOCK_NODE</span>}
          </button>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 border-b border-[rgba(255,255,255,0.06)] bg-[#0b0f19] flex items-center justify-between px-6 shrink-0 z-20">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setCollapsed(!collapsed)} 
              className="text-slate-400 hover:text-white text-xs px-2 py-1 bg-white/5 border border-[rgba(255,255,255,0.06)] rounded cursor-pointer"
            >
              {collapsed ? '▶' : '◀'}
            </button>
            <div className="relative group cursor-pointer" onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', {ctrlKey: true, key: 'k'}))}>
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search admin databases... (Ctrl+K)"
                readOnly
                className="bg-white/5 border border-[rgba(255,255,255,0.06)] rounded-lg py-1.5 pl-9 pr-4 text-xs text-slate-300 w-64 outline-none cursor-pointer group-hover:border-purple-500/30 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse"></span>
              <span className="text-xs font-semibold text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded bg-purple-500/5">ROOT_SYSADMIN</span>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Clock size={12} />
              <span className="font-mono">TIME_SYNC</span>
            </div>

            <button 
              onClick={() => triggerNotification('Telemetry Alert', 'Memory DB query queues flushed. Cache integrity: 100%.')}
              className="relative p-2 text-slate-400 hover:text-white rounded-lg bg-white/5 border border-[rgba(255,255,255,0.06)] cursor-pointer"
            >
              <Bell size={14} />
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

      {/* Floating notification alert */}
      {notification && (
        <div className="fixed bottom-12 right-6 glass-panel-glow border-purple-500/30 p-4 w-80 z-50 flex items-start gap-3 bg-[#0d1017e0] animate-slide-up">
          <Activity size={18} className="text-purple-400 mt-0.5 shrink-0 animate-pulse" />
          <div>
            <h5 className="text-xs font-bold uppercase tracking-wider text-purple-400">{notification.title}</h5>
            <p className="text-xs text-slate-300 mt-1">{notification.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}
