import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

/**
 * Enterprise CodeBlock Component with syntax styling and copy action
 */
export function CodeBlock({
  code,
  language = 'json',
  title = null,
  showLineNumbers = false,
  className = '',
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!code) return;
    try {
      await navigator.clipboard.writeText(typeof code === 'string' ? code : JSON.stringify(code, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.warn('Clipboard write failed:', e);
    }
  };

  const formattedCode = typeof code === 'string' ? code : JSON.stringify(code, null, 2);

  return (
    <div className={`rounded-xl border border-white/[0.08] bg-[#090b10] overflow-hidden text-xs font-mono ${className}`}>
      {(title || language) && (
        <div className="px-4 py-2 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between gap-3 text-slate-400">
          <span className="font-sans font-medium text-slate-300">{title || language.toUpperCase()}</span>
          <button
            type="button"
            onClick={handleCopy}
            aria-label="Copy code to clipboard"
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition-colors cursor-pointer py-0.5 px-1.5 rounded hover:bg-white/5"
          >
            {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      )}

      <div className="p-4 overflow-x-auto text-slate-200">
        <pre className="m-0 leading-relaxed font-mono whitespace-pre">{formattedCode}</pre>
      </div>
    </div>
  );
}
