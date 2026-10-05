import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card, CardContent } from './Card';

/**
 * Enterprise MetricCard Component for KPI strips & dashboards
 */
export function MetricCard({
  title,
  value,
  trend = null, // e.g. { direction: 'up'|'down'|'neutral', value: '+12.5%', label: 'vs last week' } OR string "Operational"
  subtitle = null,
  icon = null,
  description = null,
  className = '',
  onClick,
}) {
  const renderTrend = () => {
    if (!trend) return null;

    if (typeof trend === 'string') {
      return (
        <div className="flex items-center gap-1.5 mt-2">
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-1.5 py-0.5 rounded border text-cyan-300 bg-cyan-500/10 border-cyan-500/20 font-mono">
            {trend}
          </span>
        </div>
      );
    }

    const { direction, value: trendValue, label } = trend;
    const isUp = direction === 'up';
    const isDown = direction === 'down';

    const colorClass = isUp
      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      : isDown
      ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
      : 'text-slate-400 bg-slate-500/10 border-slate-500/20';

    const Icon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

    return (
      <div className="flex items-center gap-1.5 mt-2">
        <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-1.5 py-0.5 rounded border ${colorClass}`}>
          <Icon size={12} />
          {trendValue}
        </span>
        {label && <span className="text-[11px] text-slate-500">{label}</span>}
      </div>
    );
  };

  const descText = description || subtitle;

  return (
    <Card onClick={onClick} className={`relative overflow-hidden ${className}`}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">{title}</span>
          {icon && <div className="p-2 rounded-lg bg-white/5 text-cyan-400 border border-white/5">{icon}</div>}
        </div>
        <div className="text-2xl font-bold font-mono tracking-tight text-slate-100 mt-2">{value}</div>
        {renderTrend()}
        {descText && <p className="text-xs text-slate-500 mt-2">{descText}</p>}
      </CardContent>
    </Card>
  );
}
