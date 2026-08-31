import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Terminal, CheckCircle2, Circle, AlertCircle, ArrowDown, Square, Loader2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { streamAgentWorkflow, cancelExecution, confirmExecution, getExecutionDetails } from '../../api/agent';

export default function UserChat({ logs, addLog, triggerNotification }) {
  const { workspaceId } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 0: Idle, 1: Planning, 2: Researching, 3: Tool Calls, 4: Saving Memory, 5: Done
  const [activeExecutionId, setActiveExecutionId] = useState(null);
  const [activeToolName, setActiveToolName] = useState('');
  
  // Confirmation state
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [confirmationToken, setConfirmationToken] = useState(null);
  const [confirmationTool, setConfirmationTool] = useState('');

  const messagesEndRef = useRef(null);

  const steps = [
    { id: 1, label: 'Planning', desc: 'Decomposing task into sub-goals and priorities...' },
    { id: 2, label: 'Researching', desc: 'Executing semantic search and Tavily web crawling...' },
    { id: 3, label: 'Calling MCP Tools', desc: 'Invoking local filesystem and git shell scripts...' },
    { id: 4, label: 'Saving Memory', desc: 'Writing vectors to ChromaDB and mapping SQLite nodes...' },
    { id: 5, label: 'Generating Response', desc: 'Synthesizing agent inputs into final output...' }
  ];

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isRunning, currentStep, showConfirmation]);

  // Recover state on page load or when execution finishes
  const handleRecoverState = async (executionId) => {
    try {
      const details = await getExecutionDetails(executionId);
      if (details.final_response) {
        setMessages(prev => {
          // Prevent duplicates
          if (prev.some(m => m.executionId === executionId && m.sender === 'agent')) {
            return prev;
          }
          return [...prev, {
            sender: 'agent',
            text: details.final_response,
            timestamp: new Date(details.completed_at || Date.now()).toTimeString().split(' ')[0],
            executionId
          }];
        });
      }
    } catch (e) {
      console.error('Failed to recover execution details:', e);
    }
  };

  const handleSSEEvent = (eventData) => {
    const { event, execution_id, metadata, status } = eventData;
    
    if (execution_id) {
      setActiveExecutionId(execution_id);
    }

    switch (event) {
      case 'EXECUTION_STARTED':
        setCurrentStep(1);
        addLog('Orchestrator', 'Query received. Initializing pipeline execution...', 'running');
        break;
      case 'ORCHESTRATOR_STARTED':
      case 'PLANNER_STARTED':
        setCurrentStep(1);
        addLog('Planning', 'Establishing roadmap and sub-tasks...', 'running');
        break;
      case 'RESEARCH_STARTED':
        setCurrentStep(2);
        addLog('Research', 'Crawling Tavily search engine and indexing resources...', 'running');
        break;
      case 'MCP_TOOL_STARTED':
      case 'TOOL_STARTED':
        setCurrentStep(3);
        const tId = metadata?.tool_id || 'unnamed tool';
        setActiveToolName(tId);
        addLog('Tool Executor', `Invoking MCP tool: ${tId}...`, 'running');
        break;
      case 'MCP_TOOL_COMPLETED':
      case 'TOOL_COMPLETED':
        setCurrentStep(3);
        const compId = metadata?.tool_id || 'unnamed tool';
        addLog('Tool Executor', `MCP Tool execution completed: ${compId}`, 'success');
        break;
      case 'MCP_RESOURCE_STARTED':
        setCurrentStep(3);
        addLog('MCP Resource', `Reading authorized workspace resource: ${metadata?.resource_id || ''}...`, 'running');
        break;
      case 'MCP_RESOURCE_COMPLETED':
        setCurrentStep(3);
        addLog('MCP Resource', 'Resource reading and sanitization completed.', 'success');
        break;
      case 'MCP_PROMPT_STARTED':
        setCurrentStep(3);
        addLog('MCP Prompt', `Rendering prompt template: ${metadata?.prompt_id || ''}...`, 'running');
        break;
      case 'MCP_PROMPT_COMPLETED':
        setCurrentStep(3);
        addLog('MCP Prompt', 'Prompt template rendered into untrusted context.', 'success');
        break;
      case 'MCP_SECURITY_DENIED':
        addLog('MCP Security', `Security boundary rejected MCP operation: ${metadata?.reason || 'Forbidden'}`, 'error');
        break;
      case 'MEMORY_STARTED':
        setCurrentStep(4);
        addLog('Memory', 'Syncing Postgres Vector Memory blocks...', 'running');
        break;
      case 'CRITIC_STARTED':
        addLog('Critic', 'Critic evaluating security policy validations...', 'running');
        break;
      case 'RESPONSE_GENERATING':
        setCurrentStep(5);
        addLog('Response Generator', 'Scrubbing credentials and formatting output text...', 'running');
        break;
      case 'EXECUTION_COMPLETED':
        setCurrentStep(0);
        setIsRunning(false);
        addLog('Orchestrator', 'Task execution finished successfully.', 'success');
        triggerNotification('Task Completed', 'AI response successfully dispatched.');
        if (execution_id) {
          handleRecoverState(execution_id);
        }
        break;
      case 'ExecutionFailed':
      case 'MCP_TOOL_FAILED':
        setCurrentStep(0);
        setIsRunning(false);
        const errMsg = eventData.error || 'The execution could not be completed.';
        addLog('Orchestrator', `Execution failed: ${errMsg}`, 'error');
        triggerNotification('Execution Failed', errMsg);
        setMessages(prev => [...prev, {
          sender: 'agent',
          text: `⚠️ **System Error Encountered**\n\nFailed to complete the agent execution sequence. Details:\n\`\`\`\n${errMsg}\n\`\`\``,
          timestamp: new Date().toTimeString().split(' ')[0],
          executionId: execution_id
        }]);
        break;
      case 'EXECUTION_CANCELLED':
        setCurrentStep(0);
        setIsRunning(false);
        addLog('Orchestrator', 'Execution cancelled by operator signal.', 'warning');
        triggerNotification('Execution Cancelled', 'Active execution was terminated.');
        setMessages(prev => [...prev, {
          sender: 'agent',
          text: `⛔ *Execution cancelled by operator.*`,
          timestamp: new Date().toTimeString().split(' ')[0],
          executionId: execution_id
        }]);
        break;
      case 'MCP_TOOL_CONFIRMATION_REQUIRED':
      case 'WAITING_FOR_CONFIRMATION':
        setIsRunning(false);
        setConfirmationToken(metadata?.confirmation_token);
        setConfirmationTool(metadata?.tool_id || 'High-Risk MCP Operation');
        setShowConfirmation(true);
        addLog('SYS', `High-risk MCP operation requires human confirmation: ${metadata?.tool_id}`, 'warning');
        break;
      default:
        break;
    }
  };

  const handleSSEError = (err) => {
    console.error('SSE Error:', err);
    setIsRunning(false);
    setCurrentStep(0);
    addLog('SYS', `Stream connection error: ${err.message || err}`, 'error');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isRunning) return;

    if (!workspaceId) {
      addLog('SYS', 'Error: Default workspace missing. Authenticate or select workspace first.', 'error');
      return;
    }

    const userText = input.trim();
    setMessages(prev => [...prev, { sender: 'user', text: userText, timestamp: new Date().toTimeString().split(' ')[0] }]);
    setInput('');
    setIsRunning(true);
    setCurrentStep(1);

    await streamAgentWorkflow(
      { message: userText, workspace_id: workspaceId },
      handleSSEEvent,
      handleSSEError
    );
  };

  const handleCancelClick = async () => {
    if (!activeExecutionId) return;
    try {
      addLog('SYS', 'Broadcasting cancellation signal...', 'warning');
      await cancelExecution(activeExecutionId);
    } catch (e) {
      addLog('SYS', `Cancellation request failed: ${e.message || e}`, 'error');
    }
  };

  const handleConfirmAction = async (approved) => {
    if (!activeExecutionId || !confirmationToken) return;
    try {
      setShowConfirmation(false);
      if (approved) {
        addLog('SYS', 'Confirmation approved. Resuming pipeline execution...', 'success');
        setIsRunning(true);
        await confirmExecution(activeExecutionId, confirmationToken);
      } else {
        addLog('SYS', 'Confirmation rejected. Cancelling execution...', 'warning');
        await cancelExecution(activeExecutionId);
      }
    } catch (e) {
      addLog('SYS', `Confirmation submit failed: ${e.message || e}`, 'error');
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-12rem)] overflow-hidden">
      
      {/* Left Chat Window Column */}
      <div className="lg:col-span-2 glass-panel flex flex-col h-full overflow-hidden relative">
        {/* Header */}
        <div className="p-4 border-b border-[rgba(255,255,255,0.06)] bg-white/1 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20">
              <Bot size={16} className="text-cyan-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">AegisAI OS Workspace</h3>
              <span className="text-[10px] text-slate-400">Default Node: {workspaceId ? workspaceId.slice(0, 8) : 'Unassigned'}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isRunning && (
              <button
                onClick={handleCancelClick}
                className="btn-danger p-1.5 rounded-lg flex items-center gap-1.5 text-[10px] uppercase font-bold"
                title="Cancel Execution"
              >
                <Square size={10} fill="currentColor" /> Stop
              </button>
            )}
            <span className={`badge ${isRunning ? 'badge-cyan animate-pulse' : 'badge-green'}`}>
              {isRunning ? 'EXECUTING_CORE' : 'STANDBY'}
            </span>
          </div>
        </div>

        {/* Message logs */}
        <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-slate-500 gap-3">
              <Bot size={36} className="text-cyan-400 opacity-60" />
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
          
          {/* Confirmation Overlay in Chat */}
          {showConfirmation && (
            <div className="glass-panel p-4 border-yellow-500/30 bg-yellow-500/5 max-w-[450px] self-start rounded-xl flex flex-col gap-3 ml-11">
              <div className="flex gap-2.5 items-start">
                <AlertCircle size={18} className="text-yellow-400 mt-0.5 shrink-0" />
                <div className="flex flex-col gap-1 text-left">
                  <h4 className="text-xs font-bold text-yellow-400 uppercase tracking-wide">Confirmation Required</h4>
                  <p className="text-[11px] text-slate-300 leading-normal">
                    Agent requests permission to execute tool: <strong className="text-white font-mono">{confirmationTool}</strong>.
                  </p>
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => handleConfirmAction(false)}
                  className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white rounded border border-white/5 text-[10px] uppercase font-bold"
                >
                  Deny
                </button>
                <button
                  onClick={() => handleConfirmAction(true)}
                  className="px-3 py-1.5 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 rounded border border-yellow-500/20 text-[10px] uppercase font-bold"
                >
                  Approve
                </button>
              </div>
            </div>
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
            className="btn-primary px-5 rounded-lg text-xs flex items-center justify-center"
          >
            {isRunning ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          </button>
        </form>
      </div>

      {/* Right Column: Execution pipeline stages */}
      <div className="glass-panel p-5 flex flex-col h-full overflow-hidden">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-[rgba(255,255,255,0.06)] pb-3 flex items-center gap-2">
          <Terminal size={14} className="text-cyan-400" />
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
                  
                  {/* Tool output details on Active */}
                  {isActive && step.id === 3 && activeToolName && (
                    <div className="mt-2 p-2 rounded bg-black/40 border border-cyan-500/20 font-mono text-[8px] text-cyan-300 max-w-[200px]">
                      <span>CMD: call {activeToolName}</span>
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
