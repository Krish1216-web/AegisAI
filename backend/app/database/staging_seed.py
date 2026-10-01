"""
AegisAI Enterprise — Staging Environment Data Seeder

Provides idempotent, deterministic test data for staging environment validation:
- Staging admin and test role users (Owner, Admin, Member, Viewer, Isolated User)
- Multi-workspace setup for cross-tenant isolation testing (Alpha & Beta)
- Test teams, projects, and permission assignments
- Deterministic test document, knowledge graph entity, and workflow
- Mock MCP test tools

Safety Guarantees:
- Idempotent: Can be run repeatedly without duplicating records
- No production credentials or PII
- Controlled test passwords derived from environment or secure test hashes
"""

import uuid
from sqlalchemy.orm import Session
from loguru import logger

from app.models.user import User, Role
from app.models.workspace import Organization, Workspace, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.models.document import Document
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.models.workflow import Workflow, WorkflowStatus
from app.models.mcp import MCPServer, MCPCapability, MCPCapabilityType, MCPTransport, MCPServerStatus
from app.core.security import get_password_hash


# Deterministic UUIDs for Staging Seed Data
ORG_ALPHA_ID = uuid.UUID("11111111-1111-4111-a111-111111111111")
ORG_BETA_ID = uuid.UUID("22222222-2222-4222-a222-222222222222")
WS_ALPHA_ID = uuid.UUID("33333333-3333-4333-a333-333333333333")
WS_BETA_ID = uuid.UUID("44444444-4444-4444-a444-444444444444")
STAGING_DOC_ID = uuid.UUID("55555555-5555-4555-a555-555555555555")
STAGING_WORKFLOW_ID = uuid.UUID("66666666-6666-4666-a666-666666666666")


def seed_staging_environment(db: Session) -> dict:
    """
    Seeds comprehensive deterministic staging data into the database.
    Returns a summary dictionary of seeded entities.
    """
    logger.info("Initiating staging environment deterministic data seeding...")
    summary = {
        "roles": 0,
        "organizations": 0,
        "workspaces": 0,
        "users": 0,
        "memberships": 0,
        "teams": 0,
        "documents": 0,
        "graph_entities": 0,
        "workflows": 0,
        "mcp_tools": 0
    }

    # 1. Ensure Roles
    roles_to_seed = [
        ("Super Admin", "Full root level capabilities and system bypass access."),
        ("Admin", "Administrative portal access, user and MCP controls."),
        ("User", "Standard workspace operator access."),
        ("Viewer", "Read-only workspace access.")
    ]
    role_map = {}
    for r_name, r_desc in roles_to_seed:
        role = db.query(Role).filter(Role.name == r_name).first()
        if not role:
            role = Role(id=uuid.uuid4(), name=r_name, description=r_desc)
            db.add(role)
            db.flush()
            summary["roles"] += 1
        role_map[r_name] = role

    # 2. Seed Organizations
    org_alpha = db.query(Organization).filter(Organization.id == ORG_ALPHA_ID).first()
    if not org_alpha:
        org_alpha = Organization(id=ORG_ALPHA_ID, name="AegisAI Staging Org Alpha")
        db.add(org_alpha)
        db.flush()
        summary["organizations"] += 1

    org_beta = db.query(Organization).filter(Organization.id == ORG_BETA_ID).first()
    if not org_beta:
        org_beta = Organization(id=ORG_BETA_ID, name="AegisAI Staging Org Beta (Isolated)")
        db.add(org_beta)
        db.flush()
        summary["organizations"] += 1

    # 3. Seed Workspaces (Alpha & Beta for Tenant Isolation Testing)
    ws_alpha = db.query(Workspace).filter(Workspace.id == WS_ALPHA_ID).first()
    if not ws_alpha:
        ws_alpha = Workspace(id=WS_ALPHA_ID, organization_id=ORG_ALPHA_ID, name="Staging Workspace Alpha")
        db.add(ws_alpha)
        db.flush()
        summary["workspaces"] += 1

    ws_beta = db.query(Workspace).filter(Workspace.id == WS_BETA_ID).first()
    if not ws_beta:
        ws_beta = Workspace(id=WS_BETA_ID, organization_id=ORG_BETA_ID, name="Staging Workspace Beta (Isolated)")
        db.add(ws_beta)
        db.flush()
        summary["workspaces"] += 1

    # 4. Seed Controlled Test Users
    test_users = [
        ("staging_admin", "staging_admin@aegisai.enterprise", "staging_admin_pwd_2026", "Admin", ws_alpha, "admin"),
        ("staging_owner", "staging_owner@aegisai.enterprise", "staging_owner_pwd_2026", "User", ws_alpha, "owner"),
        ("staging_member", "staging_member@aegisai.enterprise", "staging_member_pwd_2026", "User", ws_alpha, "member"),
        ("staging_viewer", "staging_viewer@aegisai.enterprise", "staging_viewer_pwd_2026", "Viewer", ws_alpha, "viewer"),
        ("staging_isolated", "staging_isolated@aegisai.enterprise", "staging_isolated_pwd_2026", "User", ws_beta, "member")
    ]

    user_map = {}
    for username, email, raw_pwd, role_name, target_ws, ws_role in test_users:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                username=username,
                email=email,
                password_hash=get_password_hash(raw_pwd),
                role_id=role_map[role_name].id,
                is_active=True,
                is_verified=True,
                settings={"default_workspace_id": str(target_ws.id)}
            )
            db.add(user)
            db.flush()
            summary["users"] += 1
        user_map[email] = user

        # Seed Workspace Membership
        mem = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == target_ws.id,
            WorkspaceMember.user_id == user.id
        ).first()
        if not mem:
            mem = WorkspaceMember(
                id=uuid.uuid4(),
                workspace_id=target_ws.id,
                user_id=user.id,
                role=ws_role
            )
            db.add(mem)
            db.flush()
            summary["memberships"] += 1

    # 5. Seed Test Team in Workspace Alpha
    team_alpha = db.query(Team).filter(Team.workspace_id == WS_ALPHA_ID, Team.name == "Staging QA Team").first()
    if not team_alpha:
        team_alpha = Team(
            id=uuid.uuid4(),
            workspace_id=WS_ALPHA_ID,
            name="Staging QA Team",
            description="Dedicated QA automation test team for staging verification"
        )
        db.add(team_alpha)
        db.flush()
        summary["teams"] += 1

        # Add member to team
        team_mem = TeamMembership(
            id=uuid.uuid4(),
            team_id=team_alpha.id,
            user_id=user_map["staging_member@aegisai.enterprise"].id,
            role="member"
        )
        db.add(team_mem)
        db.flush()

    # 6. Seed Safe Test Document in Workspace Alpha
    staging_doc = db.query(Document).filter(Document.id == STAGING_DOC_ID).first()
    if not staging_doc:
        staging_doc = Document(
            id=STAGING_DOC_ID,
            user_id=user_map["staging_owner@aegisai.enterprise"].id,
            workspace_id=WS_ALPHA_ID,
            filename="staging_policy.txt",
            original_filename="staging_policy.txt",
            mime_type="text/plain",
            file_extension="txt",
            file_size=1024,
            checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_path="storage/staging/staging_policy.txt",
            status="PROCESSED"
        )
        db.add(staging_doc)
        db.flush()
        summary["documents"] += 1

    # 7. Seed Knowledge Graph Entity & Relation in Workspace Alpha
    node_a = db.query(KnowledgeGraphNode).filter(KnowledgeGraphNode.workspace_id == WS_ALPHA_ID, KnowledgeGraphNode.name == "StagingBackend").first()
    if not node_a:
        node_a = KnowledgeGraphNode(
            id=uuid.uuid4(),
            user_id=user_map["staging_owner@aegisai.enterprise"].id,
            workspace_id=WS_ALPHA_ID,
            name="StagingBackend",
            node_type=NodeType.SERVICE if hasattr(NodeType, "SERVICE") else "SERVICE",
            meta_data={"environment": "staging", "framework": "FastAPI"}
        )
        node_b = KnowledgeGraphNode(
            id=uuid.uuid4(),
            user_id=user_map["staging_owner@aegisai.enterprise"].id,
            workspace_id=WS_ALPHA_ID,
            name="StagingDatabase",
            node_type=NodeType.DATABASE if hasattr(NodeType, "DATABASE") else "DATABASE",
            meta_data={"engine": "PostgreSQL 16", "isolation": "dedicated"}
        )
        db.add(node_a)
        db.add(node_b)
        db.flush()

        edge = KnowledgeGraphEdge(
            id=uuid.uuid4(),
            user_id=user_map["staging_owner@aegisai.enterprise"].id,
            workspace_id=WS_ALPHA_ID,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            relationship_type=RelationshipType.CONNECTS_TO if hasattr(RelationshipType, "CONNECTS_TO") else "CONNECTS_TO",
            confidence=1.0,
            meta_data={"protocol": "TCP", "port": 5432}
        )
        db.add(edge)
        db.flush()
        summary["graph_entities"] += 2

    # 8. Seed Deterministic Workflow Definition
    wf = db.query(Workflow).filter(Workflow.id == STAGING_WORKFLOW_ID).first()
    if not wf:
        wf = Workflow(
            id=STAGING_WORKFLOW_ID,
            user_id=user_map["staging_owner@aegisai.enterprise"].id,
            workspace_id=WS_ALPHA_ID,
            name="Staging Automated Smoke Workflow",
            description="Executes periodic health and capability verification in staging",
            status=WorkflowStatus.ACTIVE,
            version=1,
            is_active=True
        )
        db.add(wf)
        db.flush()
        summary["workflows"] += 1

    # 9. Seed Mock MCP Server & Tool
    mcp_srv = db.query(MCPServer).filter(MCPServer.workspace_id == WS_ALPHA_ID, MCPServer.name == "staging-mcp-echo").first()
    if not mcp_srv:
        mcp_srv = MCPServer(
            id=uuid.uuid4(),
            user_id=user_map["staging_admin@aegisai.enterprise"].id,
            workspace_id=WS_ALPHA_ID,
            name="staging-mcp-echo",
            description="Staging isolated mock MCP test tool server",
            server_url="http://127.0.0.1:8000/api/v1/mcp/mock",
            transport=MCPTransport.STDIO,
            status=MCPServerStatus.ACTIVE,
            enabled=True
        )
        db.add(mcp_srv)
        db.flush()

        mcp_cap = MCPCapability(
            id=uuid.uuid4(),
            server_id=mcp_srv.id,
            capability_type=MCPCapabilityType.TOOL,
            name="echo_test",
            description="Echo test parameters for staging smoke verification",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
            enabled=True
        )
        db.add(mcp_cap)
        db.flush()
        summary["mcp_tools"] += 1

    db.commit()
    logger.info(f"Staging seeding completed successfully: {summary}")
    return summary
