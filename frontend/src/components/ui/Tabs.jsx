import React, { useState } from 'react';

/**
 * Enterprise Tabs Component
 */
export function Tabs({
  tabs = [], // [{ id, label, icon, badge }]
  activeTab,
  onChange,
  variant = 'pill', // 'pill' | 'underline'
  className = '',
}) {
  return (
    <div
      role="tablist"
      className={`flex items-center gap-1.5 overflow-x-auto p-1 select-none ${
        variant === 'pill' ? 'bg-[#0d1017] rounded-lg border border-white/[0.06]' : 'border-b border-white/[0.08]'
      } ${className}`}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        const variantStyles =
          variant === 'pill'
            ? isActive
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border border-transparent'
            : isActive
            ? 'text-cyan-400 border-b-2 border-cyan-400 -mb-[1px] font-semibold'
            : 'text-slate-400 hover:text-slate-200 border-b-2 border-transparent';

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer shrink-0 ${variantStyles}`}
          >
            {tab.icon && <span className="shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                  isActive ? 'bg-cyan-400 text-black font-bold' : 'bg-white/10 text-slate-400'
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Enterprise Tooltip Component
 */
export function Tooltip({ children, content, position = 'top', className = '' }) {
  const [visible, setVisible] = useState(false);

  if (!content) return children;

  const posStyles = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-1.5',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-1.5',
    left: 'right-full top-1/2 -translate-y-1/2 mr-1.5',
    right: 'left-full top-1/2 -translate-y-1/2 ml-1.5',
  };

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div
          role="tooltip"
          className={`absolute z-50 px-2.5 py-1 text-[11px] font-medium text-slate-200 bg-[#161b22] border border-white/10 rounded-md shadow-lg whitespace-nowrap pointer-events-none animate-fade-in ${posStyles[position]} ${className}`}
        >
          {content}
        </div>
      )}
    </div>
  );
}
