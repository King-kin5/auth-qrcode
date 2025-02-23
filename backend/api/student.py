from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from backend.database.config import get_db
from backend.admin.model import Admin
from backend.admin.dependencies import get_current_admin
from backend.admin.adminservice import AdminStudentService
from backend.admin.schema import StudentCreate, StudentResponse

router = APIRouter()

@router.post(
    "/register",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    description="Register a new student (Admin only)"
)
async def register_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Register a new student.
    Only accessible by authenticated admin users with full access privileges.
    """
    student_service = AdminStudentService(db)
    
    # Convert Pydantic model to dict
    student_data = student.dict(exclude_unset=True)
    
    # Register student through service
    new_student = student_service.register_student(
        data=student_data,
        admin_user=current_admin
    )
    
    return new_student

@router.get(
    "/",
    response_model=List[StudentResponse],
    description="Get all registered students (Admin only)"
)
async def get_all_students(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Retrieve all registered students.
    Only accessible by authenticated admin users.
    """
    student_service = AdminStudentService(db)
    return student_service.get_all_students()

@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    description="Get student by ID (Admin only)"
)
async def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Retrieve a specific student by ID.
    Only accessible by authenticated admin users.
    """
    student_service = AdminStudentService(db)
    return student_service.get_student_by_id(student_id)