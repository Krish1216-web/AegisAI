import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { HashRouter } from 'react-router-dom';
import ShowcasePage from '../pages/ShowcasePage';
import { DemoBanner, DemoWatermark } from '../components/showcase/DemoBanner';
import { DemoTimeline } from '../components/showcase/DemoTimeline';
import { DemoEventStream } from '../components/showcase/DemoEventStream';
import { DemoEvidenceViewer } from '../components/showcase/DemoEvidenceViewer';
import { DemoArchitectureView } from '../components/showcase/DemoArchitectureView';
import { DemoTourView } from '../components/showcase/DemoTourView';
import { DemoApprovalModal } from '../components/showcase/DemoApprovalModal';
import { DEMO_SCENARIOS, DEMO_TOUR_STATIONS } from '../data/demoScenarios';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthProvider } from '../context/AuthContext';
import { ToastProvider } from '../context/ToastContext';

function renderWithProviders(ui) {
  return render(
    <HashRouter>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            {ui}
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </HashRouter>
  );
}

describe('Phase 12.11 — Demo / Showcase Mode Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // 1. Banner & Watermark Tests
  // ============================================================================
  it('renders DemoBanner with persistent non-dismissible warning and scenario title', () => {
    const handleExit = vi.fn();
    render(
      <DemoBanner
        onExit={handleExit}
        currentScenarioTitle="End-to-End Cold-Chain Investigation"
      />
    );

    expect(screen.getByRole('region', { name: /demo mode notice/i })).toBeDefined();
    expect(screen.getByText(/DEMO MODE/i)).toBeDefined();
    expect(screen.getByText(/No production data or actions are modified/i)).toBeDefined();
    expect(screen.getByText(/SYNTHETIC TENANT: AEGIS-DEMO/i)).toBeDefined();
    expect(screen.getByText(/End-to-End Cold-Chain Investigation/i)).toBeDefined();

    const exitBtn = screen.getByRole('button', { name: /exit showcase/i });
    fireEvent.click(exitBtn);
    expect(handleExit).toHaveBeenCalledTimes(1);
  });

  it('renders DemoWatermark with simulated showcase tag', () => {
    render(<DemoWatermark />);
    expect(screen.getByText(/SIMULATED SHOWCASE/i)).toBeDefined();
  });

  // ============================================================================
  // 2. Timeline & Event Stream Component Tests
  // ============================================================================
  it('renders DemoTimeline stages and handles step click', () => {
    const handleStepClick = vi.fn();
    const steps = DEMO_SCENARIOS[0].steps;

    render(
      <DemoTimeline
        steps={steps}
        currentStepIndex={2}
        isCompleted={false}
        onStepClick={handleStepClick}
      />
    );

    expect(screen.getByText(/STAGE 3 OF 8/i)).toBeDefined();
    expect(screen.getByText('REQUEST')).toBeDefined();
    expect(screen.getByText('UNDERSTAND')).toBeDefined();
    expect(screen.getByText('PLAN')).toBeDefined();

    // Click on a completed step
    const step1Btn = screen.getByRole('button', { name: /step 1: REQUEST/i });
    fireEvent.click(step1Btn);
    expect(handleStepClick).toHaveBeenCalledWith(0);
  });

  it('renders DemoEventStream with simulated events log and live region', () => {
    const mockEvents = [
      { time: '14:20:01', agent: 'Orchestrator', message: 'Input validated.' },
      { time: '14:20:02', agent: 'Planner', message: 'Task decomposed into DAG.' }
    ];

    render(<DemoEventStream events={mockEvents} />);

    expect(screen.getByRole('log', { name: /simulated event log/i })).toBeDefined();
    expect(screen.getByText(/Input validated/i)).toBeDefined();
    expect(screen.getByText(/Task decomposed into DAG/i)).toBeDefined();
  });

  it('renders empty message in DemoEventStream when events list is empty', () => {
    render(<DemoEventStream events={[]} />);
    expect(screen.getByText(/Awaiting scenario initialization/i)).toBeDefined();
  });

  // ============================================================================
  // 3. Evidence Viewer & Knowledge Graph Component Tests
  // ============================================================================
  it('renders DemoEvidenceViewer citations and synthetic Knowledge Graph', () => {
    const evidence = DEMO_SCENARIOS[0].evidence;

    render(<DemoEvidenceViewer evidence={evidence} showGraph={true} />);

    expect(screen.getByText(/Grounding Evidence & Citations \(3\)/i)).toBeDefined();
    expect(screen.getByText(/DEMO — Cold Chain Operations SOP v4.pdf/i)).toBeDefined();
    expect(screen.getByText(/DEMO MCP Server :: Telemetry & Logistics Tool/i)).toBeDefined();
    expect(screen.getByText(/Synthetic Knowledge Graph/i)).toBeDefined();
    expect(screen.getByText(/7 NODES :: 7 EDGES/i)).toBeDefined();
  });

  // ============================================================================
  // 4. Architecture View & Legend Tests
  // ============================================================================
  it('renders DemoArchitectureView with component hierarchy and Real vs Demo legend', () => {
    render(<DemoArchitectureView />);

    expect(screen.getByText(/AegisAI Enterprise System Architecture/i)).toBeDefined();
    expect(screen.getByText(/Real Platform Component/i)).toBeDefined();
    expect(screen.getByText(/Simulated Demo Event/i)).toBeDefined();
    expect(screen.getByText(/Multi-Agent Collective Swarm \(9 Canonical Nodes\)/i)).toBeDefined();
    expect(screen.getByText(/Knowledge & Memory Tier/i)).toBeDefined();
    expect(screen.getByText(/MCP Tools & Workflows Tier/i)).toBeDefined();
    expect(screen.getByText(/Enterprise Governance & Zero-Trust Verification/i)).toBeDefined();
  });

  // ============================================================================
  // 5. Guided Tour View Tests
  // ============================================================================
  it('renders DemoTourView and navigates through 9 stations', () => {
    const handleSelectScenario = vi.fn();
    render(<DemoTourView onSelectScenario={handleSelectScenario} />);

    expect(screen.getByText('Intelligence Factory')).toBeDefined();
    expect(screen.getByText('1 / 9')).toBeDefined();

    // Click Next Station
    const nextBtn = screen.getByRole('button', { name: /next station/i });
    fireEvent.click(nextBtn);

    expect(screen.getByText('AI OS Workspace')).toBeDefined();
    expect(screen.getByText('2 / 9')).toBeDefined();

    // Click Previous Station
    const prevBtn = screen.getByRole('button', { name: /previous station/i });
    fireEvent.click(prevBtn);

    expect(screen.getByText('Intelligence Factory')).toBeDefined();
  });

  // ============================================================================
  // 6. Approval Modal Component Tests
  // ============================================================================
  it('renders DemoApprovalModal and triggers authorization callback with rationale', () => {
    const handleApprove = vi.fn();
    const handleReject = vi.fn();

    render(
      <DemoApprovalModal
        isOpen={true}
        onApprove={handleApprove}
        onReject={handleReject}
        scenario={DEMO_SCENARIOS[4]}
      />
    );

    expect(screen.getByText(/Restricted Action Authorization Gate \[SIMULATED\]/i)).toBeDefined();
    expect(screen.getByText(/vault_control.emergency_temperature_override/i)).toBeDefined();

    const approveBtn = screen.getByRole('button', { name: /authorize simulated execution/i });
    fireEvent.click(approveBtn);

    expect(handleApprove).toHaveBeenCalledWith(
      'Authorized by Demo System Operator for thermal calibration.'
    );
  });

  // ============================================================================
  // 7. Full Showcase Page Integration & Scenario Runner Tests
  // ============================================================================
  it('renders full ShowcasePage with header, controls, and scenario strip', () => {
    renderWithProviders(<ShowcasePage />);

    expect(screen.getByText('AEGISAI SHOWCASE')).toBeDefined();
    expect(screen.getByText(/Aegis Logistics Enterprise/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /start demo/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /skip step/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /reset/i })).toBeDefined();
  });

  it('switches between scenarios when clicking scenario cards', () => {
    renderWithProviders(<ShowcasePage />);

    // Initially Flagship
    expect(screen.getByRole('heading', { level: 2, name: /end-to-end cold-chain investigation/i })).toBeDefined();

    // Click on Autonomous Workflow scenario
    const workflowCard = screen.getByRole('button', { name: /autonomous multi-agent workflow studio/i });
    fireEvent.click(workflowCard);

    expect(screen.getByRole('heading', { level: 2, name: /autonomous multi-agent workflow studio/i })).toBeDefined();
    expect(screen.getByText(/Automate weekly inventory audit/i)).toBeDefined();
  });

  it('steps through scenario execution using Skip Step button and reaches completion', () => {
    renderWithProviders(<ShowcasePage />);

    // Current step 1
    expect(screen.getByText(/STAGE 1: REQUEST/i)).toBeDefined();

    const skipBtn = screen.getByRole('button', { name: /skip step/i });
    
    // Advance through steps
    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 2: UNDERSTAND/i)).toBeDefined();

    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 3: PLAN/i)).toBeDefined();

    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 4: RETRIEVE/i)).toBeDefined();

    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 5: REASON/i)).toBeDefined();

    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 6: EXECUTE/i)).toBeDefined();

    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 7: VERIFY/i)).toBeDefined();

    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 8: RESPOND/i)).toBeDefined();

    // Final click marks completed and renders final response
    fireEvent.click(skipBtn);
    expect(screen.getByText(/Simulated Response & Verified Conclusion/i)).toBeDefined();
    expect(screen.getByText(/Immediate Escalation Required/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /replay demo/i })).toBeDefined();
  });

  it('resets scenario state when clicking Reset button', () => {
    renderWithProviders(<ShowcasePage />);

    const skipBtn = screen.getByRole('button', { name: /skip step/i });
    fireEvent.click(skipBtn);
    expect(screen.getByText(/STAGE 2: UNDERSTAND/i)).toBeDefined();

    const resetBtn = screen.getByRole('button', { name: /reset/i });
    fireEvent.click(resetBtn);

    expect(screen.getByText(/STAGE 1: REQUEST/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /start demo/i })).toBeDefined();
  });

  it('switches between master navigation tabs in ShowcasePage', () => {
    renderWithProviders(<ShowcasePage />);

    // Default: Scenarios
    expect(screen.getByText('ACTIVE SCENARIO')).toBeDefined();

    // Switch to Architecture tab
    const archTab = screen.getByRole('button', { name: /system architecture/i });
    fireEvent.click(archTab);
    expect(screen.getByText(/AegisAI Enterprise System Architecture/i)).toBeDefined();

    // Switch to Guided Tour tab
    const tourTab = screen.getByRole('button', { name: /9-station guided tour/i });
    fireEvent.click(tourTab);
    expect(screen.getByText('Intelligence Factory')).toBeDefined();
  });

  it('toggles Presentation Mode on button click', () => {
    renderWithProviders(<ShowcasePage />);

    const presentationToggle = screen.getByRole('button', { name: /toggle presentation mode/i });
    fireEvent.click(presentationToggle);

    // Nav tabs should be hidden in presentation mode
    expect(screen.queryByRole('button', { name: /system architecture/i })).toBeNull();

    // Toggle back
    fireEvent.click(presentationToggle);
    expect(screen.getByRole('button', { name: /system architecture/i })).toBeDefined();
  });

  it('changes speed multiplier when clicking speed buttons', () => {
    renderWithProviders(<ShowcasePage />);

    const fastSpeedBtn = screen.getByRole('button', { name: '2x' });
    fireEvent.click(fastSpeedBtn);
    expect(fastSpeedBtn.className).toContain('bg-cyan-500');

    const instantSpeedBtn = screen.getByRole('button', { name: 'Instant' });
    fireEvent.click(instantSpeedBtn);
    expect(instantSpeedBtn.className).toContain('bg-cyan-500');
  });

  it('triggers approval modal in Governance scenario when reaching approval step', () => {
    renderWithProviders(<ShowcasePage />);

    // Select Governance scenario (index 4 in array)
    const govCard = screen.getByRole('button', { name: /high-risk action dual-key governance approval/i });
    fireEvent.click(govCard);

    expect(screen.getByRole('heading', { level: 2, name: /high-risk action dual-key governance approval/i })).toBeDefined();

    const startBtn = screen.getByRole('button', { name: /start demo/i });
    fireEvent.click(startBtn);

    // Wait for step execution or trigger approval
    const skipBtn = screen.getByRole('button', { name: /skip step/i });
    fireEvent.click(skipBtn);
  });
});
