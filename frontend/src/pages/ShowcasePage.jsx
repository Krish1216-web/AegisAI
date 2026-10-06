import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Bot,
  BrainCircuit,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  LogOut,
  Layers,
  Compass,
  Activity,
  CheckCircle2,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Sliders,
  ChevronRight,
  Maximize2,
  Minimize2,
  Sun,
  Moon
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Button, StatusBadge, Badge, Tabs } from '../components/ui';
import { DemoBanner, DemoWatermark } from '../components/showcase/DemoBanner';
import { DemoTimeline } from '../components/showcase/DemoTimeline';
import { DemoEventStream } from '../components/showcase/DemoEventStream';
import { DemoEvidenceViewer } from '../components/showcase/DemoEvidenceViewer';
import { DemoArchitectureView } from '../components/showcase/DemoArchitectureView';
import { DemoTourView } from '../components/showcase/DemoTourView';
import { DemoApprovalModal } from '../components/showcase/DemoApprovalModal';
import { DEMO_SCENARIOS, DEMO_ORGANIZATION } from '../data/demoScenarios';

export default function ShowcasePage() {
  const navigate = useNavigate();
  const { isAuthenticated, role } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // Active View State
  const [activeTab, setActiveTab] = useState('scenarios');
  const [selectedScenarioId, setSelectedScenarioId] = useState(DEMO_SCENARIOS[0].id);
  const [isPresentationMode, setIsPresentationMode] = useState(false);

  // Execution Runner State
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [events, setEvents] = useState([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [speedMultiplier, setSpeedMultiplier] = useState(1); // 1 = Normal (1200ms), 2 = Fast (600ms), 4 = Presentation (300ms)
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);

  const activeScenario = DEMO_SCENARIOS.find((s) => s.id === selectedScenarioId) || DEMO_SCENARIOS[0];
  const timerRef = useRef(null);

  // Elapsed Time Counter
  useEffect(() => {
    let interval;
    if (isRunning && !isCompleted) {
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRunning, isCompleted]);

  // Step Execution Runner Engine
  useEffect(() => {
    if (!isRunning || isCompleted) return;

    const currentStep = activeScenario.steps[currentStepIndex];
    if (!currentStep) {
      setIsCompleted(true);
      setIsRunning(false);
      return;
    }

    // Check if scenario requires interactive human approval at this step
    if (activeScenario.isApprovalScenario && currentStep.stage === 'PLAN' && !isApprovalOpen && currentStepIndex === 1) {
      setIsRunning(false);
      setIsApprovalOpen(true);
      return;
    }

    const stepDuration = Math.max(250, Math.floor(1200 / speedMultiplier));
    const timer = setTimeout(() => {
      // Append event to live stream
      const timeStr = new Date().toTimeString().split(' ')[0];
      setEvents((prev) => [
        ...prev,
        {
          time: timeStr,
          agent: currentStep.agent,
          stage: currentStep.stage,
          message: currentStep.simulatedEvent
        }
      ]);

      if (currentStepIndex < activeScenario.steps.length - 1) {
        setCurrentStepIndex((prev) => prev + 1);
      } else {
        setIsCompleted(true);
        setIsRunning(false);
      }
    }, stepDuration);

    return () => clearTimeout(timer);
  }, [isRunning, currentStepIndex, isCompleted, speedMultiplier, activeScenario, isApprovalOpen]);

  // Handler: Select Scenario
  const handleSelectScenario = (scenarioId) => {
    setSelectedScenarioId(scenarioId);
    handleResetScenario(scenarioId);
  };

  // Handler: Reset Scenario
  const handleResetScenario = (targetId = selectedScenarioId) => {
    setIsRunning(false);
    setIsCompleted(false);
    setCurrentStepIndex(0);
    setEvents([]);
    setElapsedSeconds(0);
    setIsApprovalOpen(false);
  };

  // Handler: Play / Pause
  const handleTogglePlay = () => {
    if (isCompleted) {
      handleResetScenario();
      setIsRunning(true);
    } else {
      setIsRunning((prev) => !prev);
    }
  };

  // Handler: Skip Next Step
  const handleSkipStep = () => {
    if (currentStepIndex < activeScenario.steps.length - 1) {
      const step = activeScenario.steps[currentStepIndex];
      const timeStr = new Date().toTimeString().split(' ')[0];
      setEvents((prev) => [
        ...prev,
        {
          time: timeStr,
          agent: step.agent,
          stage: step.stage,
          message: step.simulatedEvent
        }
      ]);
      setCurrentStepIndex((prev) => prev + 1);
    } else {
      setIsCompleted(true);
      setIsRunning(false);
    }
  };

  // Handler: Approval Granted
  const handleApprovalGranted = (rationale) => {
    setIsApprovalOpen(false);
    const timeStr = new Date().toTimeString().split(' ')[0];
    setEvents((prev) => [
      ...prev,
      {
        time: timeStr,
        agent: 'Human Operator',
        stage: 'APPROVAL',
        message: `OPERATOR_SIGN_OFF: Request authorized. Rationale: "${rationale}".`
      }
    ]);
    setCurrentStepIndex((prev) => prev + 1);
    setIsRunning(true);
  };

  // Handler: Exit Showcase
  const handleExitShowcase = () => {
    if (isAuthenticated) {
      navigate(role === 'admin' || role === 'super admin' ? '/admin/dashboard' : '/user/dashboard');
    } else {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen bg-[#07080a] text-slate-100 font-sans flex flex-col selection:bg-cyan-500/30">
      
      {/* Persistent Non-Dismissible Demo Banner */}
      <DemoBanner onExit={handleExitShowcase} currentScenarioTitle={activeScenario.title} />

      {/* Showcase Master Header */}
      <header className="h-16 border-b border-white/[0.08] bg-[#090b10] px-6 md:px-10 flex items-center justify-between shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-400 via-indigo-500 to-purple-500 flex items-center justify-center shadow-md shadow-cyan-500/10 shrink-0">
            <BrainCircuit size={18} className="text-black font-bold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-wider bg-gradient-to-r from-cyan-400 to-indigo-300 bg-clip-text text-transparent">
                AEGISAI SHOWCASE
              </span>
              <DemoWatermark />
            </div>
            <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
              {DEMO_ORGANIZATION.name} ({DEMO_ORGANIZATION.domain})
            </span>
          </div>
        </div>

        {/* Global Controls & Theme */}
        <div className="flex items-center gap-3">
          {/* Speed Selector */}
          <div className="hidden sm:flex items-center gap-1 p-1 rounded-lg bg-white/5 border border-white/10 text-xs font-mono">
            <span className="text-[10px] text-slate-500 px-1 font-bold">SPEED:</span>
            {[
              { label: '1x', val: 1 },
              { label: '2x', val: 2 },
              { label: 'Instant', val: 4 }
            ].map((sp) => (
              <button
                key={sp.val}
                onClick={() => setSpeedMultiplier(sp.val)}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors cursor-pointer ${
                  speedMultiplier === sp.val ? 'bg-cyan-500 text-black' : 'text-slate-400 hover:text-white'
                }`}
              >
                {sp.label}
              </button>
            ))}
          </div>

          {/* Presentation Mode Toggle */}
          <button
            onClick={() => setIsPresentationMode((prev) => !prev)}
            aria-label="Toggle Presentation Mode"
            title="Toggle Distraction-Free Presentation Mode"
            className="p-2 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 text-slate-300 hover:text-white transition-all cursor-pointer"
          >
            {isPresentationMode ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme mode"
            className="p-2 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 text-slate-400 hover:text-white transition-all cursor-pointer"
          >
            {theme === 'dark' ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-cyan-400" />}
          </button>

          {/* Exit Showcase CTA */}
          <Button variant="ghost" size="sm" onClick={handleExitShowcase} leftIcon={<LogOut size={13} />}>
            Exit Demo
          </Button>
        </div>
      </header>

      {/* Main Showcase Navigation Tabs */}
      {!isPresentationMode && (
        <div className="border-b border-white/[0.08] bg-[#0c0e14] px-6 md:px-10 flex items-center justify-between">
          <nav className="flex items-center gap-2 overflow-x-auto py-2">
            {[
              { id: 'scenarios', label: 'Interactive Scenarios', icon: <Sparkles size={14} /> },
              { id: 'architecture', label: 'System Architecture', icon: <Layers size={14} /> },
              { id: 'tour', label: '9-Station Guided Tour', icon: <Compass size={14} /> }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === tab.id
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200 border border-transparent'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>

          <div className="hidden lg:flex items-center gap-3 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1.5">
              <Clock size={13} className="text-cyan-400" />
              Demo Elapsed Time: <strong className="text-white">{elapsedSeconds}s</strong>
            </span>
          </div>
        </div>
      )}

      {/* Main View Area */}
      <main className="flex-1 overflow-y-auto p-6 md:p-8 max-w-7xl mx-auto w-full flex flex-col gap-6">
        
        {/* VIEW 1: SCENARIOS RUNNER */}
        {activeTab === 'scenarios' && (
          <div className="flex flex-col gap-6">
            
            {/* Scenario Selector Cards Strip */}
            {!isPresentationMode && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                {DEMO_SCENARIOS.map((sc) => {
                  const isSelected = sc.id === selectedScenarioId;
                  return (
                    <button
                      key={sc.id}
                      onClick={() => handleSelectScenario(sc.id)}
                      className={`p-3.5 rounded-xl border text-left flex flex-col justify-between gap-2 transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-cyan-500/15 border-cyan-500 text-white shadow-lg shadow-cyan-500/10'
                          : 'bg-[#0d1017] border-white/10 hover:border-white/20 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-white/10 text-cyan-300">
                          {sc.badge}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">{sc.estimatedDuration}</span>
                      </div>
                      <div className="flex flex-col">
                        <h4 className="text-xs font-bold truncate">{sc.title}</h4>
                        <span className="text-[11px] text-slate-400 truncate mt-0.5">{sc.subtitle}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Active Scenario Banner & Control Bar */}
            <div className="p-6 rounded-2xl border border-white/10 bg-[#0d1017] flex flex-col gap-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex flex-col gap-1 max-w-2xl">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30">
                      ACTIVE SCENARIO
                    </span>
                    <span className="text-xs font-mono text-slate-400">{activeScenario.category}</span>
                  </div>
                  <h2 className="text-lg md:text-xl font-bold text-white">{activeScenario.title}</h2>
                  <p className="text-xs text-slate-300 leading-relaxed">{activeScenario.businessProblem}</p>
                </div>

                {/* Runner Control Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="primary"
                    size="md"
                    onClick={handleTogglePlay}
                    leftIcon={isRunning ? <Pause size={15} /> : <Play size={15} />}
                  >
                    {isCompleted ? 'Replay Demo' : isRunning ? 'Pause Demo' : 'Start Demo'}
                  </Button>

                  <Button
                    variant="secondary"
                    size="md"
                    onClick={handleSkipStep}
                    disabled={isCompleted}
                    leftIcon={<SkipForward size={15} />}
                  >
                    Skip Step
                  </Button>

                  <Button
                    variant="ghost"
                    size="md"
                    onClick={() => handleResetScenario()}
                    leftIcon={<RotateCcw size={15} />}
                  >
                    Reset
                  </Button>
                </div>
              </div>

              {/* Execution Prompt Card */}
              <div className="p-3.5 rounded-xl border border-white/5 bg-black/40 font-mono text-xs flex items-center gap-3 text-cyan-300">
                <span className="text-slate-500 shrink-0 font-bold">DEMO PROMPT:</span>
                <span className="text-slate-200">"{activeScenario.prompt}"</span>
              </div>
            </div>

            {/* Timeline Bar */}
            <DemoTimeline
              steps={activeScenario.steps}
              currentStepIndex={currentStepIndex}
              isCompleted={isCompleted}
              onStepClick={(idx) => setCurrentStepIndex(idx)}
            />

            {/* Main Stage Output Split View */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Left Column: Current Active Stage Detail & Live Event Stream */}
              <div className="lg:col-span-7 flex flex-col gap-6">
                
                {/* Active Step Card */}
                <div className="p-5 rounded-xl border border-cyan-500/30 bg-[#0d1017] flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                      <Bot size={15} />
                      Active Agent Node: {activeScenario.steps[currentStepIndex]?.agent || 'Orchestrator'}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-bold">
                      STAGE {currentStepIndex + 1}: {activeScenario.steps[currentStepIndex]?.stage}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-white">
                    {activeScenario.steps[currentStepIndex]?.title}
                  </h3>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {activeScenario.steps[currentStepIndex]?.detail}
                  </p>
                </div>

                {/* Event Stream */}
                <DemoEventStream events={events} />

                {/* Final Response Panel (Visible when completed or reached final step) */}
                {isCompleted && activeScenario.finalResponse && (
                  <div className="p-6 rounded-xl border border-emerald-500/40 bg-gradient-to-br from-[#0d1419] to-[#0d1017] flex flex-col gap-4 shadow-xl">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                        <ShieldCheck size={16} />
                        Simulated Response & Verified Conclusion
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                        EVIDENCE VERIFIED
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-white">
                      {activeScenario.finalResponse.answer}
                    </h3>

                    {/* Key Findings */}
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-mono font-semibold uppercase text-slate-400">
                        Key Findings:
                      </span>
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {activeScenario.finalResponse.keyFindings.map((f, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Reasoning Summary */}
                    <div className="p-3.5 rounded-lg border border-white/10 bg-black/40 text-xs flex flex-col gap-1">
                      <span className="font-mono font-semibold text-cyan-300 uppercase text-[11px]">
                        Reasoning Summary (User-Facing):
                      </span>
                      <p className="text-slate-300 leading-relaxed">
                        {activeScenario.finalResponse.reasoningSummary}
                      </p>
                    </div>

                    {/* Next Actions */}
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-mono font-semibold uppercase text-slate-400">
                        Recommended Next Actions:
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {activeScenario.finalResponse.nextActions.map((act, i) => (
                          <span
                            key={i}
                            className="text-[11px] px-2.5 py-1 rounded bg-white/5 border border-white/10 text-slate-200 font-mono"
                          >
                            • {act}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: Grounding Evidence & Knowledge Graph */}
              <div className="lg:col-span-5 flex flex-col gap-6">
                <DemoEvidenceViewer
                  evidence={activeScenario.evidence}
                  showGraph={activeScenario.id === 'flagship-coldchain'}
                />
              </div>

            </div>
          </div>
        )}

        {/* VIEW 2: ARCHITECTURE VIEW */}
        {activeTab === 'architecture' && <DemoArchitectureView />}

        {/* VIEW 3: GUIDED TOUR */}
        {activeTab === 'tour' && (
          <DemoTourView onSelectScenario={handleSelectScenario} />
        )}

      </main>

      {/* Simulated Human-in-the-Loop Approval Modal */}
      <DemoApprovalModal
        isOpen={isApprovalOpen}
        onApprove={handleApprovalGranted}
        onReject={() => {
          setIsApprovalOpen(false);
          setIsRunning(false);
        }}
        scenario={activeScenario}
      />
    </div>
  );
}
