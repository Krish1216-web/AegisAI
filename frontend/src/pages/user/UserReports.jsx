import React, { useState } from 'react';
import { FileText, Download, CheckCircle, Clock, AlertTriangle, Plus, RefreshCw, BarChart, FileSpreadsheet, FileArchive } from 'lucide-react';

export default function UserReports({ triggerNotification }) {
  const [reports, setReports] = useState([
    { name: 'Weekly System Audit.pdf', type: 'PDF', size: '1.2 MB', date: '2026-07-24', status: 'ready' },
    { name: 'Memory Database Growth.xlsx', type: 'XLSX', size: '3.4 MB', date: '2026-07-23', status: 'ready' },
    { name: 'MCP Integration Ping Logs.docx', type: 'DOCX', size: '890 KB', date: '2026-07-20', status: 'ready' }
  ]);

  const [isCompiling, setIsCompiling] = useState(false);
  const [compileProgress, setCompileProgress] = useState(0);
  const [selectedFormat, setSelectedFormat] = useState('PDF');

  const handleCompile = (e) => {
    e.preventDefault();
    if (isCompiling) return;
    setIsCompiling(true);
    setCompileProgress(0);

    const interval = setInterval(() => {
      setCompileProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsCompiling(false);
          const newReportName = `AegisAI_Log_Compile_${new Date().toISOString().split('T')[0]}.${selectedFormat.toLowerCase()}`;
          const newReport = {
            name: newReportName,
            type: selectedFormat,
            size: '1.5 MB',
            date: new Date().toISOString().split('T')[0],
            status: 'ready'
          };
          setReports([newReport, ...reports]);
          triggerNotification('Report Compiled', `${newReportName} is ready for download.`);
          return 0;
        }
        return prev + 10;
      });
    }, 200);
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-wide">AI Reports Compiler</h2>
        <p className="text-xs text-slate-400 mt-1">Compile comprehensive multi-agent operational records, model diagnostics, and databases.</p>
      </div>

      {/* Main split grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Side: Compile Form */}
        <div className="lg:col-span-1 glass-panel p-5 flex flex-col gap-4">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2 flex items-center gap-2">
            <RefreshCw size={12} className="text-cyan-400" /> Compile Parameters
          </h4>

          <form onSubmit={handleCompile} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-500 uppercase tracking-wider">Report Source Node</label>
              <select className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2 px-3 text-xs text-slate-300 outline-none focus:border-cyan-500/30">
                <option value="system">Core Telemetry & Daemon logs</option>
                <option value="memory">ChromaDB Vector databases</option>
                <option value="workflows">n8n Workflow Execution runs</option>
                <option value="agents">Agent diagnostic ratings</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-500 uppercase tracking-wider">Target Format</label>
              <div className="grid grid-cols-3 gap-2">
                {['PDF', 'DOCX', 'XLSX'].map((fmt) => (
                  <button
                    key={fmt}
                    type="button"
                    onClick={() => setSelectedFormat(fmt)}
                    className={`py-2 border rounded-lg text-xs font-semibold cursor-pointer transition-all ${selectedFormat === fmt ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 'bg-transparent border-[rgba(255,255,255,0.06)] text-slate-400 hover:bg-white/2'}`}
                  >
                    {fmt}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-500 uppercase tracking-wider">Compiler Timeframe</label>
              <select className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2 px-3 text-xs text-slate-300 outline-none focus:border-cyan-500/30">
                <option value="day">Today (Last 24 Hours)</option>
                <option value="week">Weekly Logs</option>
                <option value="month">Monthly System audit</option>
              </select>
            </div>

            {isCompiling ? (
              <div className="flex flex-col gap-2 mt-2">
                <div className="flex justify-between items-center text-[10px] font-mono text-cyan-400">
                  <span>COMPILING DATASTRUCTURES...</span>
                  <span>{compileProgress}%</span>
                </div>
                <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-cyan-400 h-full transition-all duration-200" style={{ width: `${compileProgress}%` }}></div>
                </div>
              </div>
            ) : (
              <button type="submit" className="btn-primary py-2.5 rounded-lg text-xs mt-2 justify-center font-semibold">
                COMPILE_NEW_REPORT
              </button>
            )}
          </form>
        </div>

        {/* Right Side: Compiled registry list */}
        <div className="lg:col-span-2 glass-panel p-5 flex flex-col gap-4">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2 flex items-center justify-between">
            <span>Compiled Files Archive</span>
            <span className="text-[10px] text-slate-500 font-mono">{reports.length} files stored</span>
          </h4>

          <div className="flex flex-col gap-3">
            {reports.map((rep, idx) => (
              <div key={idx} className="flex items-center justify-between p-3.5 rounded-lg bg-white/2 border border-[rgba(255,255,255,0.04)] hover:border-cyan-500/10 transition-all">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-white/3 flex items-center justify-center border border-[rgba(255,255,255,0.04)] shrink-0">
                    {rep.type === 'PDF' && <FileText size={16} className="text-rose-400" />}
                    {rep.type === 'XLSX' && <FileSpreadsheet size={16} className="text-emerald-400" />}
                    {rep.type === 'DOCX' && <FileText size={16} className="text-blue-400" />}
                  </div>
                  <div>
                    <h5 className="text-xs font-semibold text-white">{rep.name}</h5>
                    <span className="text-[9px] text-slate-500 block mt-0.5">{rep.size} • Compiled {rep.date}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-400 font-mono">MD5_OK</span>
                  <button
                    onClick={() => triggerNotification('File Downloaded', `Saved ${rep.name} to local downloads.`)}
                    className="p-2 rounded-lg bg-white/3 hover:bg-white/5 border border-[rgba(255,255,255,0.06)] text-slate-400 hover:text-white cursor-pointer transition-all"
                  >
                    <Download size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
