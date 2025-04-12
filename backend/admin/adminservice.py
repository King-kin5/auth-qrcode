import base64
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

from backend.admin.model import Admin, AdminAuditLog
from backend.student.model import Student

logger = logging.getLogger(__name__)

def process_image_data(base64_data: str) -> str:
    """
    Validate and process base64-encoded image data for storage in the database.
    The input should be a string that may include a header (e.g., "data:image/jpeg;base64,...").

    Args:
        base64_data (str): The base64-encoded image data.

    Returns:
        str: The validated base64 image data.

    Raises:
        ValueError: If the image data is not valid base64.
    """
    # Return empty string for None or empty input
    if not base64_data:
        return ""
        
    # Optionally split header and encoded parts
    if ',' in base64_data:
        header, encoded = base64_data.split(',', 1)
        # Validate the header format
        if not header.startswith('data:image/') or not header.endswith(';base64'):
            raise ValueError("Invalid image data format. Must be a valid image data URL.")
    else:
        header, encoded = '', base64_data

    # Attempt to decode to validate that it's proper base64 data
    try:
        decoded_data = base64.b64decode(encoded)
        # Validate that we have actual image data of reasonable size
        if len(decoded_data) < 10:  # Extremely small data is suspicious
            raise ValueError("Image data too small to be valid")
        if len(decoded_data) > 10 * 1024 * 1024:  # Limit to 10MB
            raise ValueError("Image data exceeds maximum size of 10MB")
        
        # Return the original data with validation passed
        return base64_data
    except Exception as e:
        raise ValueError(f"Invalid base64 image data: {str(e)}")

def validate_student_data(data: Dict[str, Any]) -> None:
    """
    Validate student data to ensure all required fields are present and valid.
    
    Args:
        data: Student data dictionary
        
    Raises:
        ValueError: If any validation fails
    """
    required_fields = ['Matric', 'Firstname', 'Lastname', 'gender', 'course', 'level', 'section']
    
    # Check for required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate specific fields
    if not isinstance(data['level'], int) and not data['level'].isdigit():
        raise ValueError("Level must be a number")
        
    # Validate gender
    if data['gender'] not in ['M', 'F', 'Male', 'Female', 'Other']:
        raise ValueError("Gender must be one of: M, F, Male, Female, Other")

class AdminStudentService:
    """Service for admin operations on student records."""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def register_student(self, data: Dict[str, Any], admin_user: Admin) -> Student:
        """
        Register a new student, including processing the image to store it as a base64 string.

        Args:
            data: Student data dictionary.
            admin_user: The admin user performing the registration.

        Returns:
            Student: The created student object.

        Raises:
            HTTPException: When there is an error with privileges or during the registration process.
        """
        # Validate admin permissions outside transaction
        if not admin_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        if not admin_user.has_full_access:
            raise HTTPException(status_code=403, detail="Admin account must be active")
        
        # Validate input data
        try:
            validate_student_data(data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Start explicit transaction
        try:
            # Acquire row lock when checking for duplicate to prevent race conditions
            existing_student = self.db.query(Student).filter(
                Student.Matric == data['Matric']
            ).with_for_update().first()
            
            if existing_student:
                raise HTTPException(
                    status_code=400,
                    detail=f"Student '{data['Matric']}' is already registered"
                )
            
            # Process image data if provided
            image_data = ""
            if "image" in data and data["image"]:
                try:
                    image_data = process_image_data(data["image"])
                except ValueError as e:
                    # Explicitly raise an HTTP exception with the validation error
                    raise HTTPException(status_code=400, detail=str(e))
            
            # Create the new student record
            new_student = Student(
                Matric=data['Matric'],
                Firstname=data['Firstname'],
                Lastname=data['Lastname'],
                gender=data['gender'],
                course=data['course'],
                level=data['level'],
                section=data['section'],
                image=image_data,
                qr_code=data.get('qr_code', '')
            )
            
            self.db.add(new_student)
            self.db.flush()  # Flush to get the ID but don't commit yet
            
            # Create audit log within the same transaction
            audit_log = self._create_audit_log_entry(
                admin_user.id,
                "STUDENT_REGISTERED",
                "STUDENT",
                str(new_student.id),
                {
                    "Matric": new_student.Matric,
                    "Firstname": new_student.Firstname,
                    "Lastname": new_student.Lastname,
                    "gender": new_student.gender,
                    "course": new_student.course,
                    "level": new_student.level,
                    "section": new_student.section,
                    "image_provided": bool(new_student.image),
                    "registered_at": datetime.now().isoformat()
                }
            )
            self.db.add(audit_log)
            
            # Now commit everything together
            self.db.commit()
            self.db.refresh(new_student)
            
            self.logger.info(f"Admin {admin_user.email} registered student: {new_student.Firstname} {new_student.Lastname}")
            return new_student
            
        except HTTPException:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error during registration: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error during registration")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error during registration: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred during registration")

    def get_all_students(self) -> List[Student]:
        """Retrieve all registered students."""
        return self.db.query(Student).all()
    
    def get_student_by_id(self, student_matric: str) -> Optional[Student]:
        """Retrieve a single student using the matric number."""
        student = self.db.query(Student).filter(Student.Matric == student_matric).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student
    
    def _create_audit_log_entry(
        self,
        admin_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict
    ) -> AdminAuditLog:
        """
        Create an audit log entry object (but don't commit it).
        This should be committed in the same transaction as the main operation.
        
        Returns the created audit log object for addition to the session.
        """
        return AdminAuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            created_at=datetime.now()
        )

    def delete_student(self, student_matric: str, admin_user: Admin) -> bool:
        """
        Delete a student record.

        Args:
            student_matric: The student's matric number.
            admin_user: The admin performing the deletion.

        Returns:
            bool: True if deletion is successful.

        Raises:
            HTTPException: If deletion fails.
        """
        if not admin_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        try:
            # Start explicit transaction and use row locking
            student = self.db.query(Student).filter(
                Student.Matric == student_matric
            ).with_for_update().first()
            
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            
            matric = student.Matric
            student_id = str(student.id)
            
            # Create the audit log within the same transaction
            audit_log = self._create_audit_log_entry(
                admin_user.id,
                "STUDENT_DELETED",
                "STUDENT",
                student_id,
                {
                    "matric": matric,
                    "firstname": student.Firstname,
                    "lastname": student.Lastname,
                    "deleted_at": datetime.now().isoformat(),
                    "deleted_by": admin_user.email
                }
            )
            self.db.add(audit_log)
            
            # Delete the student
            self.db.delete(student)
            
            # Commit everything together
            self.db.commit()
            
            self.logger.info(f"Admin {admin_user.email} deleted student {matric}")
            return True
            
        except HTTPException:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error during deletion: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error during deletion")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error during deletion: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred during deletion")

    def update_student(self, student_matric: str, data: Dict[str, Any], admin_user: Admin) -> Student:
        """
        Update an existing student record, including reprocessing image data if necessary.

        Args:
            student_matric: The matric number of the student to update.
            data: A dictionary of fields to update.
            admin_user: The admin performing the update.

        Returns:
            Student: The updated student object.

        Raises:
            HTTPException: When the student is not found or an error occurs during the update.
        """
        if not admin_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Only validate fields that are being updated
        update_fields = {k: v for k, v in data.items() 
                        if k in ["Matric", "Firstname", "Lastname", "gender", "course", "level", "section", "image", "qr_code"]}
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        try:
            # Start explicit transaction and use row locking
            student = self.db.query(Student).filter(
                Student.Matric == student_matric
            ).with_for_update().first()
            
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            
            # Save original data for audit log
            original_data = {
                "Matric": student.Matric,
                "Firstname": student.Firstname,
                "Lastname": student.Lastname,
                "gender": student.gender,
                "course": student.course,
                "level": student.level,
                "section": student.section,
                "image_provided": bool(student.image)
            }
            
            # Process updated image data if provided
            if "image" in update_fields:
                try:
                    if update_fields["image"] == "":  # Empty string means remove image
                        update_fields["image"] = ""
                    else:
                        update_fields["image"] = process_image_data(update_fields["image"])
                except ValueError as e:
                    # Explicitly raise HTTP exception with the error message
                    raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")
            
            # Update the student with validated fields
            for field, value in update_fields.items():
                setattr(student, field, value)
            
            # Create audit log within the same transaction
            audit_data = {
                "original_data": original_data,
                "updated_data": {k: v if k != "image" else bool(v) for k, v in update_fields.items()},
                "updated_at": datetime.now().isoformat(),
                "updated_by": admin_user.email
            }
            
            audit_log = self._create_audit_log_entry(
                admin_user.id,
                "STUDENT_UPDATED",
                "STUDENT",
                str(student.id),
                audit_data
            )
            self.db.add(audit_log)
            
            # Commit everything together
            self.db.commit()
            self.db.refresh(student)
            
            self.logger.info(f"Admin {admin_user.email} updated student {student_matric}")
            return student
            
        except HTTPException:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error during update: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error during update")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error during update: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred during update")