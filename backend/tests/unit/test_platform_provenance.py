import pytest
import uuid
from app.core.platform.provenance import (
    ProvenanceSourceType,
    ProvenanceTrustLevel,
    ProvenanceItem,
    ProvenanceTracker
)

def test_provenance_tracker_deduplication_and_untrusted_flag():
    ws_id = uuid.uuid4()
    tracker = ProvenanceTracker(workspace_id=ws_id)

    # 1. Add RAG verified citation
    p1 = ProvenanceItem(
        source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
        source_id="chunk_1",
        title="Annual Report",
        trust_level=ProvenanceTrustLevel.VERIFIED_RAG,
        workspace_id=ws_id
    )
    tracker.add(p1)

    # Duplicate add attempt should be ignored
    p1_dup = ProvenanceItem(
        source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
        source_id="chunk_1",
        title="Annual Report (Duplicate)",
        trust_level=ProvenanceTrustLevel.VERIFIED_RAG,
        workspace_id=ws_id
    )
    tracker.add(p1_dup)

    assert len(tracker.get_items()) == 1
    assert not tracker.has_untrusted_content()

    # 2. Add Untrusted MCP tool result
    p2 = ProvenanceItem(
        source_type=ProvenanceSourceType.MCP_TOOL,
        source_id="tool_weather",
        title="Weather API result",
        trust_level=ProvenanceTrustLevel.UNTRUSTED_MCP,
        workspace_id=ws_id
    )
    tracker.add(p2)

    assert len(tracker.get_items()) == 2
    assert tracker.has_untrusted_content()

def test_provenance_tracker_cross_tenant_rejection():
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()

    tracker = ProvenanceTracker(workspace_id=ws_a)

    p_foreign = ProvenanceItem(
        source_type=ProvenanceSourceType.DOCUMENT,
        source_id="doc_foreign",
        workspace_id=ws_b
    )

    with pytest.raises(PermissionError):
        tracker.add(p_foreign)
