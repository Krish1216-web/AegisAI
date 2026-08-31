import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import get_db
from app.database.redis import get_redis
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User
from app.models.mcp import MCPServerStatus, MCPCapabilityType, MCPTransport, MCPAuthenticationType
from app.core.mcp.policy import ToolRiskLevel
from app.schemas.mcp import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPServerListResponse,
    MCPCapabilityResponse,
    MCPCapabilityListResponse,
    MCPDiscoveryResponse,
    MCPHealthCheckResponse,
    MCPToolResponse,
    MCPToolListResponse,
    MCPToolSearchRequest,
    MCPToolSearchResponse,
    MCPToolExecuteRequest,
    MCPToolExecutionResponse,
    MCPToolConfirmationRequest,
    MCPToolConfirmationResponse
)
from app.services.mcp.mcp_registry import MCPRegistryService
from app.services.mcp.mcp_discovery import MCPDiscoveryService
from app.services.mcp.mcp_tool_catalog import MCPToolCatalogService
from app.services.mcp.mcp_tool_executor import (
    MCPToolExecutionService,
    generate_tool_confirmation_token
)
from app.core.mcp.base import MCPValidationError, MCPClientError, MCPToolConfirmationRequired
from app.api.v1.endpoints.documents import resolve_workspace_id

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])

# ==========================================
# 1. MCP Server Registry Endpoints
# ==========================================

@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_rate_limit)])
async def register_mcp_server(
    payload: MCPServerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registers a new Model Context Protocol (MCP) server for the current workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    try:
        server = registry.register_server(
            user_id=current_user.id,
            workspace_id=workspace_id,
            name=payload.name,
            server_url=payload.server_url,
            transport=payload.transport,
            description=payload.description,
            authentication_type=payload.authentication_type,
            auth_config=payload.auth_config,
            meta_data=payload.metadata
        )
        resp = MCPServerResponse.model_validate(server)
        resp.capabilities_count = 0
        return resp
    except MCPValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to register MCP server: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register MCP server: {str(e)}")

@router.get("/servers", response_model=MCPServerListResponse, dependencies=[Depends(check_rate_limit)])
async def list_mcp_servers(
    status_filter: Optional[MCPServerStatus] = Query(None, alias="status"),
    enabled_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all MCP servers registered in the current user's workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    servers, total = registry.list_servers(
        user_id=current_user.id,
        workspace_id=workspace_id,
        status=status_filter,
        enabled_only=enabled_only,
        limit=limit,
        offset=offset
    )

    items = []
    for s in servers:
        resp = MCPServerResponse.model_validate(s)
        resp.capabilities_count = len([c for c in s.capabilities if not c.is_stale]) if s.capabilities else 0
        items.append(resp)

    return MCPServerListResponse(servers=items, total=total)

@router.get("/servers/{server_id}", response_model=MCPServerResponse, dependencies=[Depends(check_rate_limit)])
async def get_mcp_server(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves details for a specific MCP server.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    server = registry.get_server(user_id=current_user.id, workspace_id=workspace_id, server_id=server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found or access denied.")

    resp = MCPServerResponse.model_validate(server)
    resp.capabilities_count = len([c for c in server.capabilities if not c.is_stale]) if server.capabilities else 0
    return resp

@router.patch("/servers/{server_id}", response_model=MCPServerResponse, dependencies=[Depends(check_rate_limit)])
async def update_mcp_server(
    server_id: uuid.UUID,
    payload: MCPServerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates an existing MCP server configuration.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    try:
        server = registry.update_server(
            user_id=current_user.id,
            workspace_id=workspace_id,
            server_id=server_id,
            name=payload.name,
            description=payload.description,
            server_url=payload.server_url,
            transport=payload.transport,
            authentication_type=payload.authentication_type,
            auth_config=payload.auth_config,
            meta_data=payload.metadata,
            enabled=payload.enabled
        )
        if not server:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found or access denied.")

        resp = MCPServerResponse.model_validate(server)
        resp.capabilities_count = len([c for c in server.capabilities if not c.is_stale]) if server.capabilities else 0
        return resp
    except MCPValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to update MCP server: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update MCP server: {str(e)}")

@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_rate_limit)])
async def delete_mcp_server(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes an MCP server and its associated capabilities.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    deleted = registry.delete_server(user_id=current_user.id, workspace_id=workspace_id, server_id=server_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found or access denied.")
    return None

@router.post("/servers/{server_id}/discover", response_model=MCPDiscoveryResponse, dependencies=[Depends(check_rate_limit)])
@router.post("/servers/{server_id}/refresh", response_model=MCPDiscoveryResponse, dependencies=[Depends(check_rate_limit)])
async def discover_server_capabilities(
    server_id: uuid.UUID,
    force_refresh: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    Performs discovery against the MCP server and synchronizes tools, resources, and prompts
    with hash-based versioning and soft-stale detection.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    discovery = MCPDiscoveryService(db, redis_client=redis)
    
    try:
        result = await discovery.discover_capabilities(
            user_id=current_user.id,
            workspace_id=workspace_id,
            server_id=server_id,
            force_refresh=force_refresh
        )
        return MCPDiscoveryResponse(**result)
    except MCPValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except MCPClientError as ce:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"MCP server communication failed: {str(ce)}")
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Discovery failed: {str(e)}")

@router.get("/servers/{server_id}/health", response_model=MCPHealthCheckResponse, dependencies=[Depends(check_rate_limit)])
async def check_mcp_server_health(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Performs an active health and liveness probe against the MCP server.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    try:
        res = await registry.check_server_health(
            user_id=current_user.id,
            workspace_id=workspace_id,
            server_id=server_id
        )
        return MCPHealthCheckResponse(**res)
    except MCPValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/servers/{server_id}/capabilities", response_model=MCPCapabilityListResponse, dependencies=[Depends(check_rate_limit)])
async def list_server_capabilities(
    server_id: uuid.UUID,
    capability_type: Optional[MCPCapabilityType] = Query(None, alias="type"),
    search: Optional[str] = Query(None),
    include_stale: bool = Query(True),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists discovered capabilities (tools, resources, prompts) for an MCP server with search and stale filtering.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    server = registry.get_server(user_id=current_user.id, workspace_id=workspace_id, server_id=server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found or access denied.")

    caps, total = registry.list_capabilities(
        user_id=current_user.id,
        workspace_id=workspace_id,
        server_id=server_id,
        capability_type=capability_type,
        search=search,
        include_stale=include_stale,
        limit=limit,
        offset=offset
    )

    items = [MCPCapabilityResponse.model_validate(c) for c in caps]
    return MCPCapabilityListResponse(capabilities=items, total=total)

@router.get("/servers/{server_id}/tools", response_model=MCPCapabilityListResponse, dependencies=[Depends(check_rate_limit)])
async def list_server_tools(
    server_id: uuid.UUID,
    search: Optional[str] = Query(None),
    include_stale: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists tools exposed by a specific MCP server.
    """
    return await list_server_capabilities(
        server_id=server_id,
        capability_type=MCPCapabilityType.TOOL,
        search=search,
        include_stale=include_stale,
        limit=limit,
        offset=offset,
        current_user=current_user,
        db=db
    )

@router.get("/servers/{server_id}/resources", response_model=MCPCapabilityListResponse, dependencies=[Depends(check_rate_limit)])
async def list_server_resources(
    server_id: uuid.UUID,
    search: Optional[str] = Query(None),
    include_stale: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists resources exposed by a specific MCP server.
    """
    return await list_server_capabilities(
        server_id=server_id,
        capability_type=MCPCapabilityType.RESOURCE,
        search=search,
        include_stale=include_stale,
        limit=limit,
        offset=offset,
        current_user=current_user,
        db=db
    )

@router.get("/servers/{server_id}/prompts", response_model=MCPCapabilityListResponse, dependencies=[Depends(check_rate_limit)])
async def list_server_prompts(
    server_id: uuid.UUID,
    search: Optional[str] = Query(None),
    include_stale: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists prompt templates exposed by a specific MCP server.
    """
    return await list_server_capabilities(
        server_id=server_id,
        capability_type=MCPCapabilityType.PROMPT,
        search=search,
        include_stale=include_stale,
        limit=limit,
        offset=offset,
        current_user=current_user,
        db=db
    )

@router.get("/capabilities/{capability_id}", response_model=MCPCapabilityResponse, dependencies=[Depends(check_rate_limit)])
async def get_capability_details(
    capability_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves full capability definition and JSON schema by capability ID.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    cap = registry.get_capability(user_id=current_user.id, workspace_id=workspace_id, capability_id=capability_id)
    if not cap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found or access denied.")
    return MCPCapabilityResponse.model_validate(cap)

@router.post("/servers/{server_id}/enable", response_model=MCPServerResponse, dependencies=[Depends(check_rate_limit)])
async def enable_mcp_server(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enables an MCP server.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    server = registry.toggle_server(user_id=current_user.id, workspace_id=workspace_id, server_id=server_id, enabled=True)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found or access denied.")
    resp = MCPServerResponse.model_validate(server)
    resp.capabilities_count = len([c for c in server.capabilities if not c.is_stale]) if server.capabilities else 0
    return resp

@router.post("/servers/{server_id}/disable", response_model=MCPServerResponse, dependencies=[Depends(check_rate_limit)])
async def disable_mcp_server(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disables an MCP server.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    registry = MCPRegistryService(db)
    
    server = registry.toggle_server(user_id=current_user.id, workspace_id=workspace_id, server_id=server_id, enabled=False)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found or access denied.")
    resp = MCPServerResponse.model_validate(server)
    resp.capabilities_count = len([c for c in server.capabilities if not c.is_stale]) if server.capabilities else 0
    return resp

# ==========================================
# 2. Phase 6.3 Tool Catalog Endpoints
# ==========================================

@router.get("/tools", response_model=MCPToolListResponse, dependencies=[Depends(check_rate_limit)])
async def list_workspace_tools(
    server_id: Optional[uuid.UUID] = Query(None),
    enabled_only: bool = Query(False),
    include_stale: bool = Query(True),
    risk_level: Optional[ToolRiskLevel] = Query(None),
    transport: Optional[MCPTransport] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all MCP tools discovered across the workspace with risk assessment and execution readiness flags.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    catalog = MCPToolCatalogService(db)

    tools, total = catalog.list_tools(
        user_id=current_user.id,
        workspace_id=workspace_id,
        server_id=server_id,
        enabled_only=enabled_only,
        include_stale=include_stale,
        risk_level=risk_level,
        transport=transport,
        search=search,
        limit=limit,
        offset=offset
    )
    return MCPToolListResponse(tools=[MCPToolResponse(**t) for t in tools], total=total)

@router.post("/tools/search", response_model=MCPToolSearchResponse, dependencies=[Depends(check_rate_limit)])
async def search_workspace_tools(
    payload: MCPToolSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Performs deterministic multi-tiered ranked search across all discovered tools in the current workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    catalog = MCPToolCatalogService(db)

    results = catalog.search_tools(
        user_id=current_user.id,
        workspace_id=workspace_id,
        query=payload.query,
        server_id=payload.server_id,
        risk_level=payload.risk_level,
        enabled_only=payload.enabled_only,
        include_stale=payload.include_stale,
        limit=payload.limit
    )
    return MCPToolSearchResponse(
        results=[MCPToolResponse(**t) for t in results],
        total=len(results),
        query=payload.query
    )

@router.get("/tools/{tool_id}", response_model=MCPToolResponse, dependencies=[Depends(check_rate_limit)])
async def get_tool_details(
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves full metadata, JSON schema, risk classification, and availability state for an MCP tool.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    catalog = MCPToolCatalogService(db)

    tool = catalog.get_tool(user_id=current_user.id, workspace_id=workspace_id, tool_id=tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP tool not found or access denied.")
    return MCPToolResponse(**tool)

@router.post("/tools/{tool_id}/enable", response_model=MCPToolResponse, dependencies=[Depends(check_rate_limit)])
async def enable_mcp_tool(
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enables a specific tool capability without modifying other server tools.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    catalog = MCPToolCatalogService(db)

    tool = catalog.toggle_tool(user_id=current_user.id, workspace_id=workspace_id, tool_id=tool_id, enabled=True)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP tool not found or access denied.")
    return MCPToolResponse(**tool)

@router.post("/tools/{tool_id}/disable", response_model=MCPToolResponse, dependencies=[Depends(check_rate_limit)])
async def disable_mcp_tool(
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disables a specific tool capability without deleting it.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    catalog = MCPToolCatalogService(db)

    tool = catalog.toggle_tool(user_id=current_user.id, workspace_id=workspace_id, tool_id=tool_id, enabled=False)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP tool not found or access denied.")
    return MCPToolResponse(**tool)

# ==========================================
# 3. Phase 6.4 Tool Execution Endpoints
# ==========================================

@router.post("/tools/{tool_id}/confirm", response_model=MCPToolConfirmationResponse, dependencies=[Depends(check_rate_limit)])
async def generate_confirmation_token_endpoint(
    tool_id: uuid.UUID,
    payload: MCPToolConfirmationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a single-use confirmation token for a RESTRICTED tool execution, bound to user, workspace, tool ID, and arguments.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    catalog = MCPToolCatalogService(db)

    tool = catalog.get_tool(user_id=current_user.id, workspace_id=workspace_id, tool_id=tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP tool not found or access denied.")

    token = generate_tool_confirmation_token(
        user_id=current_user.id,
        workspace_id=workspace_id,
        tool_id=tool_id,
        arguments=payload.arguments,
        expires_in_seconds=300
    )

    return MCPToolConfirmationResponse(
        token=token,
        tool_id=str(tool_id),
        expires_in_seconds=300,
        risk_level=tool["risk_level"],
        risk_reasons=tool.get("risk_reasons", [])
    )

@router.post("/tools/{tool_id}/execute", response_model=MCPToolExecutionResponse, dependencies=[Depends(check_rate_limit)])
async def execute_mcp_tool_endpoint(
    tool_id: uuid.UUID,
    payload: MCPToolExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    Safely executes an approved MCP tool with JSON Schema validation, risk policies,
    single-use confirmation for RESTRICTED tools, and sanitized result handling.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    executor = MCPToolExecutionService(db, redis_client=redis)

    try:
        res = await executor.execute_tool(
            user_id=current_user.id,
            workspace_id=workspace_id,
            tool_id=tool_id,
            arguments=payload.arguments,
            confirmation_token=payload.confirmation_token,
            timeout=payload.timeout or 15.0
        )
        return MCPToolExecutionResponse(
            execution_id=res.execution_id,
            tool_id=res.tool_id,
            tool_name=res.tool_name,
            status=res.status,
            result=res.result,
            text_content=res.text_content,
            duration_ms=res.duration_ms,
            retry_count=res.retry_count,
            truncated=res.truncated,
            error=res.error
        )
    except MCPToolConfirmationRequired as cr:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "error": "REQUIRES_CONFIRMATION",
                "message": str(cr),
                "tool_id": cr.tool_id,
                "risk_reasons": cr.risk_reasons
            }
        )
    except MCPValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except MCPClientError as ce:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"MCP server execution failed: {str(ce)}")
    except Exception as e:
        logger.error(f"MCP Tool execution error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Execution error: {str(e)}")

