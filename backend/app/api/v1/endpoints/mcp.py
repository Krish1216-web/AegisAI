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
    MCPToolConfirmationResponse,
    MCPResourceResponse,
    MCPResourceListResponse,
    MCPResourceSearchRequest,
    MCPResourceSearchResponse,
    MCPResourceReadResponse,
    MCPPromptResponse,
    MCPPromptListResponse,
    MCPPromptSearchRequest,
    MCPPromptSearchResponse,
    MCPPromptRenderRequest,
    MCPPromptRenderResponse,
    MCPSecurityStatusResponse,
    MCPSecurityAuditLogResponse,
    MCPSecurityAuditEventSchema,
    MCPOverviewMetricsResponse,
    MCPServerMetricsSchema,
    MCPCapabilityMetricsSchema,
    MCPSecurityMetricsSchema,
    MCPExecutionMetricsSchema,
    MCPHealthMetricsSchema,
    MCPExecutionHistoryResponse,
    MCPExecutionHistoryItem
)
from app.services.mcp.mcp_registry import MCPRegistryService
from app.services.mcp.mcp_discovery import MCPDiscoveryService
from app.services.mcp.mcp_tool_catalog import MCPToolCatalogService
from app.services.mcp.mcp_tool_executor import (
    MCPToolExecutionService,
    generate_tool_confirmation_token
)
from app.services.mcp.mcp_resource_service import MCPResourceService
from app.services.mcp.mcp_prompt_service import MCPPromptService
from app.services.mcp.mcp_security import MCPSecurityService
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

# ==========================================
# 4. MCP Resource Endpoints (Phase 6.5)
# ==========================================

@router.get("/resources", response_model=MCPResourceListResponse)
def list_mcp_resources(
    server_id: Optional[uuid.UUID] = Query(None, description="Filter by server ID"),
    search: Optional[str] = Query(None, description="Search term for name or description"),
    enabled_only: bool = Query(False, description="Filter for enabled resources only"),
    include_stale: bool = Query(True, description="Whether to include stale resources"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Lists discovered MCP resources with filtering, search, and pagination.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPResourceService(db)
    resources, total = svc.list_resources(
        user_id=current_user.id,
        workspace_id=workspace_id,
        server_id=server_id,
        search=search,
        enabled_only=enabled_only,
        include_stale=include_stale,
        limit=limit,
        offset=offset
    )
    return MCPResourceListResponse(
        resources=[MCPResourceResponse(**r) for r in resources],
        total=total
    )

@router.post("/resources/search", response_model=MCPResourceSearchResponse)
def search_mcp_resources(
    req: MCPResourceSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Performs multi-tier ranked search across discovered MCP resources.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPResourceService(db)
    results = svc.search_resources(
        user_id=current_user.id,
        workspace_id=workspace_id,
        query=req.query,
        server_id=req.server_id,
        enabled_only=req.enabled_only,
        include_stale=req.include_stale,
        limit=req.limit
    )
    return MCPResourceSearchResponse(
        results=[MCPResourceResponse(**r) for r in results],
        total=len(results),
        query=req.query
    )

@router.get("/resources/{resource_id}", response_model=MCPResourceResponse)
def get_mcp_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Retrieves detailed metadata for a single discovered MCP resource.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPResourceService(db)
    res = svc.get_resource(current_user.id, workspace_id, resource_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP resource not found.")
    return MCPResourceResponse(**res)

@router.post("/resources/{resource_id}/read", response_model=MCPResourceReadResponse)
async def read_mcp_resource(
    resource_id: uuid.UUID,
    timeout: Optional[float] = Query(15.0, ge=1.0, le=60.0),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Reads content from a discovered MCP resource with strict URI validation, size limits, and sanitization.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPResourceService(db, redis_client=redis)
    try:
        content = await svc.read_resource(
            user_id=current_user.id,
            workspace_id=workspace_id,
            resource_id=resource_id,
            timeout=timeout
        )
        return MCPResourceReadResponse(
            uri=content.uri,
            mime_type=content.mime_type,
            text=content.text,
            size=content.size,
            truncated=content.truncated,
            metadata=content.metadata
        )
    except MCPValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except MCPClientError as ce:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"MCP server read failed: {str(ce)}")
    except Exception as e:
        logger.error(f"MCP Resource read error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Read error: {str(e)}")

@router.post("/resources/{resource_id}/enable", response_model=MCPResourceResponse)
def enable_mcp_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPResourceService(db)
    res = svc.toggle_resource(current_user.id, workspace_id, resource_id, enabled=True)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP resource not found.")
    return MCPResourceResponse(**res)

@router.post("/resources/{resource_id}/disable", response_model=MCPResourceResponse)
def disable_mcp_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPResourceService(db)
    res = svc.toggle_resource(current_user.id, workspace_id, resource_id, enabled=False)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP resource not found.")
    return MCPResourceResponse(**res)

# ==========================================
# 5. MCP Prompt Endpoints (Phase 6.5)
# ==========================================

@router.get("/prompts", response_model=MCPPromptListResponse)
def list_mcp_prompts(
    server_id: Optional[uuid.UUID] = Query(None, description="Filter by server ID"),
    search: Optional[str] = Query(None, description="Search term for name or description"),
    enabled_only: bool = Query(False, description="Filter for enabled prompts only"),
    include_stale: bool = Query(True, description="Whether to include stale prompts"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Lists discovered MCP prompt templates with filtering, search, and pagination.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPPromptService(db)
    prompts, total = svc.list_prompts(
        user_id=current_user.id,
        workspace_id=workspace_id,
        server_id=server_id,
        search=search,
        enabled_only=enabled_only,
        include_stale=include_stale,
        limit=limit,
        offset=offset
    )
    return MCPPromptListResponse(
        prompts=[MCPPromptResponse(**p) for p in prompts],
        total=total
    )

@router.post("/prompts/search", response_model=MCPPromptSearchResponse)
def search_mcp_prompts(
    req: MCPPromptSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Performs multi-tier ranked search across discovered MCP prompt templates.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPPromptService(db)
    results = svc.search_prompts(
        user_id=current_user.id,
        workspace_id=workspace_id,
        query=req.query,
        server_id=req.server_id,
        enabled_only=req.enabled_only,
        include_stale=req.include_stale,
        limit=req.limit
    )
    return MCPPromptSearchResponse(
        results=[MCPPromptResponse(**p) for p in results],
        total=len(results),
        query=req.query
    )

@router.get("/prompts/{prompt_id}", response_model=MCPPromptResponse)
def get_mcp_prompt(
    prompt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Retrieves detailed metadata and argument schemas for a single discovered prompt template.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPPromptService(db)
    res = svc.get_prompt(current_user.id, workspace_id, prompt_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP prompt not found.")
    return MCPPromptResponse(**res)

@router.post("/prompts/{prompt_id}/render", response_model=MCPPromptRenderResponse)
async def render_mcp_prompt(
    prompt_id: uuid.UUID,
    req: MCPPromptRenderRequest,
    timeout: Optional[float] = Query(15.0, ge=1.0, le=60.0),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    """
    Renders an MCP prompt template with bound arguments, strictly isolating messages as untrusted data.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPPromptService(db, redis_client=redis)
    try:
        res = await svc.render_prompt(
            user_id=current_user.id,
            workspace_id=workspace_id,
            prompt_id=prompt_id,
            arguments=req.arguments,
            timeout=timeout
        )
        return MCPPromptRenderResponse(
            prompt_id=res.prompt_id,
            name=res.name,
            description=res.description,
            messages=[{"role": m.role, "content": m.content, "untrusted": m.untrusted} for m in res.messages],
            untrusted=res.untrusted
        )
    except MCPValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except MCPClientError as ce:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"MCP server prompt rendering failed: {str(ce)}")
    except Exception as e:
        logger.error(f"MCP Prompt render error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Render error: {str(e)}")

@router.post("/prompts/{prompt_id}/enable", response_model=MCPPromptResponse)
def enable_mcp_prompt(
    prompt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPPromptService(db)
    res = svc.toggle_prompt(current_user.id, workspace_id, prompt_id, enabled=True)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP prompt not found.")
    return MCPPromptResponse(**res)

@router.post("/prompts/{prompt_id}/disable", response_model=MCPPromptResponse)
def disable_mcp_prompt(
    prompt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit: bool = Depends(check_rate_limit)
):
    workspace_id = resolve_workspace_id(current_user, db)
    svc = MCPPromptService(db)
    res = svc.toggle_prompt(current_user.id, workspace_id, prompt_id, enabled=False)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP prompt not found.")
    return MCPPromptResponse(**res)

# ==========================================
# 4. Phase 6.6 Security & Permission Endpoints
# ==========================================

@router.get("/security/status", response_model=MCPSecurityStatusResponse, dependencies=[Depends(check_rate_limit)])
def get_mcp_security_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns real-time workspace security policy status, active RBAC permissions, and risk metrics.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    sec_service = MCPSecurityService(db)
    status_data = sec_service.get_security_status(current_user.id, workspace_id)
    return MCPSecurityStatusResponse(**status_data)

@router.get("/security/audit-log", response_model=MCPSecurityAuditLogResponse, dependencies=[Depends(check_rate_limit)])
def get_mcp_security_audit_log(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves recent security audit events for the active workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    sec_service = MCPSecurityService(db)
    events = sec_service.get_workspace_audit_log(current_user.id, workspace_id, limit=limit)
    return MCPSecurityAuditLogResponse(
        events=[MCPSecurityAuditEventSchema(**e) for e in events],
        total=len(events)
    )

# ==========================================
# 5. Phase 6.8 MCP Control Center Overview & History
# ==========================================

@router.get("/overview", response_model=MCPOverviewMetricsResponse, dependencies=[Depends(check_rate_limit)])
def get_mcp_overview_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aggregates real-time live metrics across servers, capabilities, security decisions, health, and execution history.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    from app.models.mcp import MCPServer, MCPCapability, MCPServerStatus, MCPCapabilityType
    from app.models.ai import ToolExecution, Execution

    # 1. Servers Metrics
    servers_q = db.query(MCPServer).filter(MCPServer.workspace_id == workspace_id)
    total_servers = servers_q.count()
    active_servers = servers_q.filter(MCPServer.status == MCPServerStatus.ACTIVE, MCPServer.enabled == True).count()
    inactive_servers = servers_q.filter(MCPServer.status == MCPServerStatus.INACTIVE).count()
    error_servers = servers_q.filter(MCPServer.status == MCPServerStatus.ERROR).count()
    disabled_servers = servers_q.filter(MCPServer.enabled == False).count()

    # 2. Capabilities Metrics
    caps_q = db.query(MCPCapability).join(MCPServer, MCPCapability.server_id == MCPServer.id).filter(MCPServer.workspace_id == workspace_id)
    total_tools = caps_q.filter(MCPCapability.capability_type == MCPCapabilityType.TOOL).count()
    total_resources = caps_q.filter(MCPCapability.capability_type == MCPCapabilityType.RESOURCE).count()
    total_prompts = caps_q.filter(MCPCapability.capability_type == MCPCapabilityType.PROMPT).count()
    enabled_caps = caps_q.filter(MCPCapability.enabled == True, MCPCapability.is_stale == False).count()
    stale_caps = caps_q.filter(MCPCapability.is_stale == True).count()

    # 3. Security Metrics
    sec_service = MCPSecurityService(db)
    audit_events = sec_service.get_workspace_audit_log(current_user.id, workspace_id, limit=200)
    allowed_ops = sum(1 for e in audit_events if e.get("decision") == "ALLOW")
    conf_ops = sum(1 for e in audit_events if e.get("decision") == "REQUIRE_CONFIRMATION")
    denied_ops = sum(1 for e in audit_events if e.get("decision") == "DENY")

    # 4. Execution Metrics
    exec_q = db.query(ToolExecution).join(Execution, ToolExecution.execution_id == Execution.id).filter(Execution.workspace_id == workspace_id)
    total_execs = exec_q.count()
    success_execs = exec_q.filter(ToolExecution.status == "COMPLETED").count()
    failed_execs = exec_q.filter(ToolExecution.status == "FAILED").count()
    req_conf_execs = exec_q.filter(ToolExecution.status == "REQUIRES_CONFIRMATION").count()

    # 5. Health Metrics
    healthy_servers = active_servers
    unhealthy_servers = total_servers - healthy_servers
    latest_server = servers_q.order_by(MCPServer.last_discovery_at.desc().nullslast()).first()
    latest_health = servers_q.order_by(MCPServer.last_health_check_at.desc().nullslast()).first()

    return MCPOverviewMetricsResponse(
        servers=MCPServerMetricsSchema(
            total=total_servers,
            active=active_servers,
            inactive=inactive_servers,
            error=error_servers,
            disabled=disabled_servers
        ),
        capabilities=MCPCapabilityMetricsSchema(
            total_tools=total_tools,
            total_resources=total_resources,
            total_prompts=total_prompts,
            enabled_capabilities=enabled_caps,
            stale_capabilities=stale_caps
        ),
        security=MCPSecurityMetricsSchema(
            allowed_operations=allowed_ops,
            confirmation_required_operations=conf_ops,
            denied_operations=denied_ops,
            recent_events_count=len(audit_events)
        ),
        execution=MCPExecutionMetricsSchema(
            total=total_execs,
            successful=success_execs,
            failed=failed_execs,
            requires_confirmation=req_conf_execs
        ),
        health=MCPHealthMetricsSchema(
            healthy_servers=healthy_servers,
            unhealthy_servers=unhealthy_servers,
            last_discovery_at=latest_server.last_discovery_at.isoformat() if latest_server and latest_server.last_discovery_at else None,
            last_health_check_at=latest_health.last_health_check_at.isoformat() if latest_health and latest_health.last_health_check_at else None
        )
    )

@router.get("/executions", response_model=MCPExecutionHistoryResponse, dependencies=[Depends(check_rate_limit)])
def get_mcp_execution_history(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves tenant-isolated execution history records for tools run within the workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    from app.models.ai import ToolExecution, Execution
    from app.models.mcp import MCPCapability

    query = db.query(ToolExecution, Execution).join(Execution, ToolExecution.execution_id == Execution.id).filter(Execution.workspace_id == workspace_id)
    if status_filter:
        query = query.filter(ToolExecution.status == status_filter)

    total = query.count()
    rows = query.order_by(ToolExecution.started_at.desc()).offset(offset).limit(limit).all()

    # Pre-fetch capabilities to map human-readable names
    cap_ids = []
    for te, _ in rows:
        try:
            cap_ids.append(uuid.UUID(te.tool_id))
        except Exception:
            pass
    
    cap_map = {}
    if cap_ids:
        caps = db.query(MCPCapability).filter(MCPCapability.id.in_(cap_ids)).all()
        cap_map = {str(c.id): c.name for c in caps}

    history_items = []
    for te, ex in rows:
        duration_ms = None
        if te.completed_at and te.started_at:
            duration_ms = max(0.0, (te.completed_at - te.started_at).total_seconds() * 1000.0)

        # Sanitize result preview (redacting sensitive keys)
        res_preview = None
        if te.result:
            try:
                import json
                from app.core.mcp.security import CredentialStore
                res_obj = json.loads(te.result)
                if isinstance(res_obj, dict):
                    redacted = CredentialStore.redact_sensitive_dict(res_obj)
                    res_preview = json.dumps(redacted)
                else:
                    res_preview = str(te.result)[:200]
            except Exception:
                res_preview = str(te.result)[:200]

        history_items.append(
            MCPExecutionHistoryItem(
                id=str(te.id),
                execution_id=str(te.execution_id),
                tool_id=te.tool_id,
                tool_name=cap_map.get(te.tool_id, te.tool_id),
                status=te.status,
                started_at=te.started_at.isoformat() if te.started_at else "",
                completed_at=te.completed_at.isoformat() if te.completed_at else None,
                duration_ms=duration_ms,
                retry_count=te.retry_count,
                error=te.error,
                result_preview=res_preview
            )
        )

    return MCPExecutionHistoryResponse(
        executions=history_items,
        total=total
    )



