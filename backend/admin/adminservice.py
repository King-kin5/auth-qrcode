from datetime import datetime
import logging
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

from backend.admin.model import Admin, AdminAuditLog
from backend.security.exceptions import SecurityError
from backend.student.model import Student

logger = logging.getLogger(__name__)

class AdminStudentService:
    """Service for admin operations on student records"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def register_student(self, data: Dict[str, Any], admin_user: Admin) -> Student:
        """
        Register a new student - only accessible by admin users
        
        Args:
            data: Student data dictionary
            admin_user: The admin user performing the registration
            
        Returns:
            Student: The created student object
            
        Raises:
            HTTPException: If admin permissions are insufficient or operation fails
        """
        # Verify admin privileges
        if not admin_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
            
        # Verify active admin status
        if not admin_user.has_full_access:
            raise HTTPException(status_code=403, detail="Admin account must be active")
        
        try:
            # Check if student with exact same name
            existing_student = self.db.query(Student).filter(
                Student.name == data['name']
            ).first()
            
            if existing_student:
                raise HTTPException(
                    status_code=400,
                    detail=f"Student '{data['name']}' is already registered  "
                )
            
            # Create new student with auto-incrementing ID
            new_student = Student(
                name=data['name'],
                course=data['course'],
                level=data['level'],
                section=data['section'],
                qr_code=data.get('qr_code', '')
            )
            
            self.db.add(new_student)
            self.db.commit()
            self.db.refresh(new_student)
            
            # Create audit log entry for the registration
            self._create_audit_log(
                admin_user.id,
                "STUDENT_REGISTERED",
                "STUDENT",
                str(new_student.id),
                {
                    "name": new_student.name,
                    "course": new_student.course,
                    "level": new_student.level,
                    "section": new_student.section,
                    "registered_at": datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Admin {admin_user.email} registered student: {new_student.name}")
            return new_student
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error registering student: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error during registration")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error registering student: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred during registration")

    def get_all_students(self) -> List[Student]:
        """Get all registered students"""
        return self.db.query(Student).all()
    
    def get_student_by_id(self, student_id: int) -> Optional[Student]:
        """Get student by ID"""
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student
    
    def _create_audit_log(
        self,
        admin_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict
    ) -> None:
        """Create an audit log entry for admin actions"""
        try:
            audit_log = AdminAuditLog(
                admin_id=admin_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                created_at=datetime.now()
            )
            self.db.add(audit_log)
            self.db.commit()
            self.logger.info(f"Created audit log for action: {action}")
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create audit log: {str(e)}")
            # Don't rollback the main transaction if audit logging fails