from datetime import datetime, timedelta
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status,Path
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from backend.admin.adminservice import AdminStudentService
from backend.admin.service import AdminService
from backend.admin.model import Admin
from backend.admin.schema import AdminCreate, AdminLogin, AdminResponse, StudentCreate, StudentResponse, Token
from backend.database.config import get_db
from backend.student.model import Student

from backend.security.permissions import admin_required
from backend.security.token import create_access_token, verify_access_token
from backend.security.config import settings


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

# Admin Endpoints

@router.post("/create", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(admin_required)
) -> Any:
    """Create a new admin (requires admin privileges)"""
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
async def get_me(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_admin)
):
    """
    Retrieve current admin user information.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Admin account is inactive")
    return current_user

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

# Student Endpoints

@router.post("/register-student", response_model=StudentResponse)
async def register_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Register a new student (admin only).
    """
    service = AdminStudentService(db)
    try:
        student = service.register_student(student_data.dict(), current_admin)
        return student
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register student: {str(e)}"
        )

@router.get("/students", response_model=List[StudentResponse])
async def get_all_students(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get all registered students (admin only).
    """
    service = AdminStudentService(db)
    return service.get_all_students()

@router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get student by ID (admin only).
    """
    service = AdminStudentService(db)
    student = service.get_student_by_id(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    return student


@router.get("/students/search", response_model=List[StudentResponse])
async def search_students(
    query: str,
    search_name: bool = True,
    search_course: bool = True,
    search_level: bool = True,
    search_section: bool = True,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Search students by various criteria.
    """
    if not any([search_name, search_course, search_level, search_section]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one search field must be selected"
        )
    from sqlalchemy import or_
    student_query = db.query(Student)
    filters = []
    if search_name:
        filters.append(Student.name.ilike(f"%{query}%"))
    if search_course:
        filters.append(Student.course.ilike(f"%{query}%"))
    if search_level:
        filters.append(Student.level.ilike(f"%{query}%"))
    if search_section:
        filters.append(Student.section.ilike(f"%{query}%"))
    student_query = student_query.filter(or_(*filters))
    return student_query.all()
@router.get("/students/{student_matric:path}", response_model=StudentResponse)
async def get_student(
    student_matric: str = Path(..., description="Student matric number that may contain slashes"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get student by matric number (admin only).
    Path parameter supports matric numbers containing slashes.
    """
    service = AdminStudentService(db)
    student = service.get_student_by_id(student_matric)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    return student

@router.delete("/students/{student_matric:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_matric: str = Path(..., description="Student matric number that may contain slashes"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Delete a student by matric number (admin only).
    Path parameter supports matric numbers containing slashes.
    """
    service = AdminStudentService(db)
    try:
        result = service.delete_student(student_matric, current_admin)
        if result:
            return
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete student."
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete student: {str(e)}"
        )
    
    