from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from backend.admin.service import AdminService
from backend.database.config import get_db
from backend.admin.model import Admin
from backend.security.permissions import admin_required
from backend.security.token import create_access_token, verify_access_token
from backend.security.config import settings
from backend.admin.schema import AdminCreate, AdminLogin, AdminResponse, Token

router = APIRouter()

# OAuth2 password flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")

# Dependency to get current admin user
async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Admin:
    payload = verify_access_token(token)
    admin_id = payload.get("sub")
    
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin_service = AdminService(db)
    admin = admin_service.get_admin_by_id(admin_id)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return admin

# Routes


@router.post("/create", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(admin_required)
) -> Any:
    """Create a new admin (requires admin privileges)"""
    # Check if current admin has full access
    if not current_admin.has_full_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create admin"
        )
    
    admin_service = AdminService(db)
    new_admin = admin_service.create_admin(
        email=admin_data.email,
        password=admin_data.password,
        full_name=admin_data.full_name,
        created_by=current_admin.id
    )
    
    return new_admin

@router.get("/me", response_model=AdminResponse)
async def get_current_admin_info(
    current_admin: Admin = Depends(get_current_admin)
) -> Any:
    """Get current admin user information"""
    return current_admin

@router.post("/login", response_model=Token)
async def login(
    form_data: AdminLogin,
    db: Session = Depends(get_db)
) -> Any:
    """Admin login endpoint"""
    admin_service = AdminService(db)
    return await admin_service.login_admin(
        email=form_data.email,
        password=form_data.password
    )