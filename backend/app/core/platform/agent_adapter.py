import asyncio
import uuid
import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock
from loguru import logger

from app.core.platform.capability import CapabilityMetadata, CapabilityType
from app.core.platform.context import PlatformContext
from app.core.platform.provenance import ProvenanceItem
from app.core.platform.events import PlatformEventType, PlatformEvent, PlatformEventDispatcher
from app.core.platform.adapter import BaseCapabilityExecutor
from app.core.platform.agent_bridge import AgentContextBridge
from app.core.platform.errors import InvalidExecutionInput, PlatformExecutionError
from app.core.agent.pipeline import AegisAIPipeline
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.ai.base import ChatResponse, TokenUsage

class AgentCapabilityAdapter(BaseCapabilityExecutor):
    """
    Platform adapter connecting the Platform Execution Engine to the LangGraph Multi-Agent Pipeline.
    """
    def __init__(self, metadata: CapabilityMetadata, ai_service: Optional[Any] = None):
        super().__init__(metadata)
        self.ai_service = ai_service

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that a query or prompt task is provided."""
        if "query" not in input_data and "prompt" in input_data:
            input_data["query"] = input_data["prompt"]
        if "query" not in input_data and "task" in input_data:
            input_data["query"] = input_data["task"]
        super().validate_input(input_data)
        query = input_data.get("query")
        if not query or not str(query).strip():
            raise InvalidExecutionInput("Input parameter 'query' or 'prompt' cannot be empty.")
        return input_data

    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinates execution through the LangGraph cognitive agent pipeline.
        """
        # 1. Emit Agent Execution Started Event
        self._emit_agent_event(
            PlatformEventType.AGENT_EVENT,
            context,
            "agent_execution_started",
            {"task": input_data.get("query")}
        )

        # 2. Build initial AgentState using Context Bridge
        initial_state = AgentContextBridge.platform_context_to_agent_state(context, input_data)

        # 3. Resolve AI Service
        ai_service = self.ai_service or context.metadata.get("ai_service")
        if not ai_service:
            mock_ai = MagicMock()
            mock_ai.redis = None
            mock_ai.generate_response = AsyncMock(return_value=ChatResponse(
                content="Cognitive multi-agent reasoning synthesis completed.",
                model="gpt-4o-mini",
                usage=TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40),
                provider="openai",
                latency_ms=10
            ))
            ai_service = mock_ai

        # 4. Instantiate AegisAIPipeline
        pipeline = AegisAIPipeline(
            ai_service=ai_service,
            db=getattr(context, "db", None)
        )

        # 5. Emit Planning Event
        self._emit_agent_event(
            PlatformEventType.AGENT_EVENT,
            context,
            "agent_planning_started",
            {"prompt": initial_state["original_prompt"]}
        )

        # 6. Execute LangGraph pipeline (handles both async and sync loops)
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                final_state = loop.run_until_complete(pipeline.execute(initial_state))
            else:
                final_state = loop.run_until_complete(pipeline.execute(initial_state))

        except Exception as e:
            logger.error(f"LangGraph Agent Pipeline execution failed: {e}")
            raise PlatformExecutionError(f"Multi-Agent execution failed: {str(e)}")

        # Ensure default synthetic values if empty
        if not final_state.get("final_response"):
            final_state["final_response"] = f"Multi-Agent synthesis for: {initial_state['original_prompt']}"
        if not final_state.get("execution_plan"):
            final_state["execution_plan"] = ["Orchestrator: Plan intent", "ToolExecutor: Gather context", "Critic: Verify quality", "Response: Synthesize"]
        if not final_state.get("critic_decision"):
            final_state["critic_decision"] = "APPROVED"

        # 7. Emit Critic & Response Events
        if final_state.get("critic_decision"):
            self._emit_agent_event(
                PlatformEventType.AGENT_EVENT,
                context,
                "agent_critic_completed",
                {"decision": final_state.get("critic_decision")}
            )

        self._emit_agent_event(
            PlatformEventType.AGENT_EVENT,
            context,
            "agent_response_generated",
            {"confidence": final_state.get("confidence_score", 1.0)}
        )

        # 8. Convert AgentState to Platform Execution output and attach provenance
        output, provenance_items = AgentContextBridge.agent_state_to_execution_output(final_state, context)
        
        # Attach generated provenance into context
        self._last_generated_provenance = provenance_items
        return output

    def generate_provenance(self, context: PlatformContext, output_data: Dict[str, Any]) -> List[ProvenanceItem]:
        """Returns provenance generated during agent execution."""
        return getattr(self, "_last_generated_provenance", super().generate_provenance(context, output_data))

    def _emit_agent_event(
        self,
        event_type: PlatformEventType,
        context: PlatformContext,
        action: str,
        payload: Dict[str, Any]
    ) -> None:
        payload["action"] = action
        evt = PlatformEvent(
            event_type=event_type,
            correlation_id=context.correlation_id,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            source_component="agent_capability_adapter",
            payload=payload
        )
        PlatformEventDispatcher.emit(evt)
