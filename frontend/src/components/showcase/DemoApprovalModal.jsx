import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2, XCircle, AlertTriangle, Key } from 'lucide-react';
import { Modal, Button } from '../ui';

export function DemoApprovalModal({ isOpen, onApprove, onReject, scenario }) {
  const [rationale, setRationale] = useState('Authorized by Demo System Operator for thermal calibration.');

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onReject}
      title="Restricted Action Authorization Gate [SIMULATED]"
      size="lg"
    >
      <div className="flex flex-col gap-4 text-xs text-slate-300">
        <div className="p-3.5 rounded-lg border border-amber-500/30 bg-amber-500/10 flex items-start gap-3 text-amber-200">
          <ShieldAlert size={20} className="text-amber-400 shrink-0 mt-0.5" />
          <div className="flex flex-col gap-1">
            <span className="font-bold uppercase tracking-wider text-[11px]">
              High-Risk Facility Control Tool Requested
            </span>
            <p className="text-xs text-amber-300/90 leading-relaxed">
              Target Tool: <code className="px-1 py-0.5 rounded bg-black/40 font-mono text-cyan-300">vault_control.emergency_temperature_override</code>
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 p-3 rounded-lg bg-black/30 border border-white/10 font-mono text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-500">Target Facility:</span>
            <span className="text-slate-200">Ahmedabad Bio-Pharma Vault (AHM-01)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Target Temperature:</span>
            <span className="text-cyan-400 font-bold">4.0°C</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Policy Reference:</span>
            <span className="text-purple-400">POL-802 (Dual-Key Required)</span>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
            <Key size={13} className="text-cyan-400" />
            Mandatory Operator Approval Rationale:
          </label>
          <input
            type="text"
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            className="w-full bg-[#161b22] border border-white/15 rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500"
            placeholder="State authorization justification..."
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
          <Button variant="secondary" size="sm" onClick={onReject} leftIcon={<XCircle size={14} />}>
            Reject Request
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => onApprove(rationale)}
            leftIcon={<CheckCircle2 size={14} />}
          >
            Authorize Simulated Execution
          </Button>
        </div>
      </div>
    </Modal>
  );
}
