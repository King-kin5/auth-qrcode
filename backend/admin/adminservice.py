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
        Register a new student - only accessible by admin users.
        
        Args:
            data: Student data dictionary.
            admin_user: The admin user performing the registration.
            
        Returns:
            Student: The created student object.
            
        Raises:
            HTTPException: If admin permissions are insufficient or operation fails.
        """
        # Verify admin privileges
        if not admin_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
            
        # Verify active admin status
        if not admin_user.has_full_access:
            raise HTTPException(status_code=403, detail="Admin account must be active")
        
        try:
            # Check if a student with the exact same name already exists
            existing_student = self.db.query(Student).filter(
                Student.Matric == data['Matric']
            ).first()
            
            if existing_student:
                raise HTTPException(
                    status_code=400,
                    detail=f"Student '{data['Matric']}' is already registered"
                )
            
            # Create a new student
            new_student = Student(
                Matric=data['Matric'],
                Firstname=data['Firstname'],
                Lastname=data['Lastname'],
                gender=data['gender'],
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
                    "Matric":new_student.Matric,
                    "Firstname":new_student.Firstname,
                    "Lastname":new_student.Lastname,
                    "gender":new_student.gender,
                    "course": new_student.course,
                    "level": new_student.level,
                    "section": new_student.section,
                    "registered_at": datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Admin {admin_user.email} registered student: {new_student.Firstname,new_student.Lastname}")
            return new_student
            
        except HTTPException:
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
        """Get all registered students."""
        return self.db.query(Student).all()
    
    def get_student_by_id(self, student_matric: str) -> Optional[Student]:
        """Get a student by ID."""
        student = self.db.query(Student).filter(Student.Matric == student_matric).first()
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
        """Create an audit log entry for admin actions."""
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
            # Do not rollback the main transaction if audit logging fails.

    def delete_student(self, student_matric: str, admin_user: Admin) -> bool:
        """
        Delete a student record.
        
        Args:
            student_id: ID of the student to delete.
            admin_user: Admin performing the deletion.
            
        Returns:
            bool: True if deletion was successful.
            
        Raises:
            HTTPException: If the student is not found or the operation fails.
        """
        # Verify admin privileges
        if not admin_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
            
        # Find the student
        student = self.db.query(Student).filter(Student.Matric == student_matric).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
            
        try:
            # Store student info for audit log
            student_matric = student.Matric
            
            # Delete the student
            self.db.delete(student)
            self.db.commit()
            
            # Create audit log entry
            self._create_audit_log(
                admin_user.id,
                "STUDENT_DELETED",
                "STUDENT",
                str(student_matric),
                {
                    "matric": student_matric,
                    "deleted_at": datetime.now().isoformat(),
                    "deleted_by": admin_user.email
                }
            )
            
            self.logger.info(f"Admin {admin_user.email} deleted student  {student_matric}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error deleting student: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error during deletion")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error deleting student: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred during deletion")

    def update_student(self, student_matric: str, data: Dict[str, Any], admin_user: Admin) -> Student:
        """
        Update a student record.
        
        Args:
            student_id: ID of the student to update.
            data: Dictionary with fields to update.
            admin_user: Admin performing the update.
            
        Returns:
            Student: The updated student object.
            
        Raises:
            HTTPException: If the student is not found or the operation fails.
        """
        # Verify admin privileges
        if not admin_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
            
        # Find the student
        student = self.db.query(Student).filter(Student.Matric == student_matric).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
            
        try:
            # Store original data for audit log
            original_data = {
                "Matric":student.Matric,
                "Firstname":student.Firstname,
                "Lastname":student.Lastname,
                "gender":student.gender,
                "course": student.course,
                "level": student.level,
                "section": student.section
            }
            
            # Update allowed fields
            for field, value in data.items():
                if field in ["Matric","Firstname","Lastname","gender", "course", "level", "section", "qr_code"]:
                    setattr(student, field, value)
                    
            self.db.commit()
            self.db.refresh(student)
            
            # Create audit log entry
            self._create_audit_log(
                admin_user.id,
                "STUDENT_UPDATED",
                "STUDENT",
                str(student_matric),
                {
                    "original_data": original_data,
                    "updated_data": data,
                    "updated_at": datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Admin {admin_user.email} updated student  {student_matric}")
            return student
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error updating student: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error during update")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error updating student: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred during update")
