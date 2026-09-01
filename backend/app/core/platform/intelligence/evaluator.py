from typing import Dict, Any, List, Set, Optional
from app.core.platform.provenance import ProvenanceItem, ProvenanceSourceType, ProvenanceTrustLevel
from app.core.platform.intelligence.models import (
    RequirementType,
    ConfidenceLevel,
    ContradictionItem,
    EvidenceEvaluationResult
)

class ConfidenceEngine:
    """
    Calibrated deterministic confidence calculation for Phase 8.7.
    Produces scores in [0.0, 1.0] and categorizes confidence level.
    """

    @classmethod
    def calculate_confidence(
        cls,
        evidence_items: List[ProvenanceItem],
        contradiction_count: int = 0,
        missing_critical_requirements: int = 0
    ) -> (float, ConfidenceLevel):
        if not evidence_items and missing_critical_requirements > 0:
            return 0.20, ConfidenceLevel.INSUFFICIENT

        # Base confidence calculation based on count and source diversity
        count = len(evidence_items)
        unique_sources = len(set(item.source_type for item in evidence_items))
        
        # Average item confidence (default to 0.85 if missing)
        avg_item_conf = (
            sum(getattr(item, "confidence", 0.85) for item in evidence_items) / count
            if count > 0 else 0.50
        )

        base_score = 0.50 + min(count * 0.08, 0.25) + min(unique_sources * 0.08, 0.15)
        combined = (base_score * 0.4) + (avg_item_conf * 0.6)

        # Penalties
        penalty = (contradiction_count * 0.25) + (missing_critical_requirements * 0.30)
        final_score = max(0.05, min(1.0, combined - penalty))
        final_score = round(final_score, 3)

        if final_score >= 0.80:
            level = ConfidenceLevel.HIGH
        elif final_score >= 0.60:
            level = ConfidenceLevel.MEDIUM
        elif final_score >= 0.40:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.INSUFFICIENT

        return final_score, level

class ContradictionDetector:
    """
    Deterministic contradiction detector for normalized entity states and structured facts.
    """

    @classmethod
    def detect_contradictions(
        cls,
        step_outputs: List[Dict[str, Any]],
        evidence_items: List[ProvenanceItem]
    ) -> List[ContradictionItem]:
        contradictions: List[ContradictionItem] = []
        observed_states: Dict[str, Dict[str, str]] = {}  # entity -> {attribute: value}

        # Check structured outputs for conflicting attributes (e.g. status)
        for out in step_outputs:
            if not isinstance(out, dict):
                continue
            
            # 1. Graph / Entity structured contradictions
            nodes = out.get("nodes") or out.get("entities") or []
            if isinstance(nodes, list):
                for node in nodes:
                    if isinstance(node, dict) and "name" in node and "status" in node:
                        entity_name = str(node["name"]).lower()
                        status_val = str(node["status"]).lower()
                        
                        if entity_name in observed_states:
                            prev_status = observed_states[entity_name].get("status")
                            if prev_status and prev_status != status_val:
                                contradictions.append(ContradictionItem(
                                    fact_a=f"{entity_name}.status = {prev_status}",
                                    source_a="previous_step_result",
                                    fact_b=f"{entity_name}.status = {status_val}",
                                    source_b="current_step_result",
                                    description=f"Conflicting status detected for entity '{entity_name}': '{prev_status}' vs '{status_val}'"
                                ))
                        else:
                            observed_states[entity_name] = {"status": status_val}

        return contradictions

class EvidenceEvaluator:
    """
    Evaluates evidence sufficiency across planned requirements and gathered citations.
    """

    @classmethod
    def evaluate(
        cls,
        required_types: List[RequirementType],
        gathered_evidence: List[ProvenanceItem],
        step_outputs: List[Dict[str, Any]] = None
    ) -> EvidenceEvaluationResult:
        step_outputs = step_outputs or []
        
        # 1. Map gathered evidence to source types
        seen_sources: Set[str] = set(item.source_type.value for item in gathered_evidence)

        # 2. Check for missing required types
        missing: List[RequirementType] = []
        for req in required_types:
            if req == RequirementType.DOCUMENT_EVIDENCE:
                if not (ProvenanceSourceType.DOCUMENT_CHUNK.value in seen_sources or ProvenanceSourceType.DOCUMENT.value in seen_sources):
                    missing.append(req)
            elif req == RequirementType.GRAPH_REASONING:
                if not (ProvenanceSourceType.GRAPH_NODE.value in seen_sources or ProvenanceSourceType.GRAPH_EDGE.value in seen_sources):
                    missing.append(req)
            elif req == RequirementType.MCP_TOOL:
                if not (ProvenanceSourceType.MCP_TOOL.value in seen_sources):
                    missing.append(req)

        # 3. Detect contradictions
        contradictions = ContradictionDetector.detect_contradictions(step_outputs, gathered_evidence)

        # 4. Calculate calibrated confidence
        score, level = ConfidenceEngine.calculate_confidence(
            evidence_items=gathered_evidence,
            contradiction_count=len(contradictions),
            missing_critical_requirements=len(missing)
        )

        is_sufficient = (len(missing) == 0 and len(contradictions) == 0 and score >= 0.60) or (len(gathered_evidence) > 0 and len(missing) == 0)

        explanation = (
            f"Evidence evaluation: {len(gathered_evidence)} items, "
            f"confidence: {score} ({level.value}), "
            f"missing: {[m.value for m in missing]}, "
            f"contradictions: {len(contradictions)}"
        )

        return EvidenceEvaluationResult(
            is_sufficient=is_sufficient,
            confidence_score=score,
            confidence_level=level,
            evidence_count=len(gathered_evidence),
            source_types=list(seen_sources),
            contradictions=contradictions,
            missing_requirements=missing,
            explanation=explanation
        )
