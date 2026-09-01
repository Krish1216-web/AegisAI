import pytest
import uuid
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.config import get_platform_settings

def test_security_context_tenant_boundary_assertion():
    ws_1 = uuid.uuid4()
    ws_2 = uuid.uuid4()
    user_id = uuid.uuid4()

    sec = SecurityContext(
        user_id=user_id,
        workspace_id=ws_1,
        user_role="editor",
        permissions={"agent:invoke"}
    )

    # Same tenant assertion succeeds
    sec.assert_same_tenant(ws_1)

    # Cross tenant assertion raises PermissionError
    with pytest.raises(PermissionError):
        sec.assert_same_tenant(ws_2)

    # Permission check
    assert sec.has_permission("agent:invoke")
    assert not sec.has_permission("admin:manage")

def test_platform_settings_bounded_defaults():
    settings = get_platform_settings()
    assert settings.max_execution_timeout_seconds >= 10
    assert settings.max_execution_timeout_seconds <= 3600
    assert settings.max_context_tokens >= 1000
    assert settings.max_concurrency_limit <= 50
    assert settings.feature_flags.get("strict_tenant_isolation") is True
