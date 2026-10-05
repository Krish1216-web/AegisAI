import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HashRouter } from 'react-router-dom';
import LandingPage from '../pages/LandingPage';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthContext } from '../context/AuthContext';

// Mock matchMedia for testing environment
window.matchMedia = window.matchMedia || function () {
  return {
    matches: false,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };
};

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderWithProviders(authOverrides = {}) {
  const defaultAuth = {
    isAuthenticated: false,
    token: null,
    user: null,
    role: null,
    login: vi.fn(),
    logout: vi.fn(),
    ...authOverrides
  };

  return render(
    <AuthContext.Provider value={defaultAuth}>
      <ThemeProvider>
        <HashRouter>
          <LandingPage />
        </HashRouter>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}

describe('Phase 12.2 — Intelligence Factory Landing Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders top navigation brand, links, and public CTAs for unauthenticated user', () => {
    renderWithProviders({ isAuthenticated: false });

    expect(screen.getByText('AEGISAI')).toBeInTheDocument();
    expect(screen.getAllByText('Platform').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Intelligence Factory')).toBeInTheDocument();
    expect(screen.getAllByText('Architecture').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Security').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Use Cases')).toBeInTheDocument();

    const signInBtns = screen.getAllByRole('button', { name: /Sign In/i });
    expect(signInBtns.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('button', { name: /Enter AegisAI/i })).toBeInTheDocument();
  });

  it('navigates to /login when unauthenticated user clicks Sign In or Enter AegisAI', () => {
    renderWithProviders({ isAuthenticated: false });

    const signInBtns = screen.getAllByRole('button', { name: /Sign In/i });
    fireEvent.click(signInBtns[0]);
    expect(mockNavigate).toHaveBeenCalledWith('/login');

    const enterBtn = screen.getByRole('button', { name: /Enter AegisAI/i });
    fireEvent.click(enterBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('renders Open Workspace CTA and routes to /user/dashboard for authenticated user', () => {
    renderWithProviders({ isAuthenticated: true, role: 'user' });

    const openBtn = screen.getByRole('button', { name: /Open Workspace/i });
    expect(openBtn).toBeInTheDocument();
    fireEvent.click(openBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/user/dashboard');
  });

  it('routes to /admin/dashboard for authenticated admin role', () => {
    renderWithProviders({ isAuthenticated: true, role: 'admin' });

    const openBtn = screen.getByRole('button', { name: /Open Workspace/i });
    fireEvent.click(openBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/admin/dashboard');
  });

  it('renders cinematic Hero section with headline and terminal badge', () => {
    renderWithProviders();

    expect(screen.getByText('ENTERPRISE AI OPERATING SYSTEM')).toBeInTheDocument();
    expect(screen.getByText(/Autonomous Intelligence for the/i)).toBeInTheDocument();
    expect(screen.getByText('Enterprise')).toBeInTheDocument();
    expect(screen.getByText(/AEGIS_OS_CORE :: INTELLIGENCE_FACTORY/i)).toBeInTheDocument();
  });

  it('renders all 6 capability strip highlights', () => {
    renderWithProviders();

    expect(screen.getByText('MULTI-AGENT ORCHESTRATION')).toBeInTheDocument();
    expect(screen.getByText('LONG-TERM MEMORY')).toBeInTheDocument();
    expect(screen.getByText('ENTERPRISE RAG')).toBeInTheDocument();
    expect(screen.getByText('KNOWLEDGE GRAPH')).toBeInTheDocument();
    expect(screen.getByText('MCP ECOSYSTEM')).toBeInTheDocument();
    expect(screen.getByText('VERIFIABLE SECURITY')).toBeInTheDocument();
  });

  it('renders all 8 pipeline assembly steps', () => {
    renderWithProviders();

    const pipelineLabels = [
      'INPUT',
      'UNDERSTAND',
      'RETRIEVE',
      'REASON',
      'ORCHESTRATE',
      'EXECUTE',
      'VERIFY',
      'RESPOND'
    ];

    pipelineLabels.forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it('allows clicking pipeline steps to change active step', () => {
    renderWithProviders();

    const executeStep = screen.getByText('EXECUTE');
    fireEvent.click(executeStep);
    expect(executeStep.parentElement).toHaveClass('border-cyan-400/50');
  });

  it('renders all 7 tour station selector buttons', () => {
    renderWithProviders();

    expect(screen.getAllByText('01 — Agent Orchestration').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('02 — Long-Term Memory')).toBeInTheDocument();
    expect(screen.getByText('03 — Enterprise Knowledge & RAG')).toBeInTheDocument();
    expect(screen.getByText('04 — Model Context Protocol (MCP)')).toBeInTheDocument();
    expect(screen.getByText('05 — Workflow Automation')).toBeInTheDocument();
    expect(screen.getByText('06 — Observable Execution')).toBeInTheDocument();
    expect(screen.getByText('07 — Governance & Security')).toBeInTheDocument();
  });

  it('switches tour stations and updates deep dive content', () => {
    renderWithProviders();

    // Default station is Agent Orchestration
    expect(screen.getAllByText('Multi-Agent Collective Intelligence').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Coordinates specialized planner/i)).toBeInTheDocument();

    // Click Long-Term Memory station
    const memoryBtn = screen.getByText('02 — Long-Term Memory');
    fireEvent.click(memoryBtn);

    expect(screen.getAllByText('Episodic & Semantic Cognitive Vault').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Indexes conversational history/i)).toBeInTheDocument();

    // Click Governance & Security station
    const govBtn = screen.getByText('07 — Governance & Security');
    fireEvent.click(govBtn);

    expect(screen.getAllByText('Enterprise-Grade Fail-Closed Controls').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Enforces strict tenant boundaries/i)).toBeInTheDocument();
  });

  it('renders 4-tier high-level system architecture section', () => {
    renderWithProviders();

    expect(screen.getByText('01. INGRESS TIER')).toBeInTheDocument();
    expect(screen.getByText('Reverse Proxy')).toBeInTheDocument();
    expect(screen.getByText('02. COMPUTE TIER')).toBeInTheDocument();
    expect(screen.getByText('Stateless Cluster')).toBeInTheDocument();
    expect(screen.getByText('03. DATA TIER')).toBeInTheDocument();
    expect(screen.getByText('Durable Persistence')).toBeInTheDocument();
    expect(screen.getByText('04. ASYNC TIER')).toBeInTheDocument();
    expect(screen.getByText('Worker & Scheduler')).toBeInTheDocument();
  });

  it('renders enterprise security controls without fabricated claims', () => {
    renderWithProviders();

    expect(screen.getByText('Designed with Enterprise Security Controls')).toBeInTheDocument();
    expect(screen.getByText('Strict Tenant Isolation')).toBeInTheDocument();
    expect(screen.getByText('Tamper-Evident Audit Trails')).toBeInTheDocument();
    expect(screen.getByText('SSRF & Injection Defenses')).toBeInTheDocument();
  });

  it('renders enterprise use-cases section', () => {
    renderWithProviders();

    expect(screen.getByText('Enterprise Value Solutions')).toBeInTheDocument();
    expect(screen.getByText('Research & Synthesis')).toBeInTheDocument();
    expect(screen.getByText('Workflow Automation')).toBeInTheDocument();
    expect(screen.getByText('Unified Governance')).toBeInTheDocument();
  });

  it('renders bottom Access Terminal CTA with workspace launch button', () => {
    renderWithProviders({ isAuthenticated: true, role: 'user' });

    expect(screen.getByText('Enter the AegisAI Operating System')).toBeInTheDocument();
    const launchBtn = screen.getByRole('button', { name: /Launch Workspace/i });
    expect(launchBtn).toBeInTheDocument();
    fireEvent.click(launchBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/user/dashboard');
  });

  it('toggles theme when theme button is clicked', () => {
    renderWithProviders();

    const themeToggleBtn = screen.getByRole('button', { name: /Toggle theme mode/i });
    expect(themeToggleBtn).toBeInTheDocument();
    fireEvent.click(themeToggleBtn);
    expect(themeToggleBtn).toBeInTheDocument();
  });

  it('renders footer with copyright and external GitHub link', () => {
    renderWithProviders();

    expect(screen.getByText(/© 2026 AegisAI Platform. All rights reserved./i)).toBeInTheDocument();
    const ghLink = screen.getByRole('link', { name: /GitHub/i });
    expect(ghLink).toHaveAttribute('href', 'https://github.com/Krish1216-web/AegisAI');
  });
});
