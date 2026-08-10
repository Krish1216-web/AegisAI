from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, workspaces, organizations, ai

api_router = APIRouter()

# Mount all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(organizations.router)
api_router.include_router(ai.router)
