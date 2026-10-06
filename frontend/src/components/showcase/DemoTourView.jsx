import React, { useState } from 'react';
import { Bot, ChevronRight, ChevronLeft, Sparkles, CheckCircle2, ArrowRight } from 'lucide-react';
import { DEMO_TOUR_STATIONS } from '../../data/demoScenarios';
import { Button } from '../ui';

export function DemoTourView({ onSelectScenario }) {
  const [activeStationIndex, setActiveStationIndex] = useState(0);
  const currentStation = DEMO_TOUR_STATIONS[activeStationIndex];

  return (
    <div className="flex flex-col gap-6">
      {/* Tour Station Cards Carousel / Grid */}
      <div className="p-4 rounded-xl border border-white/10 bg-[#0d1017] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center font-mono font-bold text-cyan-400 text-sm">
            {currentStation.step}
          </span>
          <div>
            <h3 className="text-sm font-bold text-slate-100">{currentStation.title}</h3>
            <p className="text-xs text-slate-400">{currentStation.subtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveStationIndex((prev) => Math.max(0, prev - 1))}
            disabled={activeStationIndex === 0}
            aria-label="Previous station"
            className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer text-slate-300"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-xs font-mono text-slate-400 px-2">
            {activeStationIndex + 1} / {DEMO_TOUR_STATIONS.length}
          </span>
          <button
            onClick={() => setActiveStationIndex((prev) => Math.min(DEMO_TOUR_STATIONS.length - 1, prev + 1))}
            disabled={activeStationIndex === DEMO_TOUR_STATIONS.length - 1}
            aria-label="Next station"
            className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer text-slate-300"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Main Tour Detail Panel */}
      <div className="p-6 rounded-xl border border-white/10 bg-[#0a0d14] flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 w-fit font-bold">
            {currentStation.tag}
          </span>
          <h4 className="text-lg font-bold text-slate-100">{currentStation.subtitle}</h4>
          <p className="text-sm text-slate-300 leading-relaxed">{currentStation.summary}</p>
        </div>

        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
            Core Enterprise Capabilities
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {currentStation.keyPoints.map((point, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2.5 p-3 rounded-lg border border-white/5 bg-white/[0.02]"
              >
                <CheckCircle2 size={15} className="text-cyan-400 shrink-0" />
                <span className="text-xs text-slate-200">{point}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick links to all 9 stations */}
        <div className="pt-4 border-t border-white/[0.08] flex items-center gap-2 overflow-x-auto pb-1">
          {DEMO_TOUR_STATIONS.map((st, i) => (
            <button
              key={st.id}
              onClick={() => setActiveStationIndex(i)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all shrink-0 cursor-pointer ${
                activeStationIndex === i
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-white/5 text-slate-400 hover:text-slate-200 border border-white/10'
              }`}
            >
              {st.step} {st.title.split(' — ')[1] || st.title}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
