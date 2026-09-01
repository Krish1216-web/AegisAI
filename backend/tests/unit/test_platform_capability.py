import pytest
import uuid
from app.core.platform.capability import (
    CapabilityType,
    CapabilityMetadata,
    PlatformCapability,
    CapabilityRegistry
)

class DummyCapability(PlatformCapability):
    pass

def test_capability_registration_and_discovery():
    registry = CapabilityRegistry()
    ws_1 = uuid.uuid4()
    ws_2 = uuid.uuid4()

    # System-wide capability
    cap_system = DummyCapability(
        CapabilityMetadata(
            capability_id="sys.cap",
            capability_type=CapabilityType.REASONING,
            name="System Reasoning",
            description="System wide reasoning module"
        )
    )

    # Scoped capability with permission
    cap_scoped = DummyCapability(
        CapabilityMetadata(
            capability_id="scoped.cap",
            capability_type=CapabilityType.MCP,
            name="Scoped MCP",
            description="Workspace 1 private tool",
            workspace_scope=ws_1,
            required_permissions={"mcp:execute"}
        )
    )

    registry.register(cap_system)
    registry.register(cap_scoped)

    # User in Workspace 1 without permission
    res_ws1_no_perm = registry.list_available(ws_1, user_role="viewer", user_permissions=set())
    ids_ws1_no_perm = [c.capability_id for c in res_ws1_no_perm]
    assert "sys.cap" in ids_ws1_no_perm
    assert "scoped.cap" not in ids_ws1_no_perm

    # User in Workspace 1 with permission
    res_ws1_perm = registry.list_available(ws_1, user_role="viewer", user_permissions={"mcp:execute"})
    ids_ws1_perm = [c.capability_id for c in res_ws1_perm]
    assert "sys.cap" in ids_ws1_perm
    assert "scoped.cap" in ids_ws1_perm

    # User in Workspace 2 (Cross-tenant check)
    res_ws2 = registry.list_available(ws_2, user_role="admin")
    ids_ws2 = [c.capability_id for c in res_ws2]
    assert "sys.cap" in ids_ws2
    assert "scoped.cap" not in ids_ws2
