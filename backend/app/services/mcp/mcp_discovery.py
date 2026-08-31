import uuid
import datetime
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger

from app.models.mcp import MCPServer, MCPCapability, MCPServerStatus, MCPCapabilityType
from app.core.mcp.base import (
    BaseMCPClient,
    MCPToolDefinition,
    MCPResourceDefinition,
    MCPPromptDefinition,
    MCPInitializeResult,
    MCPClientError,
    MCPConnectionError,
    MCPValidationError
)
from app.core.mcp.factory import MCPClientFactory
from app.core.mcp.validation import MCPValidator

class MCPDiscoveryService:
    """
    Service responsible for connecting to MCP servers, performing handshakes,
    validating schemas, and synchronizing discovered capabilities in the database.
    """
    def __init__(self, db: Session):
        self.db = db

    async def discover_capabilities(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        prune_stale: bool = True
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()

        server = self.db.query(MCPServer).filter(
            and_(
                MCPServer.id == server_id,
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPServer.deleted_at.is_(None)
            )
        ).first()

        if not server:
            raise MCPValidationError(f"MCP server not found or access denied for ID: {server_id}")

        if not server.enabled:
            raise MCPValidationError(f"Cannot discover capabilities on disabled MCP server '{server.name}'.")

        client: Optional[BaseMCPClient] = None
        try:
            client = MCPClientFactory.create_client(
                server_url=server.server_url,
                transport=server.transport,
                auth_config=server.auth_config
            )

            # 1. Handshake & Initialization
            init_res: MCPInitializeResult = await client.initialize()
            
            # 2. Fetch Capabilities (Read-Only)
            tools: List[MCPToolDefinition] = await client.list_tools()
            resources: List[MCPResourceDefinition] = await client.list_resources()
            prompts: List[MCPPromptDefinition] = await client.list_prompts()

            # 3. Synchronize with Database
            existing_caps = self.db.query(MCPCapability).filter(
                and_(
                    MCPCapability.server_id == server.id,
                    MCPCapability.deleted_at.is_(None)
                )
            ).all()

            existing_map = {(c.capability_type, c.name): c for c in existing_caps}
            seen_keys = set()
            added_count = 0
            updated_count = 0

            # Process Tools
            for tool in tools:
                validated_schema = MCPValidator.validate_tool_input_schema(tool.input_schema)
                validated_name = MCPValidator.validate_server_name(tool.name)
                key = (MCPCapabilityType.TOOL, validated_name)
                seen_keys.add(key)

                if key in existing_map:
                    cap = existing_map[key]
                    cap.description = tool.description
                    cap.input_schema = validated_schema
                    cap.meta_data = MCPValidator.validate_metadata(tool.meta_data)
                    cap.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    updated_count += 1
                else:
                    new_cap = MCPCapability(
                        id=uuid.uuid4(),
                        server_id=server.id,
                        capability_type=MCPCapabilityType.TOOL,
                        name=validated_name,
                        description=tool.description,
                        input_schema=validated_schema,
                        meta_data=MCPValidator.validate_metadata(tool.meta_data),
                        enabled=True
                    )
                    self.db.add(new_cap)
                    added_count += 1

            # Process Resources
            for res in resources:
                validated_name = MCPValidator.validate_server_name(res.name)
                key = (MCPCapabilityType.RESOURCE, validated_name)
                seen_keys.add(key)
                res_meta = dict(res.meta_data or {})
                res_meta["uri"] = res.uri
                if res.mime_type:
                    res_meta["mime_type"] = res.mime_type

                if key in existing_map:
                    cap = existing_map[key]
                    cap.description = res.description
                    cap.meta_data = MCPValidator.validate_metadata(res_meta)
                    cap.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    updated_count += 1
                else:
                    new_cap = MCPCapability(
                        id=uuid.uuid4(),
                        server_id=server.id,
                        capability_type=MCPCapabilityType.RESOURCE,
                        name=validated_name,
                        description=res.description,
                        meta_data=MCPValidator.validate_metadata(res_meta),
                        enabled=True
                    )
                    self.db.add(new_cap)
                    added_count += 1

            # Process Prompts
            for p in prompts:
                validated_name = MCPValidator.validate_server_name(p.name)
                key = (MCPCapabilityType.PROMPT, validated_name)
                seen_keys.add(key)
                prompt_meta = dict(p.meta_data or {})
                prompt_meta["arguments"] = p.arguments

                if key in existing_map:
                    cap = existing_map[key]
                    cap.description = p.description
                    cap.meta_data = MCPValidator.validate_metadata(prompt_meta)
                    cap.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    updated_count += 1
                else:
                    new_cap = MCPCapability(
                        id=uuid.uuid4(),
                        server_id=server.id,
                        capability_type=MCPCapabilityType.PROMPT,
                        name=validated_name,
                        description=p.description,
                        meta_data=MCPValidator.validate_metadata(prompt_meta),
                        enabled=True
                    )
                    self.db.add(new_cap)
                    added_count += 1

            # Prune stale capabilities if requested
            pruned_count = 0
            if prune_stale:
                for key, cap in existing_map.items():
                    if key not in seen_keys:
                        self.db.delete(cap)
                        pruned_count += 1

            # Update Server Status and Timestamp
            server.status = MCPServerStatus.ACTIVE
            server.last_connected_at = datetime.datetime.now(datetime.timezone.utc)
            self.db.commit()

            elapsed = time.perf_counter() - start_time
            logger.info(
                f"Discovered capabilities for MCP server '{server.name}': "
                f"{len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts in {elapsed:.3f}s"
            )

            return {
                "server_id": str(server.id),
                "server_name": server.name,
                "status": server.status.value,
                "protocol_version": init_res.protocol_version,
                "total_tools": len(tools),
                "total_resources": len(resources),
                "total_prompts": len(prompts),
                "added_capabilities": added_count,
                "updated_capabilities": updated_count,
                "pruned_capabilities": pruned_count,
                "discovery_latency_ms": round(elapsed * 1000, 2)
            }

        except Exception as e:
            server.status = MCPServerStatus.ERROR
            self.db.commit()
            logger.error(f"Capability discovery failed for MCP server '{server.name}': {e}")
            raise e

        finally:
            if client:
                await client.close()
