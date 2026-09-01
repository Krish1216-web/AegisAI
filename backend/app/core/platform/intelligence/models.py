import uuid
import datetime
import enum
from typing import Dict, Any, Optional, List, Set
from pydantic import BaseModel, Field

class RequirementType(str, enum.Enum):
    DOCUMENT_EVIDENCE = "document_evidence"
    GRAPH_REASONING = "graph_reasoning"
    MCP_TOOL = "mcp_tool"
    MCP_RESOURCE = "mcp_resource"
    AGENT_REASONING = "agent_reasoning"
    WORKFLOW_EXECUTION = "workflow_execution"
    MEMORY_CONTEXT = "memory_context"

class ExecutionMode(str, enum.Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"

class AdaptiveDecisionType(str, enum.Enum):
    COMPLETE = "complete"
    CONTINUE = "continue"
    RETRY = "retry"
    FALLBACK = "fallback"
    RETRIEVE_MORE = "retrieve_more"
    DENY = "deny"
    FAIL = "fail"
    WAITING = "waiting"

class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"

class RequirementAnalysisResult(BaseModel):
    query: str
    identified_requirements: List[RequirementType]
    extracted_entities: List[str] = Field(default_factory=list)
    intent_description: str = ""
    is_complex_synthesis: bool = False
    requires_external_tool: bool = False

class CapabilityScore(BaseModel):
    capability_id: str
    capability_type: str
    score: float
    is_eligible: bool = True
    reasons: List[str] = Field(default_factory=list)

class PlanStep(BaseModel):
    step_id: str
    capability_id: str
    requirement_type: RequirementType
    description: str
    input_template: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)  # step_ids that must complete first
    fallback_capability_id: Optional[str] = None
    timeout_seconds: int = 60
    is_critical: bool = True
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, WAITING

class IntelligencePlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    mode: ExecutionMode = ExecutionMode.ADAPTIVE
    steps: List[PlanStep] = Field(default_factory=list)
    max_depth: int = 1
    total_steps: int = 0
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class ContradictionItem(BaseModel):
    fact_a: str
    source_a: str
    fact_b: str
    source_b: str
    description: str

class EvidenceEvaluationResult(BaseModel):
    is_sufficient: bool = True
    confidence_score: float = 1.0  # 0.0 to 1.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.HIGH
    evidence_count: int = 0
    source_types: List[str] = Field(default_factory=list)
    contradictions: List[ContradictionItem] = Field(default_factory=list)
    missing_requirements: List[RequirementType] = Field(default_factory=list)
    explanation: str = ""

class IntelligenceDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:10]}")
    decision_type: AdaptiveDecisionType
    reason: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    selected_capability_id: Optional[str] = None
    step_id: Optional[str] = None
    attempt_number: int = 1
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
