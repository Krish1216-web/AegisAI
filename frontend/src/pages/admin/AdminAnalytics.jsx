import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  Legend 
} from 'recharts';
import { TrendingUp, BarChart2, Database } from 'lucide-react';

const queryData = [
  { day: 'Mon', queries: 2400, latency: 12 },
  { day: 'Tue', queries: 3200, latency: 15 },
  { day: 'Wed', queries: 4100, latency: 14 },
  { day: 'Thu', queries: 3800, latency: 16 },
  { day: 'Fri', queries: 4900, latency: 13 },
  { day: 'Sat', queries: 5400, latency: 11 },
  { day: 'Sun', queries: 6200, latency: 12 }
];

const memoryData = [
  { day: 'Mon', vectorSize: 22, graphNodes: 85 },
  { day: 'Tue', vectorSize: 25, graphNodes: 92 },
  { day: 'Wed', vectorSize: 28, graphNodes: 104 },
  { day: 'Thu', vectorSize: 31, graphNodes: 112 },
  { day: 'Fri', vectorSize: 34, graphNodes: 128 },
  { day: 'Sat', vectorSize: 38, graphNodes: 140 },
  { day: 'Sun', vectorSize: 42, graphNodes: 148 }
];

const agentPerformance = [
  { name: 'Orch', success: 99.9, error: 0.1 },
  { name: 'Plan', success: 99.5, error: 0.5 },
  { name: 'Research', success: 98.8, error: 1.2 },
  { name: 'Exec', success: 99.2, error: 0.8 },
  { name: 'Memory', success: 99.7, error: 0.3 }
];

export default function AdminAnalytics() {
  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-300">
      
      {/* Page Header */}
      <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
            <BarChart2 size={20} className="text-purple-400" />
            System Performance Analytics
          </h2>
          <p className="text-xs text-slate-500 mt-1">Audit execution latency trends, cognitive database index growth, and thread error ratios.</p>
        </div>
      </div>

      {/* Main Charts layout split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Chart 1: API query load */}
        <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.04)] h-80 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-[rgba(255,255,255,0.04)]">
            <TrendingUp size={14} className="text-cyan-400" />
            API Query Load & Network Latency
          </div>
          <div className="flex-1 w-full text-[10px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={queryData}>
                <defs>
                  <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.02)" />
                <XAxis dataKey="day" stroke="#57657d" />
                <YAxis stroke="#57657d" />
                <Tooltip contentStyle={{ backgroundColor: '#0d1017', borderColor: 'rgba(255,255,255,0.06)', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="queries" stroke="#00f0ff" strokeWidth={2} fillOpacity={1} fill="url(#colorQueries)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Database Growth */}
        <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.04)] h-80 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-[rgba(255,255,255,0.04)]">
            <Database size={14} className="text-purple-400" />
            Cognitive Database Growth (Vectors & SQL)
          </div>
          <div className="flex-1 w-full text-[10px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={memoryData}>
                <defs>
                  <linearGradient id="colorMemory" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#bd00ff" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#bd00ff" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.02)" />
                <XAxis dataKey="day" stroke="#57657d" />
                <YAxis stroke="#57657d" />
                <Tooltip contentStyle={{ backgroundColor: '#0d1017', borderColor: 'rgba(255,255,255,0.06)', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="graphNodes" stroke="#bd00ff" strokeWidth={2} fillOpacity={1} fill="url(#colorMemory)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Agent Success Rates */}
        <div className="glass-panel p-5 bg-[#090b10ab] border border-[rgba(255,255,255,0.04)] h-80 flex flex-col gap-3 lg:col-span-2">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-[rgba(255,255,255,0.04)]">
            <BarChart2 size={14} className="text-emerald-400" />
            Agent Job Completion Success Rate (%)
          </div>
          <div className="flex-1 w-full text-[10px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={agentPerformance}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.02)" />
                <XAxis dataKey="name" stroke="#57657d" />
                <YAxis stroke="#57657d" />
                <Tooltip contentStyle={{ backgroundColor: '#0d1017', borderColor: 'rgba(255,255,255,0.06)', borderRadius: '8px' }} />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />
                <Bar dataKey="success" fill="#00ffaa" radius={[4, 4, 0, 0]} name="Successful tasks" />
                <Bar dataKey="error" fill="#ff007f" radius={[4, 4, 0, 0]} name="Failed/Retried tasks" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

    </div>
  );
}
