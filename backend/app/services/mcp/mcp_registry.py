import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from loguru import logger

from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPAuthenticationType, MCPCapabilityType
from app.core.mcp.validation import MCPValidator
from app.core.mcp.security import CredentialStore
from app.core.mcp.base import MCPValidationError

class MCPRegistryService:
    """
    Service managing tenant-isolated MCP Server registrations, updates, and listings.
    """
    def __init__(self, db: Session):
        self.db = db

    def register_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: str,
        server_url: str,
        transport: MCPTransport = MCPTransport.SSE,
        description: Optional[str] = None,
        authentication_type: MCPAuthenticationType = MCPAuthenticationType.NONE,
        auth_config: Optional[Dict[str, Any]] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> MCPServer:
        # Validation
        validated_name = MCPValidator.validate_server_name(name)
        validated_url = MCPValidator.validate_server_url(server_url, transport=transport)
        validated_meta = MCPValidator.validate_metadata(meta_data)
        validated_auth = MCPValidator.validate_metadata(auth_config)

        # Check for duplicate server name within the same workspace
        existing = self.db.query(MCPServer).filter(
            and_(
                MCPServer.workspace_id == workspace_id,
                MCPServer.name == validated_name,
                MCPServer.deleted_at.is_(None)
            )
        ).first()

        if existing:
            raise MCPValidationError(f"An MCP server named '{validated_name}' is already registered in this workspace.")

        server = MCPServer(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            name=validated_name,
            description=description,
            server_url=validated_url,
            transport=transport,
            status=MCPServerStatus.INACTIVE,
            enabled=True,
            authentication_type=authentication_type,
            auth_config=validated_auth,
            meta_data=validated_meta
        )

        self.db.add(server)
        self.db.commit()
        self.db.refresh(server)
        logger.info(f"Registered new MCP server '{server.name}' (ID: {server.id}) for user {user_id} in workspace {workspace_id}")
        return server

    def get_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID
    ) -> Optional[MCPServer]:
        return self.db.query(MCPServer).filter(
            and_(
                MCPServer.id == server_id,
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPServer.deleted_at.is_(None)
            )
        ).first()

    def list_servers(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: Optional[MCPServerStatus] = None,
        enabled_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[MCPServer], int]:
        query = self.db.query(MCPServer).filter(
            and_(
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPServer.deleted_at.is_(None)
            )
        )

        if status:
            query = query.filter(MCPServer.status == status)
        if enabled_only:
            query = query.filter(MCPServer.enabled.is_(True))

        total = query.count()
        servers = query.order_by(MCPServer.created_at.desc()).offset(offset).limit(limit).all()
        return servers, total

    def update_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        server_url: Optional[str] = None,
        transport: Optional[MCPTransport] = None,
        authentication_type: Optional[MCPAuthenticationType] = None,
        auth_config: Optional[Dict[str, Any]] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None
    ) -> Optional[MCPServer]:
        server = self.get_server(user_id, workspace_id, server_id)
        if not server:
            return None

        if name is not None:
            validated_name = MCPValidator.validate_server_name(name)
            # Check duplicate name collision
            if validated_name != server.name:
                collision = self.db.query(MCPServer).filter(
                    and_(
                        MCPServer.workspace_id == workspace_id,
                        MCPServer.name == validated_name,
                        MCPServer.id != server_id,
                        MCPServer.deleted_at.is_(None)
                    )
                ).first()
                if collision:
                    raise MCPValidationError(f"An MCP server named '{validated_name}' already exists in this workspace.")
                server.name = validated_name

        target_transport = transport if transport is not None else server.transport

        if server_url is not None:
            server.server_url = MCPValidator.validate_server_url(server_url, transport=target_transport)

        if transport is not None:
            server.transport = transport

        if description is not None:
            server.description = description

        if authentication_type is not None:
            server.authentication_type = authentication_type

        if auth_config is not None:
            server.auth_config = MCPValidator.validate_metadata(auth_config)

        if meta_data is not None:
            server.meta_data = MCPValidator.validate_metadata(meta_data)

        if enabled is not None:
            server.enabled = enabled
            if not enabled:
                server.status = MCPServerStatus.DISABLED

        server.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        self.db.refresh(server)
        logger.info(f"Updated MCP server '{server.name}' (ID: {server.id})")
        return server

    def delete_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID
    ) -> bool:
        server = self.get_server(user_id, workspace_id, server_id)
        if not server:
            return False

        self.db.delete(server)
        self.db.commit()
        logger.info(f"Deleted MCP server '{server.name}' (ID: {server_id})")
        return True

    def toggle_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        enabled: bool
    ) -> Optional[MCPServer]:
        return self.update_server(user_id=user_id, workspace_id=workspace_id, server_id=server_id, enabled=enabled)

    def list_capabilities(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        capability_type: Optional[MCPCapabilityType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[MCPCapability], int]:
        server = self.get_server(user_id, workspace_id, server_id)
        if not server:
            return [], 0

        query = self.db.query(MCPCapability).filter(
            and_(
                MCPCapability.server_id == server_id,
                MCPCapability.deleted_at.is_(None)
            )
        )

        if capability_type:
            query = query.filter(MCPCapability.capability_type == capability_type)

        total = query.count()
        capabilities = query.order_by(MCPCapability.name.asc()).offset(offset).limit(limit).all()
        return capabilities, total
