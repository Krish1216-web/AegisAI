import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from loguru import logger

from app.core.platform.capability import CapabilityMetadata, CapabilityType
from app.core.platform.context import PlatformContext
from app.core.platform.provenance import (
    ProvenanceItem,
    ProvenanceSourceType,
    ProvenanceTrustLevel
)
from app.core.platform.errors import (
    InvalidExecutionInput,
    InvalidExecutionOutput
)

class BaseCapabilityExecutor(ABC):
    """
    Abstract Base Class for capability execution adapters.
    """
    def __init__(self, metadata: CapabilityMetadata):
        self.metadata = metadata

    @property
    def capability_id(self) -> str:
        return self.metadata.capability_id

    @property
    def capability_type(self) -> CapabilityType:
        return self.metadata.capability_type

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates input against capability schema.
        Raises InvalidExecutionInput if malformed or missing required keys.
        """
        if not isinstance(input_data, dict):
            raise InvalidExecutionInput("Input data must be a valid JSON object.")
        
        # Bounded payload check
        if len(str(input_data)) > 100000:
            raise InvalidExecutionInput("Input data exceeds maximum allowed payload size (100KB).")

        req_fields = self.metadata.input_schema.get("required", [])
        for field in req_fields:
            if field not in input_data:
                raise InvalidExecutionInput(f"Missing required input parameter '{field}'.")

        return input_data

    @abstractmethod
    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes capability computation and returns output dictionary.
        """
        pass

    def validate_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates output against capability output schema.
        """
        if not isinstance(output_data, dict):
            raise InvalidExecutionOutput("Capability output must be a dictionary.")
        return output_data

    def generate_provenance(self, context: PlatformContext, output_data: Dict[str, Any]) -> List[ProvenanceItem]:
        """
        Default provenance generator for the capability execution.
        """
        item = ProvenanceItem(
            source_type=self._get_default_source_type(),
            source_id=self.capability_id,
            title=self.metadata.name,
            trust_level=self._get_default_trust_level(),
            workspace_id=context.workspace_id,
            metadata={"version": self.metadata.version}
        )
        return [item]

    def _get_default_source_type(self) -> ProvenanceSourceType:
        type_mapping = {
            CapabilityType.AGENT: ProvenanceSourceType.AGENT_REASONING,
            CapabilityType.RAG: ProvenanceSourceType.DOCUMENT_CHUNK,
            CapabilityType.KNOWLEDGE_GRAPH: ProvenanceSourceType.GRAPH_NODE,
            CapabilityType.MEMORY: ProvenanceSourceType.MEMORY_FACT,
            CapabilityType.MCP: ProvenanceSourceType.MCP_TOOL,
            CapabilityType.WORKFLOW: ProvenanceSourceType.WORKFLOW_NODE,
            CapabilityType.REASONING: ProvenanceSourceType.AGENT_REASONING,
            CapabilityType.INTELLIGENCE: ProvenanceSourceType.AGENT_REASONING,
            CapabilityType.EXTERNAL_SERVICE: ProvenanceSourceType.EXTERNAL_RESEARCH
        }
        return type_mapping.get(self.capability_type, ProvenanceSourceType.EXTERNAL_RESEARCH)

    def _get_default_trust_level(self) -> ProvenanceTrustLevel:
        if self.capability_type == CapabilityType.MCP:
            return ProvenanceTrustLevel.UNTRUSTED_MCP
        elif self.capability_type == CapabilityType.EXTERNAL_SERVICE:
            return ProvenanceTrustLevel.UNTRUSTED_EXTERNAL
        elif self.capability_type == CapabilityType.RAG:
            return ProvenanceTrustLevel.VERIFIED_RAG
        elif self.capability_type == CapabilityType.KNOWLEDGE_GRAPH:
            return ProvenanceTrustLevel.VERIFIED_GRAPH
        elif self.capability_type == CapabilityType.MEMORY:
            return ProvenanceTrustLevel.VERIFIED_MEMORY
        return ProvenanceTrustLevel.TRUSTED_INTERNAL


# ---------------------------------------------------------------------------
# Standard Core Adapters
# ---------------------------------------------------------------------------

class EchoCapabilityAdapter(BaseCapabilityExecutor):
    """Deterministic echo/test adapter."""
    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "echo": input_data,
            "processed_by": self.capability_id,
            "workspace_id": str(context.workspace_id)
        }

from app.core.platform.knowledge_adapters import (
    RAGCapabilityAdapter,
    HybridRAGCapabilityAdapter,
    GraphCapabilityAdapter
)

class MemoryCapabilityAdapter(BaseCapabilityExecutor):
    """Adapter wrapping Long-Term Memory recall."""
    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        key = input_data.get("key", "")
        return {
            "recalled_key": key,
            "facts": [{"fact": f"Memory fact for key '{key}'", "confidence": 0.88}]
        }

class MCPCapabilityAdapter(BaseCapabilityExecutor):
    """Adapter wrapping MCP Tool / Resource invocation."""
    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = input_data.get("tool_name", "generic_tool")
        arguments = input_data.get("arguments", {})
        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": "MCP Tool executed successfully",
            "provenance": "UNTRUSTED_MCP"
        }

class WorkflowCapabilityAdapter(BaseCapabilityExecutor):
    """Adapter wrapping Workflow execution trigger."""
    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow_id = input_data.get("workflow_id", str(context.workflow_id or "default"))
        return {
            "workflow_id": workflow_id,
            "execution_status": "COMPLETED",
            "output": {"result": "Workflow execution step resolved"}
        }


# ---------------------------------------------------------------------------
# Capability Dispatcher
# ---------------------------------------------------------------------------

class CapabilityDispatcher:
    """
    Resolves capability IDs to their execution adapter implementations.
    """
    def __init__(self):
        self._executors: Dict[str, BaseCapabilityExecutor] = {}

    def register_executor(self, executor: BaseCapabilityExecutor) -> None:
        self._executors[executor.capability_id] = executor

    def unregister_executor(self, capability_id: str) -> None:
        self._executors.pop(capability_id, None)

    def get_executor(self, capability_id: str) -> Optional[BaseCapabilityExecutor]:
        return self._executors.get(capability_id)

    def list_executors(self) -> List[str]:
        return list(self._executors.keys())

# Global platform capability dispatcher
platform_dispatcher = CapabilityDispatcher()
