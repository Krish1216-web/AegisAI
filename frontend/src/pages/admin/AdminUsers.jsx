import React, { useState } from 'react';
import { Users, Search, MoreVertical, ShieldAlert, Key, UserMinus, ToggleLeft, Edit2 } from 'lucide-react';

export default function AdminUsers() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const [users, setUsers] = useState([
    { id: '1', name: 'Krish Patel', email: 'krish@aegis.ai', role: 'admin', status: 'active', login: 'Today 15:48', memory: '12.4 MB', tasks: 142 },
    { id: '2', name: 'Alice Dev', email: 'alice@aegis.ai', role: 'user', status: 'active', login: 'Yesterday 10:14', memory: '4.8 MB', tasks: 32 },
    { id: '3', name: 'Bob Tester', email: 'bob@aegis.ai', role: 'user', status: 'suspended', login: '2026-07-20 12:40', memory: '1.2 MB', tasks: 8 },
    { id: '4', name: 'Charley Oper', email: 'charley@aegis.ai', role: 'user', status: 'offline', login: '2026-07-22 09:12', memory: '3.1 MB', tasks: 24 }
  ]);

  const handleToggleStatus = (userId) => {
    setUsers(prev => prev.map(u => {
      if (u.id === userId) {
        const nextStatus = u.status === 'suspended' ? 'active' : 'suspended';
        return { ...u, status: nextStatus };
      }
      return u;
    }));
  };

  const handleResetPassword = (name) => {
    alert(`Decryption node credentials reset code generated for: ${name}`);
  };

  const filteredUsers = users
    .filter(u => filter === 'all' ? true : u.status === filter)
    .filter(u => u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Title */}
      <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <Users size={20} className="text-purple-400" />
            User Operations Control
          </h2>
          <p className="text-xs text-slate-500 mt-1">Audit active profiles, change authorization roles, and allocate memory sizes.</p>
        </div>
      </div>

      {/* Filter and Search actions */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search profiles by handle or email..."
            className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2 pl-9 pr-4 text-xs text-white w-full outline-none focus:border-purple-500/50 transition-all"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'active', 'suspended', 'offline'].map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all cursor-pointer ${filter === t ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 'bg-white/2 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white'}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Advanced data table */}
      <div className="glass-panel overflow-hidden border-[rgba(255,255,255,0.06)] bg-[#090b10ab]">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-900/60 border-b border-[rgba(255,255,255,0.06)] text-slate-400 font-bold uppercase tracking-wider">
              <th className="p-4">Profile Name</th>
              <th className="p-4">Role</th>
              <th className="p-4">Status</th>
              <th className="p-4">Last Handshake</th>
              <th className="p-4 font-mono">Memory Load</th>
              <th className="p-4">Total Jobs</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[rgba(255,255,255,0.03)]">
            {filteredUsers.map((u) => (
              <tr key={u.id} className="hover:bg-white/1 transition-all">
                <td className="p-4 flex flex-col gap-0.5">
                  <span className="font-bold text-white">{u.name}</span>
                  <span className="text-[10px] text-slate-500">{u.email}</span>
                </td>
                <td className="p-4">
                  <span className={`badge ${u.role === 'admin' ? 'badge-purple' : 'badge-cyan'}`}>
                    {u.role}
                  </span>
                </td>
                <td className="p-4">
                  <span className={`badge ${u.status === 'active' ? 'badge-green' : (u.status === 'suspended' ? 'badge-pink' : 'badge-yellow')}`}>
                    {u.status}
                  </span>
                </td>
                <td className="p-4 text-slate-400">{u.login}</td>
                <td className="p-4 font-mono text-slate-400">{u.memory}</td>
                <td className="p-4 font-mono text-slate-400">{u.tasks}</td>
                <td className="p-4 text-right">
                  <div className="flex justify-end gap-2">
                    <button 
                      onClick={() => handleToggleStatus(u.id)}
                      className={`p-1.5 rounded bg-white/2 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white cursor-pointer`}
                      title={u.status === 'suspended' ? 'Activate User' : 'Suspend User'}
                    >
                      <UserMinus size={12} className={u.status === 'suspended' ? 'text-green-400' : 'text-rose-400'} />
                    </button>
                    <button 
                      onClick={() => handleResetPassword(u.name)}
                      className="p-1.5 rounded bg-white/2 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white cursor-pointer"
                      title="Reset Decryption Key"
                    >
                      <Key size={12} className="text-yellow-400" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredUsers.length === 0 && (
          <div className="p-12 text-center text-slate-500 text-xs">
            No profiles match database queries.
          </div>
        )}
      </div>

    </div>
  );
}
