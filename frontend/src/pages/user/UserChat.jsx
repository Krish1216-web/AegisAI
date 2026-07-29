import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Terminal, CheckCircle2, Circle, AlertCircle, ArrowDown } from 'lucide-react';

export default function UserChat({ logs, addLog, triggerNotification }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 0: Idle, 1: Planning, 2: Researching, 3: Tool Calls, 4: Saving Memory, 5: Done
  const messagesEndRef = useRef(null);

  const steps = [
    { id: 1, label: 'Planning', desc: 'Decomposing task into sub-goals and priorities...' },
    { id: 2, label: 'Researching', desc: 'Executing semantic search and Tavily web crawling...' },
    { id: 3, label: 'Calling MCP Tools', desc: 'Invoking local filesystem and git shell scripts...' },
    { id: 4, label: 'Saving Memory', desc: 'Writing vectors to ChromaDB and mapping SQLite nodes...' },
    { id: 5, label: 'Generating Response', desc: 'Synthesizing agent inputs into final output...' }
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isRunning) return;

    const userText = input.trim();
    setMessages(prev => [...prev, { sender: 'user', text: userText, timestamp: new Date().toTimeString().split(' ')[0] }]);
    setInput('');
    setIsRunning(true);
    setCurrentStep(1);

    // Sequence Simulation Loop
    // Step 1: Planning
    addLog('Orchestrator', `Query received: "${userText}". Initializing planner pipeline...`, 'running');
    
    setTimeout(() => {
      setCurrentStep(2);
      addLog('Planning', `Plan established: 3 sub-tasks initialized. Invoking research lookups...`, 'success');
    }, 2500);

    // Step 2: Researching
    setTimeout(() => {
      setCurrentStep(3);
      addLog('Research', `crawled 3 files and 2 web URLs. Invoking filesystem execution modules...`, 'success');
    }, 5500);

    // Step 3: MCP Tool Calls
    setTimeout(() => {
      setCurrentStep(4);
      addLog('Execution', `Invoked MCP tool "filesystem/write_file" to save backup log. Bytes: 1024.`, 'success');
    }, 8500);

    // Step 4: Saving Memory
    setTimeout(() => {
      setCurrentStep(5);
      addLog('Memory', `SQLite Knowledge Graph updated. Indexing semantic vector chunk in ChromaDB.`, 'success');
    }, 11500);

    // Step 5: Done & Respond
    setTimeout(() => {
      setCurrentStep(0);
      setIsRunning(false);
      
      const responseText = `### AegisAI Core Compilation Success

I have processed your query and executed the following pipeline steps:
1. **Planning**: Generated modular sub-goals.
2. **Research**: Searched local index files and retrieved parameters.
3. **MCP Tool Call**: Executed \`filesystem/write_file\` to dump backup records.
4. **Memory Log**: Added relationships into your personal SQLite Knowledge Graph.

The system is standing by for the next operational command.`;

      setMessages(prev => [...prev, {
        sender: 'agent',
        text: responseText,
        timestamp: new Date().toTimeString().split(' ')[0]
      }]);
      
      addLog('Orchestrator', `Task completed. Returning to standby state.`, 'success');
      triggerNotification('Task Completed', 'AI response successfully dispatched.');
    }, 14500);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isRunning, currentStep]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-12rem)] overflow-hidden">
      
      {/* Left Chat Window Column */}
      <div className="lg:col-span-2 glass-panel flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-[rgba(255,255,255,0.06)] bg-white/1 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20">
              <Bot size={16} className="text-cyan-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">AegisAI OS Workspace</h3>
              <span className="text-[10px] text-slate-400">Model: Gemini 3.5 Flash Core</span>
            </div>
          </div>
          <span className={`badge ${isRunning ? 'badge-cyan animate-pulse' : 'badge-green'}`}>
            {isRunning ? 'EXECUTING_CORE' : 'STANDBY'}
          </span>
        </div>

        {/* Message logs */}
        <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-slate-500 gap-3">
              <Bot size={36} className="text-cyan-400 opacity-60 animate-bounce" />
              <h4 className="text-sm font-bold text-slate-300">Enter OS command prompt</h4>
              <p className="text-xs max-w-sm">Provide an instruction query. AegisAI specialized agents will plan, gather facts, call MCP tools, and update database memory.</p>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isUser = msg.sender === 'user';
              return (
                <div key={idx} className={`flex gap-3 max-w-[85%] ${isUser ? 'self-end flex-row-reverse' : 'self-start'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${isUser ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400' : 'bg-purple-500/10 border-purple-500/20 text-purple-400'}`}>
                    {isUser ? <User size={14} /> : <Bot size={14} />}
                  </div>
                  <div className={`p-4 rounded-xl text-xs leading-relaxed ${isUser ? 'bg-cyan-500/5 border border-cyan-500/15 text-slate-100 rounded-tr-none' : 'bg-white/2 border border-[rgba(255,255,255,0.06)] text-slate-300 rounded-tl-none'}`}>
                    <div className="markdown-body whitespace-pre-wrap">{msg.text}</div>
                    <span className="block text-[8px] text-slate-500 text-right mt-2">{msg.timestamp}</span>
                  </div>
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input prompt form */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-[rgba(255,255,255,0.06)] bg-black/20 flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isRunning}
            placeholder={isRunning ? 'AegisAI agent loop is running...' : 'Type system instruction...'}
            className="flex-1 bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-3 px-4 text-xs text-white outline-none focus:border-cyan-500/50 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isRunning}
            className="btn-primary px-5 rounded-lg text-xs"
          >
            <Send size={14} />
          </button>
        </form>
      </div>

      {/* Right Column: Execution pipeline stages */}
      <div className="glass-panel p-5 flex flex-col h-full overflow-hidden">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
          <Terminal size={14} className="text-cyan-400 animate-pulse" />
          Execution Stage logs
        </h4>

        {/* Steps loop */}
        <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-5">
          {steps.map((step) => {
            const isCompleted = currentStep > step.id || (currentStep === 0 && messages.length > 0);
            const isActive = currentStep === step.id;
            return (
              <div key={step.id} className={`flex gap-3 transition-all duration-300 ${isCompleted ? 'opacity-100' : (isActive ? 'opacity-100 scale-102' : 'opacity-40')}`}>
                <div className="flex flex-col items-center">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center border shrink-0 text-[10px] font-bold ${isCompleted ? 'bg-green-500/10 border-green-500/20 text-green-400' : (isActive ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400 animate-pulse' : 'bg-white/5 border-[rgba(255,255,255,0.06)] text-slate-500')}`}>
                    {isCompleted ? <CheckCircle2 size={12} /> : step.id}
                  </div>
                  {step.id !== 5 && <div className={`w-0.5 h-10 my-1 ${isCompleted ? 'bg-green-500/20' : 'bg-white/5'}`}></div>}
                </div>
                
                <div className="flex flex-col gap-0.5 text-left">
                  <span className={`text-xs font-semibold ${isCompleted ? 'text-green-400' : (isActive ? 'text-cyan-400' : 'text-slate-300')}`}>
                    {step.label} {isActive && '...'}
                  </span>
                  <span className="text-[10px] text-slate-400 leading-normal">{step.desc}</span>
                  
                  {/* Tool output mockup details on Active */}
                  {isActive && step.id === 3 && (
                    <div className="mt-2 p-2 rounded bg-black/40 border border-cyan-500/20 font-mono text-[8px] text-cyan-300 max-w-[200px]">
                      <span>CMD: call filesystem/write_file</span>
                      <pre className="mt-1 opacity-70">{"{\n  \"path\": \"/backup.log\",\n  \"content\": \"sys_boot\"\n}"}</pre>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Ticker system telemetry */}
        <div className="border-t border-[rgba(255,255,255,0.06)] pt-4 mt-auto flex flex-col gap-2">
          <div className="flex justify-between text-[10px] text-slate-500">
            <span>LLM TEMPERATURE: 0.2</span>
            <span>TOP_P: 0.95</span>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500">
            <span>REASONING LOOPS: active</span>
            <span>TOKEN COST: $0.00014</span>
          </div>
        </div>
      </div>

    </div>
  );
}
