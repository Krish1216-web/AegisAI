import pytest
import uuid
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.provenance import ProvenanceItem, ProvenanceSourceType, ProvenanceTrustLevel

def test_platform_context_creation_and_safe_dict():
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    sec_ctx = SecurityContext(
        user_id=user_id,
        workspace_id=ws_id,
        user_role="admin",
        trust_level=TrustLevel.HIGH
    )

    ctx = PlatformContext(
        user_id=user_id,
        workspace_id=ws_id,
        security_context=sec_ctx,
        input_data={
            "query": "Hello world",
            "api_key": "sk-secret-key-12345",
            "password": "SuperSecretPassword!"
        }
    )

    ctx.set_result("stage_1", {"data": "step 1 output"})
    ctx.add_error("ERR_TEST", "Connection failed with token=secret_token_abc")
    ctx.add_warning("High latency detected with password=12345")

    # Verify safe dict redacts sensitive values
    safe = ctx.get_safe_dict()
    assert safe["user_id"] == str(user_id)
    assert safe["workspace_id"] == str(ws_id)
    assert safe["input_data"]["query"] == "Hello world"
    assert safe["input_data"]["api_key"] == "[REDACTED]"
    assert safe["input_data"]["password"] == "[REDACTED]"
    assert "secret_token_abc" not in safe["errors"][0]["message"]
    assert "12345" not in safe["warnings"][0]

def test_platform_context_tenant_isolation_on_provenance():
    user_id = uuid.uuid4()
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()

    sec_ctx = SecurityContext(
        user_id=user_id,
        workspace_id=ws_a,
        user_role="editor"
    )

    ctx = PlatformContext(
        user_id=user_id,
        workspace_id=ws_a,
        security_context=sec_ctx
    )

    # Valid tenant provenance
    p_valid = ProvenanceItem(
        source_type=ProvenanceSourceType.DOCUMENT,
        source_id="doc_123",
        workspace_id=ws_a
    )
    ctx.add_provenance(p_valid)
    assert len(ctx.provenance) == 1

    # Cross-tenant provenance attempt
    p_invalid = ProvenanceItem(
        source_type=ProvenanceSourceType.DOCUMENT,
        source_id="doc_cross",
        workspace_id=ws_b
    )
    with pytest.raises(PermissionError):
        ctx.add_provenance(p_invalid)
