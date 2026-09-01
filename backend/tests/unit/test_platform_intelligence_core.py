import pytest
import uuid
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.provenance import ProvenanceItem, ProvenanceSourceType, ProvenanceTrustLevel
from app.core.platform.intelligence.models import (
    RequirementType,
    ExecutionMode,
    ConfidenceLevel,
    AdaptiveDecisionType,
    PlanStep
)
from app.core.platform.intelligence.requirement_analyzer import RequirementAnalyzer
from app.core.platform.intelligence.capability_selector import CapabilitySelector
from app.core.platform.intelligence.planner import IntelligencePlanner, IntelligencePlannerError
from app.core.platform.intelligence.evaluator import ConfidenceEngine, ContradictionDetector, EvidenceEvaluator

@pytest.fixture
def test_context():
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    sec_ctx = SecurityContext(user_id=user_id, workspace_id=ws_id, user_role="admin")
    return PlatformContext(user_id=user_id, workspace_id=ws_id, security_context=sec_ctx)

def test_requirement_analysis_detection():
    # 1. Document / RAG
    res1 = RequirementAnalyzer.analyze("Retrieve Q3 revenue strategy documents")
    assert RequirementType.DOCUMENT_EVIDENCE in res1.identified_requirements

    # 2. Graph Reasoning
    res2 = RequirementAnalyzer.analyze("Find connected entities and relationships for Project Alpha")
    assert RequirementType.GRAPH_REASONING in res2.identified_requirements

    # 3. MCP Tool
    res3 = RequirementAnalyzer.analyze("Execute database calculator tool via MCP")
    assert RequirementType.MCP_TOOL in res3.identified_requirements

    # 4. Multi-Agent Synthesis
    res4 = RequirementAnalyzer.analyze("Synthesize an extensive architecture evaluation plan")
    assert RequirementType.AGENT_REASONING in res4.identified_requirements

def test_capability_scoring_and_selection(test_context):
    analysis = RequirementAnalyzer.analyze("Find remote work policy document and resolve related entities")
    scores = CapabilitySelector.score_capabilities(test_context, analysis)

    assert len(scores) > 0
    # Top scored capability should be RAG or Graph
    top_cap = scores[0]
    assert top_cap.is_eligible is True
    assert top_cap.score > 0

    # Best selection for document evidence
    selected_rag = CapabilitySelector.select_best_for_requirement(test_context, RequirementType.DOCUMENT_EVIDENCE)
    assert selected_rag in ["knowledge.rag", "rag.retriever"]

def test_dag_planning_modes(test_context):
    analysis = RequirementAnalyzer.analyze("Search policy docs, expand graph nodes, and synthesize response")
    
    # 1. Sequential Plan
    plan_seq = IntelligencePlanner.create_plan(test_context, analysis, mode=ExecutionMode.SEQUENTIAL)
    assert len(plan_seq.steps) >= 2
    assert plan_seq.mode == ExecutionMode.SEQUENTIAL
    # Step 2 must depend on Step 1
    if len(plan_seq.steps) > 1:
        assert plan_seq.steps[1].dependencies == [plan_seq.steps[0].step_id]

    # 2. Parallel Plan
    plan_par = IntelligencePlanner.create_plan(test_context, analysis, mode=ExecutionMode.PARALLEL)
    assert plan_par.mode == ExecutionMode.PARALLEL
    # RAG and Graph can run with 0 dependencies in parallel
    for step in plan_par.steps:
        if step.requirement_type in [RequirementType.DOCUMENT_EVIDENCE, RequirementType.GRAPH_REASONING]:
            assert len(step.dependencies) == 0

    # 3. Adaptive Plan
    plan_adp = IntelligencePlanner.create_plan(test_context, analysis, mode=ExecutionMode.ADAPTIVE)
    assert plan_adp.mode == ExecutionMode.ADAPTIVE
    assert plan_adp.max_depth <= 6

def test_planner_cycle_and_limit_enforcement(test_context):
    # Self-loop cycle rejection
    cyclic_steps = [
        PlanStep(
            step_id="step_1",
            capability_id="knowledge.rag",
            requirement_type=RequirementType.DOCUMENT_EVIDENCE,
            description="Cycle test",
            dependencies=["step_1"]
        )
    ]
    with pytest.raises(IntelligencePlannerError, match="Self-loop"):
        IntelligencePlanner._validate_acyclic(cyclic_steps)

    # Mutual cycle rejection
    mutual_cycle = [
        PlanStep(
            step_id="step_1",
            capability_id="knowledge.rag",
            requirement_type=RequirementType.DOCUMENT_EVIDENCE,
            description="Step 1",
            dependencies=["step_2"]
        ),
        PlanStep(
            step_id="step_2",
            capability_id="knowledge.graph",
            requirement_type=RequirementType.GRAPH_REASONING,
            description="Step 2",
            dependencies=["step_1"]
        )
    ]
    with pytest.raises(IntelligencePlannerError, match="Cyclic dependency"):
        IntelligencePlanner._validate_acyclic(mutual_cycle)

def test_confidence_engine_and_evaluator(test_context):
    ws = test_context.workspace_id

    # 1. High Confidence Evidence
    items = [
        ProvenanceItem(
            source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
            source_id="chunk_1",
            title="Q3 Policy",
            snippet="Policy details",
            confidence=0.92,
            workspace_id=ws
        ),
        ProvenanceItem(
            source_type=ProvenanceSourceType.GRAPH_NODE,
            source_id="node_1",
            title="Entity Alpha",
            confidence=0.88,
            workspace_id=ws
        )
    ]

    score, level = ConfidenceEngine.calculate_confidence(items)
    assert score >= 0.70
    assert level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    # 2. Evidence Evaluator with all requirements satisfied
    eval_res = EvidenceEvaluator.evaluate(
        required_types=[RequirementType.DOCUMENT_EVIDENCE, RequirementType.GRAPH_REASONING],
        gathered_evidence=items
    )
    assert eval_res.is_sufficient is True
    assert len(eval_res.missing_requirements) == 0

def test_contradiction_detection(test_context):
    step_outputs = [
        {"nodes": [{"name": "Project Apollo", "status": "active"}]},
        {"nodes": [{"name": "Project Apollo", "status": "archived"}]}
    ]

    contradictions = ContradictionDetector.detect_contradictions(step_outputs, [])
    assert len(contradictions) == 1
    assert "active" in contradictions[0].description
    assert "archived" in contradictions[0].description
