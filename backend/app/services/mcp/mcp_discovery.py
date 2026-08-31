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
    MCPValidationError,
    MCPTimeoutError
)
from app.core.mcp.connection import MCPConnectionManager
from app.core.mcp.normalization import MCPNormalizer
from app.core.mcp.validation import MCPValidator

# In-memory lock registry for local testing / fallback
_LOCAL_DISCOVERY_LOCKS = set()

class MCPDiscoveryService:
    """
    Advanced capability discovery and synchronization engine for MCP servers.
    Provides change tracking, definition hashing, soft-stale detection, and concurrency protection.
    """
    def __init__(self, db: Session, redis_client: Optional[Any] = None):
        self.db = db
        self.redis = redis_client

    async def _acquire_lock(self, server_id: str) -> bool:
        lock_key = f"aegis:mcp:discovery:{server_id}"
        if self.redis:
            try:
                # Try acquiring Redis distributed lock for 45s
                acquired = await self.redis.set(lock_key, "locked", ex=45, nx=True)
                return bool(acquired)
            except Exception:
                pass
        
        # Local fallback lock
        if server_id in _LOCAL_DISCOVERY_LOCKS:
            return False
        _LOCAL_DISCOVERY_LOCKS.add(server_id)
        return True

    async def _release_lock(self, server_id: str) -> None:
        lock_key = f"aegis:mcp:discovery:{server_id}"
        if self.redis:
            try:
                await self.redis.delete(lock_key)
            except Exception:
                pass
        _LOCAL_DISCOVERY_LOCKS.discard(server_id)

    async def discover_capabilities(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        str_server_id = str(server_id)

        # 1. Acquire Concurrency Lock
        if not await self._acquire_lock(str_server_id):
            raise MCPValidationError(f"Capability discovery is currently in progress for server {server_id}. Please wait.")

        server = self.db.query(MCPServer).filter(
            and_(
                MCPServer.id == server_id,
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPServer.deleted_at.is_(None)
            )
        ).first()

        if not server:
            await self._release_lock(str_server_id)
            raise MCPValidationError(f"MCP server not found or access denied for ID: {server_id}")

        if not server.enabled:
            await self._release_lock(str_server_id)
            raise MCPValidationError(f"Cannot discover capabilities on disabled MCP server '{server.name}'.")

        client: Optional[BaseMCPClient] = None
        try:
            # 2. Connect & Handshake with Bounded Timeout & Exponential Retries
            client, init_res = await MCPConnectionManager.connect_and_initialize(
                server_url=server.server_url,
                transport=server.transport,
                auth_config=server.auth_config,
                timeout=10.0
            )

            # 3. Retrieve Capabilities (Read-Only)
            async def _fetch_caps():
                tools = await client.list_tools()
                resources = await client.list_resources()
                prompts = await client.list_prompts()
                return tools, resources, prompts

            tools, resources, prompts = await MCPConnectionManager.execute_with_retry(_fetch_caps, max_retries=2)

            # 4. Load Existing Capabilities
            existing_caps = self.db.query(MCPCapability).filter(
                and_(
                    MCPCapability.server_id == server.id,
                    MCPCapability.deleted_at.is_(None)
                )
            ).all()

            existing_map = {(c.capability_type, c.name): c for c in existing_caps}
            seen_keys = set()
            now = datetime.datetime.now(datetime.timezone.utc)

            tools_added = 0
            tools_changed = 0
            resources_added = 0
            resources_changed = 0
            prompts_added = 0
            prompts_changed = 0
            reactivated_count = 0
            unchanged_count = 0

            # Process Tools
            for tool in tools:
                validated_name = MCPValidator.validate_server_name(tool.name)
                sanitized_desc = MCPNormalizer.sanitize_text(tool.description)
                validated_schema = MCPValidator.validate_tool_input_schema(tool.input_schema)
                validated_meta = MCPValidator.validate_metadata(tool.meta_data)
                def_hash = MCPNormalizer.compute_definition_hash(
                    capability_type=MCPCapabilityType.TOOL,
                    name=validated_name,
                    description=sanitized_desc,
                    input_schema=validated_schema,
                    meta_data=validated_meta
                )
                key = (MCPCapabilityType.TOOL, validated_name)
                seen_keys.add(key)

                if key in existing_map:
                    cap = existing_map[key]
                    if cap.is_stale:
                        cap.is_stale = False
                        cap.stale_at = None
                        reactivated_count += 1

                    if cap.definition_hash != def_hash:
                        cap.description = sanitized_desc
                        cap.input_schema = validated_schema
                        cap.meta_data = validated_meta
                        cap.definition_hash = def_hash
                        cap.version = (cap.version or 1) + 1
                        cap.last_discovered_at = now
                        tools_changed += 1
                    else:
                        cap.last_discovered_at = now
                        unchanged_count += 1
                else:
                    new_cap = MCPCapability(
                        id=uuid.uuid4(),
                        server_id=server.id,
                        capability_type=MCPCapabilityType.TOOL,
                        name=validated_name,
                        description=sanitized_desc,
                        input_schema=validated_schema,
                        meta_data=validated_meta,
                        definition_hash=def_hash,
                        is_stale=False,
                        first_discovered_at=now,
                        last_discovered_at=now,
                        version=1,
                        enabled=True
                    )
                    self.db.add(new_cap)
                    tools_added += 1

            # Process Resources
            for res in resources:
                validated_name = MCPValidator.validate_server_name(res.name)
                sanitized_desc = MCPNormalizer.sanitize_text(res.description)
                res_meta = dict(res.meta_data or {})
                res_meta["uri"] = res.uri
                if res.mime_type:
                    res_meta["mime_type"] = res.mime_type
                validated_meta = MCPValidator.validate_metadata(res_meta)
                def_hash = MCPNormalizer.compute_definition_hash(
                    capability_type=MCPCapabilityType.RESOURCE,
                    name=validated_name,
                    description=sanitized_desc,
                    input_schema=None,
                    meta_data=validated_meta
                )
                key = (MCPCapabilityType.RESOURCE, validated_name)
                seen_keys.add(key)

                if key in existing_map:
                    cap = existing_map[key]
                    if cap.is_stale:
                        cap.is_stale = False
                        cap.stale_at = None
                        reactivated_count += 1

                    if cap.definition_hash != def_hash:
                        cap.description = sanitized_desc
                        cap.meta_data = validated_meta
                        cap.definition_hash = def_hash
                        cap.version = (cap.version or 1) + 1
                        cap.last_discovered_at = now
                        resources_changed += 1
                    else:
                        cap.last_discovered_at = now
                        unchanged_count += 1
                else:
                    new_cap = MCPCapability(
                        id=uuid.uuid4(),
                        server_id=server.id,
                        capability_type=MCPCapabilityType.RESOURCE,
                        name=validated_name,
                        description=sanitized_desc,
                        meta_data=validated_meta,
                        definition_hash=def_hash,
                        is_stale=False,
                        first_discovered_at=now,
                        last_discovered_at=now,
                        version=1,
                        enabled=True
                    )
                    self.db.add(new_cap)
                    resources_added += 1

            # Process Prompts
            for p in prompts:
                validated_name = MCPValidator.validate_server_name(p.name)
                sanitized_desc = MCPNormalizer.sanitize_text(p.description)
                prompt_meta = dict(p.meta_data or {})
                prompt_meta["arguments"] = p.arguments
                validated_meta = MCPValidator.validate_metadata(prompt_meta)
                def_hash = MCPNormalizer.compute_definition_hash(
                    capability_type=MCPCapabilityType.PROMPT,
                    name=validated_name,
                    description=sanitized_desc,
                    input_schema=None,
                    meta_data=validated_meta
                )
                key = (MCPCapabilityType.PROMPT, validated_name)
                seen_keys.add(key)

                if key in existing_map:
                    cap = existing_map[key]
                    if cap.is_stale:
                        cap.is_stale = False
                        cap.stale_at = None
                        reactivated_count += 1

                    if cap.definition_hash != def_hash:
                        cap.description = sanitized_desc
                        cap.meta_data = validated_meta
                        cap.definition_hash = def_hash
                        cap.version = (cap.version or 1) + 1
                        cap.last_discovered_at = now
                        prompts_changed += 1
                    else:
                        cap.last_discovered_at = now
                        unchanged_count += 1
                else:
                    new_cap = MCPCapability(
                        id=uuid.uuid4(),
                        server_id=server.id,
                        capability_type=MCPCapabilityType.PROMPT,
                        name=validated_name,
                        description=sanitized_desc,
                        meta_data=validated_meta,
                        definition_hash=def_hash,
                        is_stale=False,
                        first_discovered_at=now,
                        last_discovered_at=now,
                        version=1,
                        enabled=True
                    )
                    self.db.add(new_cap)
                    prompts_added += 1

            # Soft-Stale Detection for Disappeared Capabilities
            stale_count = 0
            for key, cap in existing_map.items():
                if key not in seen_keys and not cap.is_stale:
                    cap.is_stale = True
                    cap.stale_at = now
                    stale_count += 1

            # Update Server Metadata & Liveness Status
            server.status = MCPServerStatus.ACTIVE
            server.server_version = init_res.server_version or "1.0.0"
            server.protocol_version = init_res.protocol_version or "2024-11-05"
            server.last_connected_at = now
            server.last_discovery_at = now
            server.last_error = None
            self.db.commit()

            elapsed = time.perf_counter() - start_time
            logger.info(
                f"Completed MCP discovery for '{server.name}': "
                f"+{tools_added} tools, ~{tools_changed} changed, "
                f"+{resources_added} res, +{prompts_added} prompts, "
                f"{stale_count} stale in {elapsed:.3f}s"
            )

            return {
                "server_id": str(server.id),
                "server_name": server.name,
                "status": server.status.value,
                "server_version": server.server_version,
                "protocol_version": server.protocol_version,
                "total_tools": len(tools),
                "total_resources": len(resources),
                "total_prompts": len(prompts),
                "tools_added": tools_added,
                "tools_changed": tools_changed,
                "resources_added": resources_added,
                "resources_changed": resources_changed,
                "prompts_added": prompts_added,
                "prompts_changed": prompts_changed,
                "stale_capabilities": stale_count,
                "reactivated_capabilities": reactivated_count,
                "unchanged_capabilities": unchanged_count,
                "discovered_at": now.isoformat(),
                "discovery_latency_ms": round(elapsed * 1000, 2)
            }

        except Exception as e:
            server.status = MCPServerStatus.ERROR
            server.last_error = str(e)
            self.db.commit()
            logger.error(f"MCP discovery failed for '{server.name}': {e}")
            raise e

        finally:
            await self._release_lock(str_server_id)
            if client:
                await client.close()
