import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

/**
 * Enterprise Table Components
 */
export function Table({ children, className = '' }) {
  return (
    <div className="w-full overflow-x-auto rounded-xl border border-white/[0.08] bg-[#0d101740]">
      <table className={`w-full text-left border-collapse text-sm text-slate-200 ${className}`}>
        {children}
      </table>
    </div>
  );
}

export function TableHeader({ children, className = '' }) {
  return <thead className={`border-b border-white/[0.08] bg-white/[0.02] text-xs font-semibold uppercase tracking-wider text-slate-400 ${className}`}>{children}</thead>;
}

export function TableBody({ children, className = '' }) {
  return <tbody className={`divide-y divide-white/[0.04] ${className}`}>{children}</tbody>;
}

export function TableRow({ children, className = '', isClickable = false, onClick = null }) {
  return (
    <tr
      onClick={onClick}
      className={`transition-colors duration-100 ${
        isClickable ? 'hover:bg-white/[0.04] cursor-pointer' : 'hover:bg-white/[0.02]'
      } ${className}`}
    >
      {children}
    </tr>
  );
}

export function TableHead({ children, className = '', sortable = false, onSort = null }) {
  return (
    <th
      onClick={sortable ? onSort : undefined}
      className={`px-4 py-3 text-xs font-semibold select-none ${
        sortable ? 'cursor-pointer hover:text-cyan-400' : ''
      } ${className}`}
    >
      {children}
    </th>
  );
}

export function TableCell({ children, className = '' }) {
  return <td className={`px-4 py-3.5 text-xs text-slate-300 align-middle ${className}`}>{children}</td>;
}

/**
 * Enterprise Pagination Component
 */
export function Pagination({
  currentPage = 1,
  totalPages = 1,
  totalItems = null,
  pageSize = 10,
  onPageChange,
  className = '',
}) {
  if (totalPages <= 1 && !totalItems) return null;

  return (
    <div className={`flex items-center justify-between gap-4 py-3 px-2 text-xs text-slate-400 select-none ${className}`}>
      <div>
        {totalItems !== null && (
          <span>
            Showing <strong className="text-slate-200 font-mono">{(currentPage - 1) * pageSize + 1}</strong> to{' '}
            <strong className="text-slate-200 font-mono">{Math.min(currentPage * pageSize, totalItems)}</strong> of{' '}
            <strong className="text-slate-200 font-mono">{totalItems}</strong> entries
          </span>
        )}
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(1)}
          aria-label="First page"
          className="p-1 rounded hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
        >
          <ChevronsLeft size={16} />
        </button>
        <button
          type="button"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          aria-label="Previous page"
          className="p-1 rounded hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
        >
          <ChevronLeft size={16} />
        </button>

        <span className="px-2 font-mono text-slate-300">
          Page {currentPage} of {Math.max(1, totalPages)}
        </span>

        <button
          type="button"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          aria-label="Next page"
          className="p-1 rounded hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
        >
          <ChevronRight size={16} />
        </button>
        <button
          type="button"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(totalPages)}
          aria-label="Last page"
          className="p-1 rounded hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
        >
          <ChevronsRight size={16} />
        </button>
      </div>
    </div>
  );
}
