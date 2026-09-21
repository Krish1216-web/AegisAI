import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Organization, Workspace, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.models.project import Project, ProjectMembership, ProjectResource
from app.services.authorization import AuthorizationService
from app.core.collaboration.access import CollaborationResourceAccessService
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.auth.permissions import Permissions, ALL_PERMISSIONS, WORKSPACE_ROLE_PERMISSIONS


@pytest.fixture
def authz_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    # System Roles
    user_system_role = Role(id=uuid.uuid4(), name="User", description="Standard user")
    admin_system_role = Role(id=uuid.uuid4(), name="Admin", description="System admin")
    session.add_all([user_system_role, admin_system_role])
    session.flush()

    # Organizations
    org = Organization(id=uuid.uuid4(), name="Primary Org")
    session.add(org)
    session.flush()

    # Workspaces A and B
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Alpha")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Beta")
    session.add_all([ws_a, ws_b])
    session.flush()

    # Users
    user_owner_a = User(id=uuid.uuid4(), email="owner_a@aegis.ai", username="owner_a", password_hash="hash", role_id=user_system_role.id, is_active=True)
    user_admin_a = User(id=uuid.uuid4(), email="admin_a@aegis.ai", username="admin_a", password_hash="hash", role_id=user_system_role.id, is_active=True)
    user_member_a = User(id=uuid.uuid4(), email="member_a@aegis.ai", username="member_a", password_hash="hash", role_id=user_system_role.id, is_active=True)
    user_viewer_a = User(id=uuid.uuid4(), email="viewer_a@aegis.ai", username="viewer_a", password_hash="hash", role_id=user_system_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="user_b@aegis.ai", username="user_b", password_hash="hash", role_id=user_system_role.id, is_active=True)
    sys_admin = User(id=uuid.uuid4(), email="sysadmin@aegis.ai", username="sysadmin", password_hash="hash", role_id=admin_system_role.id, is_active=True)
    inactive_user = User(id=uuid.uuid4(), email="inactive@aegis.ai", username="inactive", password_hash="hash", role_id=user_system_role.id, is_active=False)

    session.add_all([user_owner_a, user_admin_a, user_member_a, user_viewer_a, user_b, sys_admin, inactive_user])
    session.flush()

    user_owner_a.role = user_system_role
    user_admin_a.role = user_system_role
    user_member_a.role = user_system_role
    user_viewer_a.role = user_system_role
    user_b.role = user_system_role
    sys_admin.role = admin_system_role
    inactive_user.role = user_system_role

    # Memberships in Workspace A
    m_owner = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_owner_a.id, role="owner")
    m_admin = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_admin_a.id, role="admin")
    m_member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_member_a.id, role="member")
    m_viewer = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_viewer_a.id, role="viewer")
    
    # Membership in Workspace B
    m_b = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner")
    
    session.add_all([m_owner, m_admin, m_member, m_viewer, m_b])
    session.flush()

    # Team in Workspace A
    team_a = Team(id=uuid.uuid4(), workspace_id=ws_a.id, name="Eng Team", status="active")
    session.add(team_a)
    session.flush()

    tm_owner = TeamMembership(id=uuid.uuid4(), team_id=team_a.id, user_id=user_member_a.id, role="owner", status="active")
    session.add(tm_owner)

    # Project in Workspace A
    proj_a = Project(id=uuid.uuid4(), workspace_id=ws_a.id, name="Project Alpha", status="active")
    session.add(proj_a)
    session.flush()

    pm_editor = ProjectMembership(id=uuid.uuid4(), project_id=proj_a.id, user_id=user_viewer_a.id, role="editor", status="active")
    p_resource = ProjectResource(id=uuid.uuid4(), workspace_id=ws_a.id, project_id=proj_a.id, resource_type="document", resource_id="doc-12345")
    session.add_all([pm_editor, p_resource])
    session.commit()

    authz = AuthorizationService(session)
    collab = CollaborationResourceAccessService(session)

    yield {
        "session": session,
        "authz": authz,
        "collab": collab,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "owner_a": user_owner_a,
        "admin_a": user_admin_a,
        "member_a": user_member_a,
        "viewer_a": user_viewer_a,
        "user_b": user_b,
        "sys_admin": sys_admin,
        "inactive_user": inactive_user,
        "team_a": team_a,
        "proj_a": proj_a,
    }
    session.close()


def test_tenant_isolation_cross_workspace_resource_denial(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]

    # User B is in Workspace B, attempts to access Workspace A
    assert authz.authorize(ctx["user_b"].id, ctx["ws_a"].id, Permissions.WORKSPACE_VIEW) is False

    with pytest.raises(HTTPException) as exc_info:
        authz.assert_authorized(ctx["user_b"].id, ctx["ws_a"].id, Permissions.WORKSPACE_VIEW)
    assert exc_info.value.status_code == 403

    # Assert workspace ownership helper
    with pytest.raises(HTTPException) as exc_ws:
        authz.assert_workspace_ownership(ctx["ws_a"].id, ctx["ws_b"].id)
    assert exc_ws.value.status_code == 403


def test_idor_bola_cross_workspace_probes(authz_test_db):
    ctx = authz_test_db
    collab = ctx["collab"]

    # User B tries to probe document doc-12345 in Project A of Workspace A
    can_access = collab.check_access(
        workspace_id=ctx["ws_a"].id,
        user_id=ctx["user_b"].id,
        resource_type="document",
        resource_id="doc-12345",
        project_id=ctx["proj_a"].id,
        required_permission=Permissions.DOCUMENT_VIEW
    )
    assert can_access is False


def test_role_matrix_hierarchy_and_permissions(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]
    ws_id = ctx["ws_a"].id

    # 1. Workspace Owner has all permissions including transfer ownership
    owner_perms = authz.get_effective_permissions(ctx["owner_a"].id, ws_id)
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP in owner_perms
    assert Permissions.WORKSPACE_ROLES_MANAGE in owner_perms
    assert Permissions.DOCUMENT_CREATE in owner_perms

    # 2. Workspace Admin has roles manage, but NOT transfer ownership
    admin_perms = authz.get_effective_permissions(ctx["admin_a"].id, ws_id)
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP not in admin_perms
    assert Permissions.WORKSPACE_ROLES_MANAGE in admin_perms
    assert Permissions.DOCUMENT_CREATE in admin_perms

    # 3. Workspace Member has document create/update, but NOT roles/members manage
    member_perms = authz.get_effective_permissions(ctx["member_a"].id, ws_id)
    assert Permissions.WORKSPACE_ROLES_MANAGE not in member_perms
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP not in member_perms
    assert Permissions.DOCUMENT_CREATE in member_perms
    assert Permissions.WORKFLOW_EXECUTE in member_perms

    # 4. Workspace Viewer has document view, but CANNOT create documents or workflows
    viewer_perms = authz.get_effective_permissions(ctx["viewer_a"].id, ws_id)
    assert Permissions.DOCUMENT_VIEW in viewer_perms
    assert Permissions.DOCUMENT_CREATE not in viewer_perms
    assert Permissions.WORKFLOW_CREATE not in viewer_perms


def test_team_role_overlay_and_boundaries(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]
    ws_id = ctx["ws_a"].id
    team_id = ctx["team_a"].id

    # Member A is a member of Workspace A and team owner of Team A
    # Base member doesn't have TEAM_UPDATE in workspace role
    base_perms = authz.get_effective_permissions(ctx["member_a"].id, ws_id)
    assert Permissions.TEAM_UPDATE not in base_perms

    # With team overlay, Member A gains TEAM_UPDATE & TEAM_MANAGE
    team_perms = authz.get_effective_permissions(ctx["member_a"].id, ws_id, team_id=team_id)
    assert Permissions.TEAM_UPDATE in team_perms
    assert Permissions.TEAM_MANAGE in team_perms
    assert Permissions.MEMBER_ADD in team_perms
    # But still does NOT gain workspace-level transfer ownership
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP not in team_perms


def test_project_role_overlay_and_boundaries(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]
    ws_id = ctx["ws_a"].id
    proj_id = ctx["proj_a"].id

    # Viewer A has viewer workspace role (no PROJECT_UPDATE)
    base_perms = authz.get_effective_permissions(ctx["viewer_a"].id, ws_id)
    assert Permissions.PROJECT_UPDATE not in base_perms

    # With project editor overlay, Viewer A gains PROJECT_UPDATE and resource add
    proj_perms = authz.get_effective_permissions(ctx["viewer_a"].id, ws_id, project_id=proj_id)
    assert Permissions.PROJECT_UPDATE in proj_perms
    assert Permissions.PROJECT_RESOURCE_ADD in proj_perms


def test_security_context_tenant_assertion(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]

    sec_ctx = authz.create_security_context(
        user_id=ctx["owner_a"].id,
        workspace_id=ctx["ws_a"].id,
        trust_level="high"
    )

    # Same tenant assertion succeeds
    sec_ctx.assert_same_tenant(ctx["ws_a"].id)

    # Cross-tenant assertion raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        sec_ctx.assert_same_tenant(ctx["ws_b"].id)
    assert "Cross-tenant access violation" in str(exc_info.value)


def test_system_admin_universal_access(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]

    # System admin has ALL_PERMISSIONS across any workspace
    perms = authz.get_effective_permissions(ctx["sys_admin"].id, ctx["ws_a"].id)
    assert perms == ALL_PERMISSIONS
    assert authz.authorize(ctx["sys_admin"].id, ctx["ws_a"].id, Permissions.WORKSPACE_TRANSFER_OWNERSHIP) is True


def test_inactive_and_deleted_user_denied_permissions(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]

    # Inactive user receives empty permission set
    perms = authz.get_effective_permissions(ctx["inactive_user"].id, ctx["ws_a"].id)
    assert perms == set()
    assert authz.authorize(ctx["inactive_user"].id, ctx["ws_a"].id, Permissions.WORKSPACE_VIEW) is False


def test_property_fuzz_malformed_client_identifiers(authz_test_db):
    ctx = authz_test_db
    authz = ctx["authz"]

    # Arbitrary non-existent UUIDs
    random_user = uuid.uuid4()
    random_ws = uuid.uuid4()

    assert authz.authorize(random_user, random_ws, Permissions.WORKSPACE_VIEW) is False
    assert authz.authorize(ctx["member_a"].id, random_ws, "non_existent:permission") is False
