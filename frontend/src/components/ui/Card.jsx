import React from 'react';

/**
 * Enterprise Card Component with header, content, and footer sub-components
 */
export function Card({ children, className = '', glow = false, onClick, ...props }) {
  const glowStyle = glow ? 'border-cyan-500/30 shadow-[0_0_15px_rgba(0,240,255,0.05)]' : 'border-white/[0.08]';
  const interactiveStyle = onClick ? 'hover:border-white/20 cursor-pointer transition-all duration-200' : '';

  return (
    <div
      onClick={onClick}
      className={`bg-[#0d101780] backdrop-blur-md rounded-xl border ${glowStyle} ${interactiveStyle} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }) {
  return (
    <div className={`px-5 py-4 border-b border-white/[0.06] flex items-center justify-between gap-3 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '', as: Component = 'h3', ...props }) {
  return (
    <Component className={`text-sm font-semibold tracking-wide text-slate-100 ${className}`} {...props}>
      {children}
    </Component>
  );
}

export function CardDescription({ children, className = '', ...props }) {
  return (
    <p className={`text-xs text-slate-400 mt-0.5 ${className}`} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ children, className = '', ...props }) {
  return (
    <div className={`p-5 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className = '', ...props }) {
  return (
    <div className={`px-5 py-3 border-t border-white/[0.06] bg-white/[0.01] flex items-center justify-between gap-3 rounded-b-xl ${className}`} {...props}>
      {children}
    </div>
  );
}
