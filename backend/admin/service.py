from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.admin.model import Admin, AdminAuditLog
from backend.database.config import SessionLocal
from backend.database.data import PasswordValidator
from backend.student.entities import Status, Tier
from backend.security.password import hash_password, verify_password
from backend.security.exceptions import SecurityError, AuthenticationException
from backend.security.config import settings
from backend.security.token import create_access_token


class AdminService:
    """Service for admin user management and initialization."""

    def __init__(self, db: Optional[Session] = None):
        # Use provided session or create a new one
        self.db = db or SessionLocal()
        self.logger = logging.getLogger(__name__)

    def get_admin_by_id(self, admin_id: str) -> Optional[Admin]:
        """Get admin by ID."""
        return self.db.query(Admin).filter(Admin.id == admin_id).first()

    def get_admin_by_email(self, email: str) -> Optional[Admin]:
        """Get admin by email."""
        return self.db.query(Admin).filter(Admin.email == email).first()

    def authenticate_admin(self, email: str, password: str) -> Optional[Admin]:
        """Authenticate admin with email and password."""
        admin = self.get_admin_by_email(email)
        if not admin:
            self.logger.warning(f"Failed login attempt for non-existent admin: {email}")
            return None

        if not verify_password(password, admin.hashed_password):
            self.logger.warning(f"Failed login attempt for admin: {email}")
            return None

        return admin

    async def login_admin(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login admin and generate access token.
        
        Args:
            email: Admin email
            password: Admin password
            
        Returns:
            Dict containing access token and token type
            
        Raises:
            AuthenticationException: If login fails
        """
        try:
            # Authenticate admin
            admin = self.authenticate_admin(email, password)
            if not admin:
                raise AuthenticationException("Incorrect email or password")

            # Check if admin is active
            if not admin.is_active:
                raise AuthenticationException("Admin account is inactive")

            # Check admin permissions
            if not admin.has_full_access:
                raise AuthenticationException("Insufficient admin privileges")

            # Update last login timestamp
            admin.last_login = datetime.now()
            self.db.commit()

            # Generate access token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                user_id=admin.id,
                expires_delta=access_token_expires
            )

            # Create audit log for successful login
            self.create_admin_audit_log(
                admin_id=str(admin.id),
                action="LOGIN",
                entity_type="ADMIN",
                entity_id=str(admin.id),
                details={
                    "email": admin.email,
                    "login_time": datetime.now().isoformat()
                }
            )

            return {
                "access_token": access_token,
                "token_type": "bearer"
            }

        except AuthenticationException:
            raise
        except Exception as e:
            self.logger.error(f"Login error: {str(e)}")
            raise AuthenticationException("Login failed")

    def create_admin_audit_log(
        self,
        admin_id: str,
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
            self.logger.error(f"Failed to create audit log: {e}")
            self.db.rollback()
            raise

    def create_admin(self) -> Optional[Admin]:
        """Create initial admin user if it doesn't exist."""
        try:
            # Get the raw password string from SecretStr and validate complexity
            admin_password = settings.INITIAL_ADMIN_PASSWORD.get_secret_value()
            is_valid, error_msg = PasswordValidator.validate_password(admin_password)
            if not is_valid:
                raise SecurityError(f"Invalid initial admin password: {error_msg}")

            admin_email = settings.INITIAL_ADMIN_EMAIL
            existing_admin = self.db.query(Admin).filter(Admin.email == admin_email).first()

            if not existing_admin:
                admin_user = Admin(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    full_name=settings.INITIAL_ADMIN_NAME,
                    tier=Tier.ADMIN,
                    status=Status.ACTIVE,
                    is_active=True,
                )

                self.db.add(admin_user)
                self.db.commit()
                self.db.refresh(admin_user)

                # Create audit log for admin creation
                self.create_admin_audit_log(
                    admin_id=admin_user.id,
                    action="ADMIN_CREATED",
                    entity_type="USER",
                    entity_id=str(admin_user.id),
                    details={
                        "email": admin_email,
                        "requires_password_change": True
                    }
                )

                self.logger.info(f"Created initial admin user: {admin_email}")
                return admin_user
            else:
                self.logger.info("Admin user already exists")
                return existing_admin

        except SecurityError as e:
            self.logger.error(f"Security error creating admin: {e}")
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating admin: {e}")
            self.db.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error creating admin: {e}")
            raise

    def init_data(self) -> None:
        """Initialize all required initial data."""
        try:
            admin_user = self.create_admin()
            if admin_user:
                self.logger.info("Data initialization completed successfully")
            # Add other initialization functions here if needed.
        except Exception as e:
            self.logger.error(f"Error in data initialization: {e}")
            raise