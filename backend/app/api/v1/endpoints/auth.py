from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import redis

from app.database.session import get_db
from app.database.redis import get_redis
from app.schemas.user import UserCreate, UserResponse
from app.schemas.token import Token
from app.services.auth import AuthService
from app.api.dependencies import get_current_user, RoleChecker
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    """
    Registers a new user account with specified system roles.
    """
    auth_service = AuthService(db, redis_client)
    return auth_service.register_user(payload)

@router.post("/login", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Verifies credentials and returns access token + sets HTTP-Only refresh cookie.
    """
    auth_service = AuthService(db, redis_client)
    result = auth_service.login_user(form_data.username, form_data.password)
    
    # Set the refresh token as a secure, HTTP-Only cookie
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=False,  # Set to True in production with TLS
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return result

@router.post("/refresh", response_model=Token)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Evaluates HTTP-Only cookies to trigger token rotation (RTR).
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token cookie missing."
        )
        
    auth_service = AuthService(db, redis_client)
    result = auth_service.rotate_tokens(refresh_token)
    
    # Set the new rotated refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )
    
    return result

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Invalidates current session refresh tokens.
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        auth_service = AuthService(db, redis_client)
        auth_service.logout_user(refresh_token)
        
    response.delete_cookie("refresh_token")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns profile information of the currently authenticated active user.
    """
    return current_user

@router.get("/admin-only", response_model=UserResponse)
def get_admin_data(current_user: User = Depends(RoleChecker(["Admin", "Super Admin"]))):
    """
    Secured demonstration endpoint evaluating Admin RBAC configurations.
    """
    return current_user
