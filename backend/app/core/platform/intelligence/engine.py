import uuid
import time
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.core.platform.context import PlatformContext
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.provenance import ProvenanceItem, ProvenanceSourceType, ProvenanceTrustLevel
from app.core.platform.events import PlatformEventType, PlatformEvent, PlatformEventDispatcher
from app.core.platform.intelligence.models import (
    RequirementType,
    ExecutionMode,
    AdaptiveDecisionType,
    ConfidenceLevel,
    RequirementAnalysisResult,
    PlanStep,
    IntelligencePlan,
    IntelligenceDecision,
    EvidenceEvaluationResult
)
from app.core.platform.intelligence.requirement_analyzer import RequirementAnalyzer
from app.core.platform.intelligence.capability_selector import CapabilitySelector
from app.core.platform.intelligence.planner import IntelligencePlanner
from app.core.platform.intelligence.evaluator import EvidenceEvaluator

MAX_ADAPTIVE_ATTEMPTS = 3

class AdvancedIntelligenceService:
    """
    Central orchestration service for Phase 8.7 Advanced Intelligence.
    Executes capability plans adaptively exclusively through PlatformExecutionService.
    """

    def __init__(self, db: Session):
        self.db = db
        from app.services.platform_execution import PlatformExecutionService
        self.execution_service = PlatformExecutionService(db)

    def execute_intelligent_query(
        self,
        query: str,
        context: PlatformContext,
        mode: ExecutionMode = ExecutionMode.ADAPTIVE,
        input_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for intelligent multi-capability orchestration.
        """
        start_time = time.time()
        input_data = input_data or {}
        correlation_id = context.correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        decisions: List[IntelligenceDecision] = []
        all_provenance: List[ProvenanceItem] = []
        step_outputs: List[Dict[str, Any]] = []

        if isinstance(mode, str):
            try:
                mode = ExecutionMode(mode.lower())
            except ValueError:
                mode = ExecutionMode.ADAPTIVE
        mode_val = mode.value

        # 1. Emit Initial Event
        PlatformEventDispatcher.emit(
            PlatformEvent(
                event_type=PlatformEventType.INTELLIGENCE_EVENT if hasattr(PlatformEventType, "INTELLIGENCE_EVENT") else PlatformEventType.SYSTEM_EVENT,
                correlation_id=correlation_id,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                source_component="advanced_intelligence_service",
                payload={"action": "intelligence_requested", "query": query, "mode": mode_val}
            )
        )

        # 2. Requirement Analysis
        analysis = RequirementAnalyzer.analyze(query, input_data)
        decisions.append(
            IntelligenceDecision(
                decision_type=AdaptiveDecisionType.CONTINUE,
                reason=analysis.intent_description,
                confidence_score=0.90,
                confidence_level=ConfidenceLevel.HIGH,
                metadata={"requirements": [r.value for r in analysis.identified_requirements]}
            )
        )

        # 3. Execution Planning
        plan = IntelligencePlanner.create_plan(context, analysis, mode=mode, input_data=input_data)
        
        PlatformEventDispatcher.emit(
            PlatformEvent(
                event_type=PlatformEventType.INTELLIGENCE_EVENT if hasattr(PlatformEventType, "INTELLIGENCE_EVENT") else PlatformEventType.SYSTEM_EVENT,
                correlation_id=correlation_id,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                source_component="intelligence_planner",
                payload={"action": "intelligence_plan_created", "total_steps": len(plan.steps), "mode": mode_val}
            )
        )

        # 4. Adaptive / Sequential Step Execution
        step_results: Dict[str, Any] = {}
        pending_confirmation_info = None
        current_status = LifecycleState.COMPLETED

        for step in plan.steps:
            attempt = 1
            step_completed = False
            step_output = None
            step.status = "RUNNING"

            PlatformEventDispatcher.emit(
                PlatformEvent(
                    event_type=PlatformEventType.INTELLIGENCE_EVENT if hasattr(PlatformEventType, "INTELLIGENCE_EVENT") else PlatformEventType.SYSTEM_EVENT,
                    correlation_id=correlation_id,
                    workspace_id=context.workspace_id,
                    user_id=context.user_id,
                    source_component="advanced_intelligence_service",
                    payload={"action": "intelligence_step_started", "step_id": step.step_id, "capability_id": step.capability_id}
                )
            )

            # Adaptive execution loop for current step
            while attempt <= MAX_ADAPTIVE_ATTEMPTS and not step_completed:
                target_cap_id = step.capability_id

                # Prepare step input
                step_input = dict(step.input_template)
                if step.requirement_type == RequirementType.MCP_TOOL:
                    if "risk_level" in input_data:
                        step_input["risk_level"] = input_data["risk_level"]
                    if "arguments" in input_data:
                        step_input["arguments"] = input_data["arguments"]
                    if "tool_name" in input_data:
                        step_input["tool_name"] = input_data["tool_name"]

                if attempt > 1 and step.requirement_type == RequirementType.DOCUMENT_EVIDENCE:
                    # Broaden search adaptively on subsequent attempts
                    step_input["top_k"] = min(step_input.get("top_k", 5) * 2, 50)
                    step_input["similarity_threshold"] = max(0.0, step_input.get("similarity_threshold", 0.0) - 0.1)

                # Execute capability strictly through PlatformExecutionService
                res = self.execution_service.execute(
                    capability_id=target_cap_id,
                    context=context,
                    input_data=step_input
                )

                # Collect provenance
                if res.provenance:
                    all_provenance.extend(res.provenance)

                # Check for MCP confirmation waiting state
                is_waiting = (
                    res.status == LifecycleState.WAITING 
                    or str(res.status).lower() == "waiting" 
                    or (isinstance(res.output, dict) and res.output.get("status") == "WAITING")
                    or (isinstance(res.output, dict) and res.output.get("confirmation_required"))
                )

                if is_waiting:
                    step.status = "WAITING"
                    current_status = LifecycleState.WAITING
                    pending_confirmation_info = {
                        "tool_name": res.output.get("tool_name") if isinstance(res.output, dict) else "mcp_tool",
                        "confirmation_token": res.output.get("confirmation_token") if isinstance(res.output, dict) else "TOKEN",
                        "step_id": step.step_id
                    }
                    decisions.append(
                        IntelligenceDecision(
                            decision_type=AdaptiveDecisionType.WAITING,
                            reason="Step requires single-use cryptographic confirmation",
                            confidence_score=0.85,
                            confidence_level=ConfidenceLevel.HIGH,
                            selected_capability_id=target_cap_id,
                            step_id=step.step_id,
                            attempt_number=attempt
                        )
                    )
                    break

                # Check for failure and fallback
                if res.status in [LifecycleState.FAILED, LifecycleState.DENIED]:
                    if step.fallback_capability_id and attempt < MAX_ADAPTIVE_ATTEMPTS:
                        decisions.append(
                            IntelligenceDecision(
                                decision_type=AdaptiveDecisionType.FALLBACK,
                                reason=f"Primary capability {target_cap_id} failed. Attempting fallback {step.fallback_capability_id}",
                                confidence_score=0.50,
                                confidence_level=ConfidenceLevel.MEDIUM,
                                selected_capability_id=step.fallback_capability_id,
                                step_id=step.step_id,
                                attempt_number=attempt
                            )
                        )
                        step.capability_id = step.fallback_capability_id
                        attempt += 1
                        continue
                    elif step.is_critical:
                        step.status = "FAILED"
                        current_status = LifecycleState.FAILED
                        decisions.append(
                            IntelligenceDecision(
                                decision_type=AdaptiveDecisionType.FAIL,
                                reason=f"Critical step {step.step_id} failed: {res.errors}",
                                confidence_score=0.10,
                                confidence_level=ConfidenceLevel.INSUFFICIENT,
                                selected_capability_id=target_cap_id,
                                step_id=step.step_id,
                                attempt_number=attempt
                            )
                        )
                        break
                    else:
                        # Non-critical failure, skip
                        step.status = "SKIPPED"
                        step_completed = True
                        break

                # Success case
                step_output = res.output
                step_outputs.append(step_output)
                step_results[step.step_id] = step_output
                step.status = "COMPLETED"
                step_completed = True

                PlatformEventDispatcher.emit(
                    PlatformEvent(
                        event_type=PlatformEventType.INTELLIGENCE_EVENT if hasattr(PlatformEventType, "INTELLIGENCE_EVENT") else PlatformEventType.SYSTEM_EVENT,
                        correlation_id=correlation_id,
                        workspace_id=context.workspace_id,
                        user_id=context.user_id,
                        source_component="advanced_intelligence_service",
                        payload={"action": "intelligence_step_completed", "step_id": step.step_id, "capability_id": target_cap_id}
                    )
                )

            if current_status in [LifecycleState.WAITING, LifecycleState.FAILED]:
                break

        # 5. Evidence & Confidence Evaluation
        evidence_eval = EvidenceEvaluator.evaluate(
            required_types=analysis.identified_requirements,
            gathered_evidence=all_provenance,
            step_outputs=step_outputs
        )

        decisions.append(
            IntelligenceDecision(
                decision_type=AdaptiveDecisionType.COMPLETE if evidence_eval.is_sufficient else AdaptiveDecisionType.CONTINUE,
                reason=evidence_eval.explanation,
                confidence_score=evidence_eval.confidence_score,
                confidence_level=evidence_eval.confidence_level,
                metadata={"evidence_count": evidence_eval.evidence_count}
            )
        )

        # 6. Synthesize Final Output
        final_answer = "Intelligence execution completed."
        if step_outputs:
            for out in reversed(step_outputs):
                if isinstance(out, dict) and any(k in out for k in ["response", "answer", "result", "summary", "output"]):
                    final_answer = out.get("response") or out.get("answer") or out.get("result") or out.get("summary") or str(out.get("output"))
                    break

        duration_ms = int((time.time() - start_time) * 1000)

        # Provenance for Intelligence Decision Chain
        all_provenance.append(
            ProvenanceItem(
                source_type=ProvenanceSourceType.INTELLIGENCE_DECISION if hasattr(ProvenanceSourceType, "INTELLIGENCE_DECISION") else ProvenanceSourceType.AGENT_REASONING,
                source_id=plan.plan_id,
                title=f"Intelligence Orchestration Plan ({len(plan.steps)} steps)",
                snippet=evidence_eval.explanation,
                trust_level=ProvenanceTrustLevel.TRUSTED_INTERNAL,
                confidence=evidence_eval.confidence_score,
                workspace_id=context.workspace_id,
                metadata={
                    "mode": mode_val,
                    "confidence_level": evidence_eval.confidence_level.value,
                    "total_steps": len(plan.steps)
                }
            )
        )

        PlatformEventDispatcher.emit(
            PlatformEvent(
                event_type=PlatformEventType.INTELLIGENCE_EVENT if hasattr(PlatformEventType, "INTELLIGENCE_EVENT") else PlatformEventType.SYSTEM_EVENT,
                correlation_id=correlation_id,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                source_component="advanced_intelligence_service",
                payload={"action": "intelligence_completed", "duration_ms": duration_ms, "status": current_status.value}
            )
        )

        exec_id = f"exec_intel_{uuid.uuid4().hex[:12]}"
        import datetime
        from app.core.platform.execution_result import PlatformExecutionResult
        from app.services.platform_execution import PlatformExecutionService
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        intel_exec_res = PlatformExecutionResult(
            execution_id=exec_id,
            capability_id="intelligence.orchestrator",
            status=current_status,
            output={"response": final_answer, "step_results": step_results},
            provenance=all_provenance,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            started_at=now_dt,
            completed_at=now_dt,
            metadata={"workspace_id": str(context.workspace_id), "user_id": str(context.user_id), "mode": mode_val}
        )
        PlatformExecutionService._executions[exec_id] = intel_exec_res

        return {
            "execution_id": exec_id,
            "query": query,
            "status": current_status.value,
            "mode": mode_val,
            "plan": plan.dict(),
            "decisions": [d.dict() for d in decisions],
            "evidence_evaluation": evidence_eval.dict(),
            "confidence": evidence_eval.confidence_score,
            "confidence_level": evidence_eval.confidence_level.value,
            "output": {
                "response": final_answer,
                "step_results": step_results,
                "confirmation_info": pending_confirmation_info
            },
            "provenance": [p.dict() for p in all_provenance],
            "duration_ms": duration_ms,
            "correlation_id": correlation_id
        }
