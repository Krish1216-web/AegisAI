import React, { Component } from 'react';
import { AlertTriangle, RefreshCw, Home, ShieldAlert } from 'lucide-react';
import { Button } from './Button';

/**
 * Enterprise Error Boundary Component
 * Gracefully isolates component render failures and provides recovery actions.
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // In production, we log error telemetry securely without exposing raw secrets
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleReload = () => {
    window.location.reload();
  };

  handleNavigateHome = () => {
    window.location.href = '#/';
    this.handleReset();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        if (typeof this.props.fallback === 'function') {
          return this.props.fallback({
            error: this.state.error,
            resetErrorBoundary: this.handleReset,
          });
        }
        return this.props.fallback;
      }

      const isInline = this.props.variant === 'inline';

      if (isInline) {
        return (
          <div
            role="alert"
            className="p-4 rounded-xl border border-rose-500/30 bg-rose-950/20 text-slate-200 flex flex-col gap-3 my-2"
          >
            <div className="flex items-center gap-2.5 text-rose-400 font-semibold text-xs uppercase tracking-wider">
              <AlertTriangle size={16} />
              <span>{this.props.title || 'Component Error'}</span>
            </div>
            <p className="text-xs text-slate-300">
              {this.state.error?.message || 'An unexpected rendering error occurred in this module.'}
            </p>
            <div className="flex items-center gap-2 pt-1">
              <Button variant="secondary" size="xs" onClick={this.handleReset}>
                <RefreshCw size={12} className="mr-1" /> Try Again
              </Button>
            </div>
          </div>
        );
      }

      return (
        <div
          role="alert"
          aria-live="assertive"
          className="min-h-[360px] w-full flex flex-col items-center justify-center p-8 text-center bg-[#0d1017]/80 backdrop-blur-md rounded-2xl border border-white/[0.08] shadow-2xl my-6"
        >
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mb-4 shadow-lg shadow-rose-500/10">
            <ShieldAlert size={28} />
          </div>

          <h2 className="text-lg font-bold text-white tracking-wide uppercase mb-1.5">
            {this.props.title || 'Interface Resilience Shield Engaged'}
          </h2>

          <p className="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
            {this.state.error?.message ||
              'A critical rendering exception was intercepted. Your session and tenant data remain securely protected.'}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button variant="secondary" size="sm" onClick={this.handleReset} className="flex items-center gap-1.5">
              <RefreshCw size={14} /> Try Again
            </Button>
            <Button variant="ghost" size="sm" onClick={this.handleReload} className="flex items-center gap-1.5">
              Reload Interface
            </Button>
            <Button variant="primary" size="sm" onClick={this.handleNavigateHome} className="flex items-center gap-1.5">
              <Home size={14} /> Return to Workspace
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
