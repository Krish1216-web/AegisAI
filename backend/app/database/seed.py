import uuid
from sqlalchemy.orm import Session
from loguru import logger

from app.models.user import User, Role
from app.models.workspace import Organization, Workspace, WorkspaceMember
from app.core.security import get_password_hash

def seed_database(db: Session):
    """
    Checks if the database is empty of users and seeds standard system roles,
    default users (user/user2026, admin/admin2026, superadmin/super2026),
    a default organization, and a default workspace.
    """
    try:
        # Check if users already exist
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info("Database already seeded. Skipping seeder execution.")
            return

        logger.info("Starting database auto-seeding...")

        # 1. Seed Roles
        roles_to_seed = [
            ("Super Admin", "Full root level capabilities and system bypass access."),
            ("Admin", "Administrative portal access, user and MCP controls."),
            ("User", "Standard workspace operator access.")
        ]
        
        role_map = {}
        for r_name, r_desc in roles_to_seed:
            role = db.query(Role).filter(Role.name == r_name).first()
            if not role:
                role = Role(id=uuid.uuid4(), name=r_name, description=r_desc)
                db.add(role)
                db.flush()
            role_map[r_name] = role

        # 2. Seed default organization and workspace
        org_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        
        default_org = Organization(
            id=org_id,
            name="Default Organization"
        )
        db.add(default_org)
        db.flush()

        default_workspace = Workspace(
            id=workspace_id,
            organization_id=org_id,
            name="Default Workspace"
        )
        db.add(default_workspace)
        db.flush()

        # 3. Seed Users
        users_to_seed = [
            ("superadmin", "superadmin@aegis.ai", "super2026", "Super Admin", "owner"),
            ("admin", "admin@aegis.ai", "admin2026", "Admin", "admin"),
            ("user", "user@aegis.ai", "user2026", "User", "member")
        ]

        for username, email, password, role_name, ws_role in users_to_seed:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    username=username,
                    email=email,
                    password_hash=get_password_hash(password),
                    role_id=role_map[role_name].id,
                    is_active=True,
                    is_verified=True,
                    settings={"default_workspace_id": str(workspace_id)}
                )
                db.add(user)
                db.flush()

                # Add to default workspace member list
                member = WorkspaceMember(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    user_id=user.id,
                    role=ws_role
                )
                db.add(member)

        db.commit()
        logger.info(f"Database auto-seeding completed. Workspace ID: {workspace_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Database auto-seeding failed: {e}")
        raise
