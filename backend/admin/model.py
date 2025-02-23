from datetime import datetime
import uuid

from sqlalchemy import JSON, UUID, Column, DateTime, ForeignKey, Integer, String, Boolean, Enum as SQLAEnum
from backend.student.entities import Status, Tier
from sqlalchemy.orm import relationship
from backend.database.config import Base

class AdminUserMixin:
    """Mixin to handle admin-specific functionality"""
    @property
    def is_admin(self) -> bool:
        """Check if user has admin tier"""
        return self.tier == Tier.ADMIN
        
    @property 
    def has_full_access(self) -> bool:
        """Check if admin has full unrestricted access"""
        return self.is_admin and self.status == Status.ACTIVE

class Admin(Base, AdminUserMixin):
    """User model representing application users with admin privileges."""
    __tablename__ = "admin"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    tier = Column(SQLAEnum(Tier), default=Tier.ADMIN)
    status = Column(SQLAEnum(Status), default=Status.ACTIVE)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Define a one-to-many relationship with AdminAuditLog.
    audit_logs = relationship("AdminAuditLog", back_populates="admin", cascade="all, delete-orphan")

class AdminAuditLog(Base):
    """Model for tracking admin actions in the system."""
    __tablename__ = "admin_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(UUID(as_uuid=True), ForeignKey('admin.id'), nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.now)

    # Define the many-to-one relationship with Admin.
    admin = relationship("Admin", back_populates="audit_logs")