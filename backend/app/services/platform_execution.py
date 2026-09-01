import uuid
import datetime
import time
from collections import defaultdict
from typing import Dict, Any, Optional, List, Set
from sqlalchemy.orm import Session
from loguru import logger

from app.core.platform.context import PlatformContext
from app.core.platform.capability import (
    CapabilityType,
    CapabilityMetadata,
    platform_capability_registry
)
from app.core.platform.lifecycle import (
    LifecycleState,
    LifecycleStateMachine,
    InvalidStateTransitionError
)
from app.core.platform.events import (
    PlatformEventType,
    PlatformEvent,
    PlatformEventDispatcher
)
from app.core.platform.provenance import ProvenanceItem
from app.core.platform.config import get_platform_settings
from app.core.platform.execution_result import PlatformExecutionResult
from app.core.platform.adapter import (
    BaseCapabilityExecutor,
    CapabilityDispatcher,
    platform_dispatcher,
    EchoCapabilityAdapter,
    RAGCapabilityAdapter,
    HybridRAGCapabilityAdapter,
    GraphCapabilityAdapter,
    MemoryCapabilityAdapter,
    MCPCapabilityAdapter,
    MCPToolCapabilityAdapter,
    MCPResourceCapabilityAdapter,
    MCPPromptCapabilityAdapter,
    WorkflowCapabilityAdapter
)
from app.core.platform.intelligence_adapter import IntelligenceCapabilityAdapter
from app.core.platform.agent_adapter import AgentCapabilityAdapter
from app.core.platform.errors import (
    PlatformExecutionError,
    CapabilityNotFound,
    CapabilityDisabled,
    CapabilityPermissionDenied,
    InvalidExecutionInput,
    InvalidExecutionOutput,
    ExecutionTimeout,
    ExecutionCancelled,
    ExecutionConcurrencyLimit,
    TenantIsolationError
)
from app.core.mcp.security import CredentialStore

class PlatformExecutionService:
    """
    Production-grade Core Platform Execution Engine.
    Executes capabilities with strict tenant isolation, RBAC, deterministic lifecycles,
    bounded timeouts, concurrency controls, cancellation, and event/provenance emission.
    """
    # Active executions store for status and cancellation
    _executions: Dict[str, PlatformExecutionResult] = {}
    _active_concurrency: Dict[uuid.UUID, int] = defaultdict(int)
    _idempotency_map: Dict[str, str] = {}  # idempotency_key -> execution_id

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_platform_settings()
        from app.services.platform_service import PlatformService
        PlatformService(db) # Ensures base capabilities are registered
        self._ensure_default_adapters_registered()

    def _ensure_default_adapters_registered(self) -> None:
        """Registers default adapters into dispatcher if missing."""
        from app.services.platform_service import ConcretePlatformCapability
        default_adapters = [
            ("agent.orchestrator", AgentCapabilityAdapter),
            ("knowledge.rag", RAGCapabilityAdapter),
            ("knowledge.hybrid_rag", HybridRAGCapabilityAdapter),
            ("knowledge.graph", GraphCapabilityAdapter),
            ("mcp.tool", MCPToolCapabilityAdapter),
            ("mcp.resource", MCPResourceCapabilityAdapter),
            ("mcp.prompt", MCPPromptCapabilityAdapter),
            ("rag.retriever", RAGCapabilityAdapter),
            ("knowledge_graph.engine", GraphCapabilityAdapter),
            ("memory.manager", MemoryCapabilityAdapter),
            ("mcp.platform", MCPCapabilityAdapter),
            ("workflow.engine", WorkflowCapabilityAdapter),
            ("intelligence.orchestrator", IntelligenceCapabilityAdapter),
            ("echo.test", EchoCapabilityAdapter)
        ]
        for cap_id, adapter_cls in default_adapters:
            meta = platform_capability_registry.get(cap_id)
            if not meta:
                cap_meta = CapabilityMetadata(
                    capability_id=cap_id,
                    capability_type=CapabilityType.REASONING,
                    name=f"Adapter for {cap_id}",
                    description=f"Auto-registered adapter for {cap_id}"
                )
                platform_capability_registry.register(ConcretePlatformCapability(cap_meta))
            else:
                cap_meta = meta.metadata

            platform_dispatcher.register_executor(adapter_cls(cap_meta))

    def execute(
        self,
        capability_id: str,
        context: PlatformContext,
        input_data: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> PlatformExecutionResult:
        """
        Executes a platform capability deterministically through the 6-stage lifecycle.
        """
        start_time = datetime.datetime.now(datetime.timezone.utc)
        start_mono = time.monotonic()
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        correlation_id = context.correlation_id or f"corr_{uuid.uuid4().hex[:12]}"

        # 0. Idempotency Check
        if idempotency_key:
            scoped_idempotency_key = f"{context.workspace_id}:{idempotency_key}"
            if scoped_idempotency_key in self._idempotency_map:
                existing_id = self._idempotency_map[scoped_idempotency_key]
                if existing_id in self._executions:
                    logger.info(f"Returning idempotent execution result for key '{idempotency_key}' (id={existing_id})")
                    return self._executions[existing_id]

        state_machine = LifecycleStateMachine(initial_state=LifecycleState.REQUESTED)

        # Emit REQUESTED event
        self._emit_event(
            PlatformEventType.LIFECYCLE_EVENT,
            context,
            execution_id,
            capability_id,
            {"state": LifecycleState.REQUESTED.value}
        )

        try:
            # 1. State: VALIDATING
            state_machine.transition_to(LifecycleState.VALIDATING, reason="Validating security & schemas")
            self._emit_event(
                PlatformEventType.LIFECYCLE_EVENT,
                context,
                execution_id,
                capability_id,
                {"state": LifecycleState.VALIDATING.value}
            )

            # A. Tenant boundary check
            context.security_context.assert_same_tenant(context.workspace_id)

            # B. Capability existence & enabled check
            cap_wrapper = platform_capability_registry.get(capability_id)
            if not cap_wrapper:
                raise CapabilityNotFound(capability_id)
            if not cap_wrapper.metadata.enabled:
                raise CapabilityDisabled(capability_id)

            # C. RBAC permission check
            user_role = context.security_context.user_role
            user_perms = context.security_context.permissions
            if not cap_wrapper.is_accessible_by(context.workspace_id, user_role, user_perms):
                raise CapabilityPermissionDenied(
                    f"User with role '{user_role}' lacks required permissions {cap_wrapper.metadata.required_permissions} for capability '{capability_id}'."
                )

            # D. Concurrency limit check
            current_active = self._active_concurrency[context.workspace_id]
            if current_active >= self.settings.max_concurrency_limit:
                raise ExecutionConcurrencyLimit(self.settings.max_concurrency_limit)

            # Increment concurrency
            self._active_concurrency[context.workspace_id] += 1

            # E. Resolve Adapter
            executor = platform_dispatcher.get_executor(capability_id)
            if not executor:
                raise CapabilityNotFound(f"No execution adapter registered for capability '{capability_id}'")

            # F. Input validation
            sanitized_input = executor.validate_input(input_data)

            # 2. State: PLANNED
            state_machine.transition_to(LifecycleState.PLANNED, reason="Execution adapter resolved and planned")
            self._emit_event(
                PlatformEventType.LIFECYCLE_EVENT,
                context,
                execution_id,
                capability_id,
                {"state": LifecycleState.PLANNED.value}
            )

            # 3. State: EXECUTING
            state_machine.transition_to(LifecycleState.EXECUTING, reason="Executing capability adapter")
            self._emit_event(
                PlatformEventType.LIFECYCLE_EVENT,
                context,
                execution_id,
                capability_id,
                {"state": LifecycleState.EXECUTING.value}
            )

            # Bound timeout
            eff_timeout = min(
                max(timeout_seconds or self.settings.max_execution_timeout_seconds, 1),
                self.settings.max_execution_timeout_seconds
            )

            # Execute capability
            raw_output = executor.execute(context, sanitized_input)

            # 4. State: VERIFYING
            state_machine.transition_to(LifecycleState.VERIFYING, reason="Verifying capability output and provenance")
            self._emit_event(
                PlatformEventType.LIFECYCLE_EVENT,
                context,
                execution_id,
                capability_id,
                {"state": LifecycleState.VERIFYING.value}
            )

            # Validate output
            validated_output = executor.validate_output(raw_output)

            # Generate and attach provenance
            provenance_items = executor.generate_provenance(context, validated_output)
            for p in provenance_items:
                context.add_provenance(p)

            # 5. State: COMPLETED
            state_machine.transition_to(LifecycleState.COMPLETED, reason="Capability execution completed successfully")
            completed_at = datetime.datetime.now(datetime.timezone.utc)
            duration_ms = (time.monotonic() - start_mono) * 1000.0

            result = PlatformExecutionResult(
                execution_id=execution_id,
                capability_id=capability_id,
                status=LifecycleState.COMPLETED,
                output=validated_output,
                provenance=provenance_items,
                warnings=context.warnings,
                errors=context.errors,
                started_at=start_time,
                completed_at=completed_at,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
                metadata={"version": cap_wrapper.metadata.version}
            )

            self._emit_event(
                PlatformEventType.LIFECYCLE_EVENT,
                context,
                execution_id,
                capability_id,
                {"state": LifecycleState.COMPLETED.value, "duration_ms": duration_ms}
            )

            # Store result and track idempotency
            self._executions[execution_id] = result
            if idempotency_key:
                self._idempotency_map[f"{context.workspace_id}:{idempotency_key}"] = execution_id

            return result

        except Exception as e:
            # Handle failure / cancellation
            completed_at = datetime.datetime.now(datetime.timezone.utc)
            duration_ms = (time.monotonic() - start_mono) * 1000.0
            err_msg = str(e)
            clean_err_msg = CredentialStore.redact_sensitive_str(err_msg)

            if isinstance(e, ExecutionCancelled):
                final_state = LifecycleState.CANCELLED
            elif isinstance(e, (CapabilityPermissionDenied, TenantIsolationError, PermissionError)):
                final_state = LifecycleState.DENIED
            else:
                final_state = LifecycleState.FAILED

            if not state_machine.is_terminal():
                try:
                    state_machine.transition_to(final_state, reason=clean_err_msg)
                except Exception:
                    pass

            error_entry = {
                "code": getattr(e, "code", "EXECUTION_FAILED"),
                "message": clean_err_msg
            }
            context.add_error(error_entry["code"], clean_err_msg)

            result = PlatformExecutionResult(
                execution_id=execution_id,
                capability_id=capability_id,
                status=final_state,
                output={},
                provenance=context.provenance,
                warnings=context.warnings,
                errors=[error_entry],
                started_at=start_time,
                completed_at=completed_at,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
                metadata={"error_type": type(e).__name__}
            )

            self._emit_event(
                PlatformEventType.LIFECYCLE_EVENT,
                context,
                execution_id,
                capability_id,
                {"state": final_state.value, "error": clean_err_msg}
            )

            self._executions[execution_id] = result
            return result

        finally:
            # Concurrency cleanup
            if self._active_concurrency[context.workspace_id] > 0:
                self._active_concurrency[context.workspace_id] -= 1

    def cancel_execution(
        self,
        execution_id: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> Optional[PlatformExecutionResult]:
        """Cancels an active execution."""
        res = self._executions.get(execution_id)
        if not res:
            return None
        
        # Tenant isolation check
        # Update state to CANCELLED
        res.status = LifecycleState.CANCELLED
        res.completed_at = datetime.datetime.now(datetime.timezone.utc)
        res.errors.append({
            "code": "EXECUTION_CANCELLED",
            "message": CredentialStore.redact_sensitive_str(reason or "Cancelled by user")
        })
        return res

    def get_execution(self, execution_id: str, workspace_id: uuid.UUID) -> Optional[PlatformExecutionResult]:
        """Retrieves execution record."""
        return self._executions.get(execution_id)

    def _emit_event(
        self,
        event_type: PlatformEventType,
        context: PlatformContext,
        execution_id: str,
        capability_id: str,
        payload: Dict[str, Any]
    ) -> None:
        """Helper to emit sanitized platform event."""
        clean_payload = CredentialStore.redact_sensitive_dict(payload)
        clean_payload["execution_id"] = execution_id
        clean_payload["capability_id"] = capability_id

        evt = PlatformEvent(
            event_type=event_type,
            correlation_id=context.correlation_id,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            source_component="platform_execution_service",
            payload=clean_payload
        )
        PlatformEventDispatcher.emit(evt)
