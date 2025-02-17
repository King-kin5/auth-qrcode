from datetime import datetime
import logging
import re
from typing import Optional
from sqlalchemy import Tuple
from sqlalchemy.exc import SQLAlchemyError

from backend.database.config import SessionLocal
from backend.security.exceptions import SecurityError
from backend.security.password import verify_password,hash_password
from backend.security.config import settings

logger = logging.getLogger(__name__)

class PasswordValidator:
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validates password against security requirements
        Returns: (is_valid: bool, error_message: str)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
            
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
            
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
            
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"
            
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
            
        # Check for common passwords (could be expanded)
        common_passwords = {"password123", "admin123", "12345678"}
        if password.lower() in common_passwords:
            return False, "Password is too common"
            
        return True, ""

    @staticmethod
    def check_password_history(new_password: str, password_history: list) -> bool:
        """
        Checks if password was used recently
        Returns: bool indicating if password is acceptable
        """
        return not any(
            verify_password(new_password, old_password) 
            for old_password in password_history
        )

def create_admin_audit_log(
    db_session,
    admin_id: str,
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
        db_session.add(audit_log)
        db_session.commit()
        logger.info(f"Created audit log for action: {action}")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create audit log: {e}")
        db_session.rollback()
        raise

def create_initial_admin() -> Optional[User]:
    """Create initial admin user if it doesn't exist"""
    db = SessionLocal()
    try:
        # Get the raw password string from SecretStr
        admin_password = settings.INITIAL_ADMIN_PASSWORD.get_secret_value()
        
        # Validate password complexity
        is_valid, error_msg = PasswordValidator.validate_password(admin_password)
        if not is_valid:
            raise SecurityError(f"Invalid initial admin password: {error_msg}")

        # Check if admin exists
        admin_email = settings.INITIAL_ADMIN_EMAIL
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        
        if not existing_admin:
            admin_user = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),  # Use the raw password string here too
                full_name=settings.INITIAL_ADMIN_NAME,
                tier=UserTier.ADMIN,
                status=UserStatus.ACTIVE,
                is_active=True,
                requires_password_change=True,  # Force password change on first login
                created_at=datetime.now()
            )
            
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Create audit log for admin creation
            create_admin_audit_log(
                db,
                admin_user.id,
                "ADMIN_CREATED",
                "USER",
                str(admin_user.id),
                {
                    "email": admin_email,
                    "created_at": admin_user.created_at.isoformat(),
                    "requires_password_change": True
                }
            )
            
            logger.info(f"Created initial admin user: {admin_email}")
            return admin_user
        else:
            logger.info("Admin user already exists")
            return existing_admin
            
    except SecurityError as e:
        logger.error(f"Security error creating admin: {e}")
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error creating admin: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating admin: {e}")
        raise
    finally:
        db.close()

def init_data():
    """Initialize all required initial data"""
    try:
        admin_user = create_initial_admin()
        if admin_user:
            logger.info("Data initialization completed successfully")
        # Add other initialization functions here
        
    except Exception as e:
        logger.error(f"Error in data")