from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, workspaces, organizations, ai, agent, documents, rag, knowledge_graph, mcp, workflows, platform, admin, teams, permissions, projects, websockets, comments, notifications

api_router = APIRouter()

# Mount all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(organizations.router)
api_router.include_router(ai.router)
api_router.include_router(agent.router)
api_router.include_router(documents.router)
api_router.include_router(rag.router)
api_router.include_router(knowledge_graph.router)
api_router.include_router(mcp.router)
api_router.include_router(workflows.router)
api_router.include_router(platform.router)
api_router.include_router(admin.router)



api_router.include_router(teams.router)
api_router.include_router(permissions.router)
api_router.include_router(projects.router)
api_router.include_router(websockets.router)
api_router.include_router(comments.router)
api_router.include_router(notifications.router)
