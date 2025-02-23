from datetime import datetime
import logging
import re
from typing import Optional, Tuple  # Import Tuple from typing

from backend.database.config import SessionLocal
from backend.security.exceptions import SecurityError
from backend.security.password import verify_password, hash_password
from backend.security.config import settings

logger = logging.getLogger(__name__)

class PasswordValidator:
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validates password against security requirements.
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
