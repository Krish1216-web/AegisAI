import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

/**
 * Enterprise Breadcrumb Navigation Component
 */
export function Breadcrumb({ items = [], className = '' }) {
  if (!items || items.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className={`flex items-center gap-1.5 text-xs text-slate-400 ${className}`}>
      <Link to="/" className="hover:text-cyan-400 transition-colors flex items-center gap-1">
        <Home size={13} />
      </Link>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <React.Fragment key={item.label || index}>
            <ChevronRight size={12} className="text-slate-600 shrink-0" />
            {isLast || !item.to ? (
              <span className={`font-medium ${isLast ? 'text-slate-200' : 'text-slate-400'}`}>
                {item.label}
              </span>
            ) : (
              <Link to={item.to} className="hover:text-cyan-400 transition-colors font-medium">
                {item.label}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
