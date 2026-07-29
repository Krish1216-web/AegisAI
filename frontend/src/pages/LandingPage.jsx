import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bot, 
  Server, 
  Cpu, 
  TrendingUp, 
  Bookmark, 
  GitBranch, 
  ListTodo, 
  Workflow, 
  Play, 
  Code, 
  ArrowRight, 
  Check, 
  X, 
  ChevronDown, 
  BookOpen, 
  Activity, 
  Database,
  Globe,
  Radio,
  FileText,
  Settings,
  HelpCircle,
  Terminal,
  RotateCw,
  Zap,
  ShieldCheck,
  Compass,
  Layers,
  Map,
  ShieldAlert,
  ArrowDown,
  Hammer
} from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();
  const canvasRef = useRef(null);

  // Tour States
  const [tourStarted, setTourStarted] = useState(false);
  const [activeZone, setActiveZone] = useState('1');
  const [factoryState, setFactoryState] = useState('STANDBY'); // 'STANDBY', 'WARPING', 'ACTIVE'
  const [warpProgress, setWarpProgress] = useState(0);
  const [systemAlert, setSystemAlert] = useState('SYSTEMS_OK');

  // Sound Synth engine
  const playSynth = (type) => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();

      if (type === 'beep') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(1000, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(500, ctx.currentTime + 0.05);
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.07);
        osc.start();
        osc.stop(ctx.currentTime + 0.07);
      } else if (type === 'ignition') {
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gain = ctx.createGain();
        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(ctx.destination);
        osc1.type = 'sawtooth';
        osc1.frequency.setValueAtTime(80, ctx.currentTime);
        osc1.frequency.linearRampToValueAtTime(450, ctx.currentTime + 2.0);
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(160, ctx.currentTime);
        osc2.frequency.exponentialRampToValueAtTime(900, ctx.currentTime + 2.0);
        gain.gain.setValueAtTime(0.25, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 2.2);
        osc1.start();
        osc2.start();
        osc1.stop(ctx.currentTime + 2.2);
        osc2.stop(ctx.currentTime + 2.2);
      } else if (type === 'gate') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(150, ctx.currentTime);
        osc.frequency.linearRampToValueAtTime(400, ctx.currentTime + 0.6);
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
        osc.start();
        osc.stop(ctx.currentTime + 0.6);
      }
    } catch (e) {
      console.log('Audio Context suppressed by user agent permissions.');
    }
  };

  // Canvas loop rendering particle steam exhaust and drones
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let animationId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Steam particles
    const numSteam = 30;
    const steam = [];
    for (let i = 0; i < numSteam; i++) {
      steam.push({
        x: Math.random() * width,
        y: height - Math.random() * 200,
        vx: (Math.random() - 0.5) * 1.5,
        vy: -0.5 - Math.random() * 1.5,
        size: 10 + Math.random() * 40,
        alpha: 0.05 + Math.random() * 0.15
      });
    }

    // Flying inspector drones
    const numDrones = 8;
    const drones = [];
    for (let i = 0; i < numDrones; i++) {
      drones.push({
        x: Math.random() * width,
        y: Math.random() * (height - 300),
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 1.2,
        size: 2,
        color: i % 2 === 0 ? '#00f0ff' : '#ff7700'
      });
    }

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const render = () => {
      ctx.fillStyle = '#06070a';
      ctx.fillRect(0, 0, width, height);

      // Industrial Grid alignment lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.015)';
      ctx.lineWidth = 1;
      const step = 60;
      for (let x = 0; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Draw steam chimney vents particles
      ctx.fillStyle = 'rgba(120, 130, 140, 0.5)';
      steam.forEach(s => {
        s.x += s.vx;
        s.y += s.vy;
        if (s.y < 0 || s.alpha <= 0.002) {
          s.y = height;
          s.x = Math.random() * width;
          s.alpha = 0.05 + Math.random() * 0.15;
        }
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, 2 * Math.PI);
        ctx.fillStyle = `rgba(100, 110, 120, ${s.alpha})`;
        ctx.fill();
        s.alpha -= 0.0005;
      });

      // Draw flying inspector drones
      drones.forEach(d => {
        d.x += d.vx * (factoryState === 'ACTIVE' ? 6 : 1);
        d.y += d.vy * (factoryState === 'ACTIVE' ? 6 : 1);
        if (d.x < 0 || d.x > width) d.vx *= -1;
        if (d.y < 0 || d.y > height) d.vy *= -1;

        ctx.beginPath();
        ctx.arc(d.x, d.y, d.size, 0, 2 * Math.PI);
        ctx.fillStyle = d.color;
        ctx.shadowBlur = 8;
        ctx.shadowColor = d.color;
        ctx.fill();
      });

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
    };
  }, [factoryState]);

  // Reactor Core temp warning triggers
  useEffect(() => {
    if (factoryState === 'WARPING') {
      setSystemAlert('WARNING_REACTOR_HEATING');
    }
  }, [factoryState]);

  // Main Reactor Ignition console CTA handler
  const handleIgnition = () => {
    if (factoryState !== 'STANDBY') return;
    setFactoryState('WARPING');
    playSynth('ignition');

    let prog = 0;
    const interval = setInterval(() => {
      prog += 5;
      setWarpProgress(prog);
      if (prog >= 100) {
        clearInterval(interval);
        setFactoryState('ACTIVE');
        setTimeout(() => {
          navigate('/login');
        }, 500);
      }
    }, 100);
  };

  const zones = [
    { id: '1', name: 'Zone 1: Intake Scanner', label: 'USER REQUEST SCANNER', icon: <Terminal size={16} />, status: 'SCANNED', telemetry: 'Request complexity: LOW • Language: EN-US', details: 'Ingests user prompt payloads, tokenizes strings, and calculates initial agent routing workflows.', tech: 'BERT encoder classification tags.' },
    { id: '2', name: 'Zone 2: Planning Center', label: 'WORKFLOW GANTRY', icon: <Workflow size={16} />, status: 'DECOMPOSED', telemetry: 'Orchestration nodes active: 4 • Step count: 6', details: 'Decomposes task commands into execution lists and allocates CPU worker chambers.', tech: 'Structured JSON planning models.' },
    { id: '3', name: 'Zone 3: Research Laboratory', label: 'DOCUMENT CRAWLER', icon: <Globe size={16} />, status: 'SYNCHRONIZED', telemetry: 'Vector lookup indexes: ChromaDB • Web Ping: 12ms', details: 'Crawls local project files, retrieves API documentation, and fetches external web assets.', tech: 'Google Custom Search and local indexes.' },
    { id: '4', name: 'Zone 4: Memory Crypt', label: 'CONTEXT RETRIEVAL', icon: <Database size={16} />, status: 'LOADED', telemetry: 'Relevant memories hit: 3 • Cache OK', details: 'Indexes past queries context structures to align answer styles and prevent duplicate execution.', tech: 'ChromaDB local vector files.' },
    { id: '5', name: 'Zone 5: MCP Integration Hub', label: 'API AIRPORT DOCK', icon: <Server size={16} />, status: 'CONNECTED', telemetry: 'AWS S3, Slack, Docker: ACTIVE • Sync OK', details: 'Bridges executor runtimes to external channels, database layers, and deployment servers.', tech: 'Model Context Protocol adapters.' },
    { id: '6', name: 'Zone 6: Quantum Chamber', label: 'COMMAND PROCESSOR', icon: <Cpu size={16} />, status: 'COMPILING', telemetry: 'EC2 instance code: running • Log print OK', details: 'Executes commands inside sandboxed files folders, compiles files, and packages reports.', tech: 'Docker compiler cluster nodes.' },
    { id: '7', name: 'Zone 7: Quality Inspect', label: 'ACCURACY CRITIC', icon: <ShieldCheck size={16} />, status: 'APPROVED', telemetry: 'Confidence rating: 98.6% • Critic OK', details: 'Validates code execution outputs, fact-checks references, and signs security approval.', tech: 'Orchestrator critic loops.' },
    { id: '8', name: 'Zone 8: Delivery Platform', label: 'INTELLIGENCE ASSEMBLY', icon: <Layers size={16} />, status: 'DELIVERED', telemetry: 'Payload size: 14KB • MD5 verified', details: 'Packages the verified context files, triggers workspace rendering, and sends final report.', tech: 'Markdown visualization display.' }
  ];

  const activeZoneData = zones.find(z => z.id === activeZone);

  return (
    <div className="bg-[#06070a] text-slate-100 min-h-screen overflow-x-hidden font-sans relative selection:bg-cyan-500/30 selection:text-white pb-20">
      
      {/* Background Grid Canvas */}
      <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none z-0" />

      {/* Industrial Neon Vignette overlay */}
      <div className="fixed inset-0 pointer-events-none z-0 bg-[radial-gradient(circle_at_center,rgba(0,0,0,0)_60%,rgba(6,7,10,0.9))]"></div>

      {/* Floating Header */}
      <header className="h-20 border-b border-white/5 bg-[#06070ac0] backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-6 md:px-12 select-none">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-400 to-indigo-500 flex items-center justify-center shadow-lg shadow-cyan-500/10">
            <Zap size={18} className="text-black" />
          </div>
          <span className="font-bold text-sm tracking-wider bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">AEGISAI</span>
        </div>

        <div className="hidden md:flex items-center gap-8 text-[9px] font-mono text-slate-500">
          <span>ALERTS: {systemAlert}</span>
          <span>•</span>
          <span>STATUS: ONLINE</span>
        </div>

        <div className="flex items-center gap-6">
          <button onClick={() => { playSynth('beep'); navigate('/login'); }} className="btn-primary py-1.5 px-4 rounded-lg text-xs font-semibold cursor-pointer">
            ACCESS_PORTAL
          </button>
        </div>
      </header>

      {/* ========================================================
          OPENING SCENE: GIGAFACTORY HANGAR GATES
          ======================================================== */}
      {!tourStarted ? (
        <section className="h-[calc(100vh-80px)] flex flex-col justify-center items-center px-6 relative z-10 text-center">
          
          {/* Gigafactory entrance gate SVG representation */}
          <div className="w-80 h-56 relative mb-12 flex flex-col items-center justify-center border border-white/5 rounded-2xl bg-[#090b1080] shadow-2xl relative group overflow-hidden">
            {/* Sliding gates grids */}
            <div className="absolute inset-x-0 top-0 h-1/2 border-b border-white/5 bg-[#12162095] group-hover:-translate-y-full transition-transform duration-500 flex items-end justify-center pb-2">
              <span className="text-[8px] text-slate-500 font-mono tracking-widest uppercase">HANGAR_GATE_01_A</span>
            </div>
            <div className="absolute inset-x-0 bottom-0 h-1/2 border-t border-white/5 bg-[#12162095] group-hover:translate-y-full transition-transform duration-500 flex items-start justify-center pt-2">
              <span className="text-[8px] text-slate-500 font-mono tracking-widest uppercase">HANGAR_GATE_01_B</span>
            </div>

            <Zap size={32} className="text-cyan-400 animate-pulse" />
          </div>

          <span className="text-[10px] text-slate-500 font-mono tracking-widest uppercase mb-2">Factory Entrance</span>
          <h1 className="text-4xl md:text-6xl font-extrabold text-white tracking-wider leading-none">
          AEGISAI
        </h1>
          <p className="text-xs text-slate-400 mt-3 max-w-md mx-auto leading-relaxed">
            Initialize the security protocol handshake link to open the factory gates and enter the production line deck.
          </p>

          <button 
            onClick={() => { playSynth('gate'); navigate('/login'); }}
            className="btn-primary py-2.5 px-8 rounded-lg text-xs font-bold gap-2 cursor-pointer shadow-lg shadow-cyan-500/10 mt-8"
          >
            INITIATE_TOUR <ArrowRight size={14} />
          </button>

        </section>
      ) : (
        /* ========================================================
            THE MAIN ASSEMBLY LINE COCKPIT
            ======================================================== */
        <section className="py-12 px-6 md:px-12 relative z-10 max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8 animate-fade-in">
          
          {/* Column 1: Assembly flow line selector */}
          <div className="lg:col-span-1 flex flex-col gap-2 border-r border-white/5 pr-4">
            <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider mb-2 block">Production line zones</span>
            
            {zones.map((z) => (
              <button
                key={z.id}
                onClick={() => { playSynth('beep'); setActiveZone(z.id); }}
                className={`p-3 rounded-lg border text-left text-xs transition-all flex items-center justify-between cursor-pointer ${activeZone === z.id ? 'bg-cyan-500/5 border-cyan-500/25 text-cyan-400 shadow-md shadow-cyan-500/5' : 'bg-transparent border-transparent text-slate-400 hover:text-white'}`}
              >
                <span>{z.name}</span>
                <span className="text-[8px] font-mono text-slate-500">{z.status}</span>
              </button>
            ))}
          </div>

          {/* Column 2 & 3: active Zone Holographic Visualizer */}
          <div className="lg:col-span-2 glass-panel p-6 border-white/5 bg-[#0d101750] shadow-lg flex flex-col justify-between min-h-[380px]">
            
            <div className="flex justify-between items-start border-b border-white/5 pb-3">
              <div>
                <span className="text-[8px] text-slate-500 font-mono uppercase tracking-wider block">{activeZoneData.label}</span>
                <h3 className="text-md font-bold text-white tracking-wide mt-1">{activeZoneData.name}</h3>
              </div>
              <div className="flex items-center gap-1.5 font-mono text-[9px] text-cyan-400 bg-cyan-500/10 px-2.5 py-0.5 rounded animate-pulse">
                <RotateCw size={10} className="animate-spin-slow" />
                <span>CONVEYOR_ACTIVE</span>
              </div>
            </div>

            {/* Interactive Mechanical Machinery Blueprint (SVG graphics) */}
            <div className="my-8 flex items-center justify-center relative min-h-[160px]">
              
              {/* Central gear spinning mechanism */}
              <div className="w-24 h-24 border border-dashed border-cyan-500/20 rounded-full flex items-center justify-center animate-spin-slow">
                <RotateCw size={24} className="text-cyan-400" />
              </div>

              {/* Laser scanner grid overlay lines */}
              <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent top-1/2 -translate-y-1/2 animate-pulse"></div>

              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <line x1="20" y1="80" x2="80" y2="80" stroke="rgba(0,240,255,0.15)" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="220" y1="80" x2="280" y2="80" stroke="rgba(189,0,255,0.15)" strokeWidth="1" strokeDasharray="3 3" />
              </svg>
            </div>

            <div className="border-t border-white/5 pt-4 text-xs">
              <span className="text-[9px] text-slate-500 font-mono uppercase block">Active Process details</span>
              <p className="text-slate-400 mt-1 leading-relaxed">{activeZoneData.details}</p>
            </div>

          </div>

          {/* Column 4: Ticker telemetry logs terminal */}
          <div className="lg:col-span-1 glass-panel p-6 border-white/5 bg-[#0d101780] shadow-lg flex flex-col justify-between">
            <div>
              <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider block">Telemetry console</span>
              <h4 className="text-xs font-bold text-white tracking-wide mt-1">Live Logs Terminal</h4>
              
              <div className="mt-4 flex flex-col gap-2.5 font-mono text-[10px] text-slate-400">
                <div className="p-2.5 rounded bg-white/2 border border-white/3 text-[9px] text-cyan-400">
                  {activeZoneData.telemetry}
                </div>
                <div className="flex justify-between items-center text-[9px] text-slate-500 mt-1">
                  <span>Compiler: OK</span>
                  <span>Latency: 12ms</span>
                </div>
              </div>
            </div>

            <div className="mt-8 border-t border-white/5 pt-4">
              <span className="text-[9px] text-slate-500 font-mono uppercase block">Technological stack</span>
              <span className="font-semibold text-cyan-400 font-mono text-[10px] block mt-1">{activeZoneData.tech}</span>
            </div>
          </div>

          {/* ========================================================
              ACTIVE REACTOR CORE: ACTIVATE AEGISAI (CTA)
              ======================================================== */}
          <div className="lg:col-span-4 glass-panel p-8 border-purple-500/15 bg-gradient-to-b from-[#0d1017e0] to-[#06070ae0] shadow-2xl relative overflow-hidden mt-8 text-center flex flex-col items-center">
            
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(189,0,255,0.01)_1px,transparent_0)]" style={{ backgroundSize: '100% 4px' }}></div>

            <span className="text-[9px] text-purple-400 font-mono font-bold tracking-widest uppercase">System Reactor Console</span>
            <h3 className="text-xl font-bold text-white mt-3 tracking-wide">Ignite AegisAI Operations</h3>
            <p className="text-xs text-slate-400 mt-2 max-w-md leading-relaxed">
              Fire up the core engines, spin the assembly gears, and open the active system operator dashboard gates.
            </p>

            <div className="mt-8 w-full max-w-xs">
              {factoryState === 'WARPING' ? (
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center text-[10px] font-mono text-cyan-400">
                    <span>HEATING PROCESSORS...</span>
                    <span>{warpProgress}%</span>
                  </div>
                  <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-cyan-400 h-full transition-all duration-100" style={{ width: `${warpProgress}%` }}></div>
                  </div>
                </div>
              ) : (
                <button
                  onClick={handleIgnition}
                  disabled={factoryState === 'ACTIVE'}
                  className="w-full py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-black font-bold tracking-widest text-xs shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30 transition-all cursor-pointer border border-cyan-400/20 disabled:opacity-50"
                >
                  [ ACTIVATE AEGISAI ]
                </button>
              )}
            </div>

            <div className="grid grid-cols-3 gap-6 w-full max-w-md mt-10 text-left border-t border-white/5 pt-6 text-[10px] font-mono text-slate-500">
              <div>
                <span>REACTOR_ONLINE: 100%</span>
                <span className="block mt-1 text-[9px] text-cyan-400">PLANNER OK</span>
              </div>
              <div>
                <span>VAULT_CACHE: FLUSHED</span>
                <span className="block mt-1 text-[9px] text-purple-400">CHROMADB OK</span>
              </div>
              <div>
                <span>MCP_LINK: CONNECTED</span>
                <span className="block mt-1 text-[9px] text-emerald-400">AWS, DOCKER OK</span>
              </div>
            </div>

          </div>

        </section>
      )}

      {/* Footer */}
      <footer className="py-12 px-6 md:px-12 border-t border-white/5 relative z-10 bg-[#06070a90] select-none">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-400 to-indigo-500 flex items-center justify-center">
              <Layers size={16} className="text-black" />
            </div>
            <span className="font-bold text-xs tracking-wider bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">AEGIS_OS</span>
          </div>

          <span className="text-[10px] text-slate-500 font-mono">
            © 2026 AEGISAI. CONVEYOR SHIFT SYSTEM SECURE.
          </span>
        </div>
      </footer>

    </div>
  );
}
