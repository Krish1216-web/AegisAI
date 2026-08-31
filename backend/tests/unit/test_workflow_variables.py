import pytest
import uuid
from app.services.workflow_execution import WorkflowExecutionContext

def test_workflow_variable_and_context_resolution():
    ctx = WorkflowExecutionContext(
        execution_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        workflow_version=1,
        user_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        input_data={
            "customer": {
                "name": "Jane Doe",
                "tier": "enterprise"
            },
            "request_id": 9988
        },
        variables={
            "global_timeout": 60,
            "system_env": "production"
        },
        node_outputs={
            "enrich_node": {
                "transformed": {
                    "score": 98.5,
                    "status": "APPROVED"
                }
            }
        }
    )

    # 1. Single typed resolution
    assert ctx.resolve_expression("{{input.request_id}}") == 9988
    assert ctx.resolve_expression("{{variables.global_timeout}}") == 60
    assert ctx.resolve_expression("{{nodes.enrich_node.transformed.score}}") == 98.5

    # 2. Template string interpolation
    template = "Customer {{input.customer.name}} with tier {{input.customer.tier}} is {{nodes.enrich_node.transformed.status}} in {{variables.system_env}}."
    resolved = ctx.resolve_expression(template)
    assert resolved == "Customer Jane Doe with tier enterprise is APPROVED in production."

    # 3. Non-existent path fails gracefully to empty string
    missing = ctx.resolve_expression("Hello {{input.missing.field}} world")
    assert missing == "Hello  world"
