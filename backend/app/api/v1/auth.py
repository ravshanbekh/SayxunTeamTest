"""
Authentication endpoints - admin login and registration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.schemas.admin import AdminCreate, AdminLogin, AdminResponse, Token
from app.services.auth_service import create_admin, authenticate_admin, create_admin_token
from app.api.deps import get_current_admin
from app.models.admin import AdminUser


router = APIRouter()


@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(
    admin_data: AdminCreate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new admin user. Requires admin authentication.
    """
    try:
        admin = await create_admin(db, admin_data)
        return admin
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )


@router.post("/login", response_model=Token)
async def login_admin(
    login_data: AdminLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Admin login - returns JWT token.
    """
    admin = await authenticate_admin(db, login_data)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_admin_token(admin)
    return token
