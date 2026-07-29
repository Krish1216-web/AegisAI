import React, { useState } from 'react';
import { Bookmark, Search, Calendar, ChevronRight, Pin, Tag, Database, Download } from 'lucide-react';

export default function UserMemory() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const memories = [
    { id: '1', type: 'preference', text: 'Operator prefers FastAPI for Python backends and Vite + React for modern frontend UIs.', date: '2026-07-24 10:14', pinned: true, tags: ['tech', 'api', 'react'] },
    { id: '2', type: 'session', text: 'Analyzed local CP competitive programming folder containing Lab1.cpp and Main.java.', date: '2026-07-24 15:48', pinned: false, tags: ['session', 'cpp', 'workspace'] },
    { id: '3', type: 'long-term', text: 'Knowledge graph database schema includes entities, relationship attributes, and metadata strength logs.', date: '2026-07-24 10:15', pinned: true, tags: ['database', 'sqlite', 'schema'] },
    { id: '4', type: 'preference', text: 'User configures local embeddings on CPU to avoid active internet API token pings.', date: '2026-07-24 10:18', pinned: false, tags: ['security', 'offline', 'embeddings'] }
  ];

  const filteredMemories = memories
    .filter(m => filter === 'all' ? true : m.type === filter)
    .filter(m => m.text.toLowerCase().includes(search.toLowerCase()) || m.tags.some(t => t.toLowerCase().includes(search.toLowerCase())));

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <Bookmark size={20} className="text-cyan-400" />
            Cognitive Memory Explorer
          </h2>
          <p className="text-xs text-slate-400 mt-1">Search and filter active cognitive preferences stored in local vector embeddings.</p>
        </div>
        <button 
          onClick={() => alert('Exporting vector database database...')}
          className="btn-secondary text-xs flex items-center gap-2 cursor-pointer"
        >
          <Download size={12} /> EXPORT_VECTORS
        </button>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cognitive vectors and tags (e.g. FastAPI)..."
            className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2 pl-9 pr-4 text-xs text-white w-full outline-none focus:border-cyan-500/50 transition-all"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'preference', 'long-term', 'session'].map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all cursor-pointer ${filter === t ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'bg-white/2 border border-[rgba(255,255,255,0.04)] text-slate-400 hover:text-white'}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Memories display grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredMemories.map((mem) => (
          <div key={mem.id} className="glass-panel p-5 flex flex-col gap-4 relative hover:-translate-y-0.5">
            {/* Header info */}
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2">
                <span className={`badge ${mem.type === 'preference' ? 'badge-green' : (mem.type === 'long-term' ? 'badge-purple' : 'badge-cyan')}`}>
                  {mem.type}
                </span>
                <span className="text-[9px] text-slate-500 flex items-center gap-1">
                  <Calendar size={10} /> {mem.date}
                </span>
              </div>
              {mem.pinned && (
                <Pin size={12} className="text-cyan-400 rotate-45" />
              )}
            </div>

            {/* Text description */}
            <p className="text-xs text-slate-300 leading-relaxed flex-1">
              {mem.text}
            </p>

            {/* Tags and operations */}
            <div className="flex justify-between items-center border-t border-[rgba(255,255,255,0.03)] pt-3 mt-auto">
              <div className="flex gap-1.5">
                {mem.tags.map((tg, idx) => (
                  <span key={idx} className="text-[9px] text-slate-500 flex items-center gap-0.5">
                    <Tag size={8} /> #{tg}
                  </span>
                ))}
              </div>
              <span className="text-[9px] font-mono text-cyan-400/60">ID: vec-0{mem.id}</span>
            </div>
          </div>
        ))}
        {filteredMemories.length === 0 && (
          <div className="col-span-2 glass-panel p-12 text-center text-slate-500 text-xs">
            No memories match search query parameters.
          </div>
        )}
      </div>

    </div>
  );
}
