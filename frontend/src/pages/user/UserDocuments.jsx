import React, { useState } from 'react';
import { FileText, Upload, BrainCircuit, ArrowUpRight, CheckCircle, HelpCircle, File, Eye, List, Table, Languages } from 'lucide-react';

export default function UserDocuments({ triggerNotification }) {
  const [docs, setDocs] = useState([
    { id: '1', name: 'quarterly_report.pdf', size: '2.4 MB', type: 'PDF', date: '2026-07-24' },
    { id: '2', name: 'api_endpoints.docx', size: '1.1 MB', type: 'DOCX', date: '2026-07-23' },
    { id: '3', name: 'database_schema.xlsx', size: '4.8 MB', type: 'XLSX', date: '2026-07-22' }
  ]);

  const [activeDoc, setActiveDoc] = useState(docs[0]);
  const [aiOutput, setAiOutput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState('');

  const handleUploadMock = (e) => {
    e.preventDefault();
    triggerNotification('File Uploaded', 'Document registered in workspace memory.');
    const newDoc = {
      id: (docs.length + 1).toString(),
      name: 'new_context_document.pdf',
      size: '1.8 MB',
      type: 'PDF',
      date: new Date().toISOString().split('T')[0]
    };
    setDocs([newDoc, ...docs]);
    setActiveDoc(newDoc);
  };

  const handleAiAction = (action) => {
    if (!activeDoc) return;
    setIsProcessing(true);
    setAiOutput('');
    
    const steps = [
      'Reading document raw context buffers...',
      'Mapping semantic entity tokens...',
      'Synthesizing summaries via memory agent...'
    ];

    steps.forEach((step, idx) => {
      setTimeout(() => {
        setProcessingStep(step);
        if (idx === steps.length - 1) {
          setTimeout(() => {
            setIsProcessing(false);
            setProcessingStep('');
            
            if (action === 'summarize') {
              setAiOutput(`### Summary of ${activeDoc.name}\n\n* **Executive Core**: The document reviews the primary structural targets of AegisAI's orchestration nodes.\n* **Key Findings**: Multi-agent pipelines decrease overall latency by 42% relative to single-thread loops.\n* **Action Plan**: Migrate legacy MySQL tables onto SQLite semantic tables to optimize local lookup caching.`);
            } else if (action === 'explain') {
              setAiOutput(`### Concept Explanation for ${activeDoc.name}\n\n* **Model Context Protocol (MCP)**: An open-standard client-server connection layout that lets agents execute code parameters in sandboxed docker clusters securely.\n* **ChromaDB Vector Indexes**: A local storage map holding embeddings of past interactions to enrich the agent context window.`);
            } else if (action === 'tables') {
              setAiOutput(`### Table Extraction Output (${activeDoc.name})\n\n| Execution Stage | Latency Delta | CPU Allocation | Success Rating |\n| :--- | :--- | :--- | :--- |\n| Orchestration | 12ms | 4% | 100% |\n| Planning Node | 82ms | 18% | 98.4% |\n| Tool Callouts | 142ms | 8% | 100% |`);
            } else {
              setAiOutput(`### Handshake Translation (${activeDoc.name})\n\nTranslated to **SYS_LOG_HUMAN**:\n\n"The operational integrity of all active vector links is currently standing at 100%. Cache lines have been flushed and verified."`);
            }
            triggerNotification('AI Processing Done', 'Document extraction pipeline completed.');
          }, 1000);
        }
      }, idx * 800);
    });
  };

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-140px)] animate-fade-in overflow-hidden">
      
      {/* Page Header */}
      <div className="shrink-0">
        <h2 className="text-xl font-bold text-white tracking-wide">Document Analytics Hub</h2>
        <p className="text-xs text-slate-400 mt-1">Upload enterprise files and extract structured indexes, translation vectors, or summaries.</p>
      </div>

      {/* Main split dashboard view */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        
        {/* Left Side: Upload & File list */}
        <div className="w-80 flex flex-col gap-4 shrink-0 overflow-y-auto">
          {/* File Drag Box */}
          <div onClick={handleUploadMock} className="glass-panel p-6 border-dashed border-cyan-500/20 hover:border-cyan-500/40 text-center cursor-pointer group transition-all">
            <Upload size={24} className="mx-auto text-slate-500 group-hover:text-cyan-400 transition-colors mb-2" />
            <h4 className="text-xs font-semibold text-white">Upload New Files</h4>
            <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">PDF, DOCX, XLSX, Images up to 24MB. Click to browse.</p>
          </div>

          {/* Files List */}
          <div className="glass-panel p-4 flex flex-col gap-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-2">Documents Registry</h4>
            <div className="flex flex-col gap-2">
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => setActiveDoc(doc)}
                  className={`flex items-center gap-3 p-3 rounded-lg border text-xs cursor-pointer transition-all hover:bg-white/2 ${activeDoc?.id === doc.id ? 'bg-cyan-500/5 border-cyan-500/25 text-cyan-400' : 'border-transparent text-slate-400'}`}
                >
                  <File size={16} className={activeDoc?.id === doc.id ? 'text-cyan-400' : 'text-slate-500'} />
                  <div className="flex-1 min-w-0">
                    <h5 className="font-semibold text-white truncate">{doc.name}</h5>
                    <span className="text-[9px] text-slate-500 block mt-0.5">{doc.size} • {doc.date}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Side: Active Workspace */}
        <div className="flex-1 glass-panel flex flex-col bg-[#090b10] border-white/5 rounded-xl overflow-hidden">
          {activeDoc ? (
            <React.Fragment>
              {/* Workspace Header */}
              <div className="h-14 border-b border-[rgba(255,255,255,0.06)] bg-[#0d101780] flex items-center justify-between px-6 shrink-0">
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-cyan-400" />
                  <span className="text-xs font-bold text-white uppercase tracking-wider">{activeDoc.name}</span>
                </div>
                <span className="text-[9px] text-slate-500 bg-white/5 px-2 py-0.5 rounded font-mono">STATUS_PARSED</span>
              </div>

              {/* Actions toolbar */}
              <div className="p-4 border-b border-[rgba(255,255,255,0.04)] flex gap-2 shrink-0 flex-wrap">
                <button onClick={() => handleAiAction('summarize')} className="btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 hover:border-cyan-500/20">
                  <List size={12} className="text-cyan-400" /> SUMMARIZE
                </button>
                <button onClick={() => handleAiAction('explain')} className="btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 hover:border-purple-500/20">
                  <BrainCircuit size={12} className="text-purple-400" /> EXPLAIN CONCEPTS
                </button>
                <button onClick={() => handleAiAction('tables')} className="btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 hover:border-yellow-500/20">
                  <Table size={12} className="text-yellow-400" /> EXTRACT TABLES
                </button>
                <button onClick={() => handleAiAction('translate')} className="btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 hover:border-emerald-500/20">
                  <Languages size={12} className="text-emerald-400" /> TRANSLATE LOGS
                </button>
              </div>

              {/* Output Content display */}
              <div className="flex-1 p-6 overflow-y-auto relative">
                {isProcessing ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#090b10d0] z-20">
                    <div className="w-8 h-8 border-2 border-cyan-500/10 border-t-cyan-400 rounded-full animate-spin mb-3"></div>
                    <span className="text-xs text-cyan-400 font-mono">{processingStep}</span>
                  </div>
                ) : null}

                {aiOutput ? (
                  <div className="prose prose-invert max-w-none text-xs text-slate-300 leading-relaxed font-sans animate-fade-in">
                    {/* Render raw strings as Markdown layout structure */}
                    <div className="space-y-4">
                      {aiOutput.split('\n\n').map((block, idx) => {
                        if (block.startsWith('###')) {
                          return <h4 key={idx} className="text-sm font-bold text-white border-b border-[rgba(255,255,255,0.06)] pb-2">{block.replace('### ', '')}</h4>;
                        } else if (block.startsWith('|')) {
                          const rows = block.split('\n').filter(r => !r.includes(':---'));
                          return (
                            <table key={idx} className="w-full text-left border-collapse my-4 text-[11px] text-slate-300">
                              <thead>
                                <tr className="border-b border-[rgba(255,255,255,0.06)]">
                                  {rows[0].split('|').slice(1, -1).map((col, cIdx) => <th key={cIdx} className="pb-2 font-bold text-slate-400">{col.trim()}</th>)}
                                </tr>
                              </thead>
                              <tbody>
                                {rows.slice(1).map((row, rIdx) => (
                                  <tr key={rIdx} className="border-b border-[rgba(255,255,255,0.02)] hover:bg-white/1">
                                    {row.split('|').slice(1, -1).map((val, vIdx) => <td key={vIdx} className="py-2.5">{val.trim()}</td>)}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          );
                        } else if (block.startsWith('*')) {
                          return (
                            <ul key={idx} className="list-disc pl-5 space-y-2">
                              {block.split('\n').map((li, lIdx) => <li key={lIdx}>{li.replace('* ', '')}</li>)}
                            </ul>
                          );
                        } else {
                          return <p key={idx}>{block}</p>;
                        }
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center text-slate-500">
                    <BrainCircuit size={36} className="text-slate-700 animate-pulse mb-3" />
                    <h4 className="text-xs font-semibold text-slate-400">Document Reader Standby</h4>
                    <p className="text-[10px] text-slate-600 mt-1 max-w-sm">Select an AI action from the toolbar to initiate automated extraction loops.</p>
                  </div>
                )}
              </div>
            </React.Fragment>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center text-slate-500">
              <FileText size={36} className="text-slate-700 mb-3" />
              <h4 className="text-xs font-semibold text-slate-400">No Document Selected</h4>
              <p className="text-[10px] text-slate-600 mt-1">Select an existing document from the registry registry or upload a new file.</p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
