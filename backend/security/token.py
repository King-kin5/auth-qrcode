# Configure logging
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional

import jwt
from backend.security.config import settings
from backend.security.exceptions import AuthenticationException


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    SECRET_KEY = settings.SECRET_KEY
    ALGORITHM = settings.ALGORITHM
    
    if expires_delta is None:
        expires_delta = timedelta(days=1)
    
    to_encode = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + expires_delta
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Dict[str, Any]:
    try:
        logger.info(f"Attempting to verify token: {token[:10]}...")
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        logger.info("Token successfully decoded")
        return payload
    except jwt.exceptions.ExpiredSignatureError as e:
        logger.error(f"Token expired: {e}")
        raise AuthenticationException("Token has expired")
    except jwt.exceptions.PyJWTError as e:  # Base exception class for all JWT errors
        logger.error(f"JWT Error during token verification: {e}")
        logger.error(f"Token details - Secret Key Length: {len(settings.SECRET_KEY)}, Algorithm: {settings.ALGORITHM}")
        raise AuthenticationException("Could not validate credentials")

def create_password_reset_jwt(user_id: int) -> str:
    SECRET_KEY = settings.SECRET_KEY
    ALGORITHM = settings.ALGORITHM
    expires_delta = timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE)
    
    to_encode = {
        "sub": "password_reset",
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + expires_delta
    }
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password_reset_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=settings.ALGORITHM
        )
        
        if payload.get('sub') != 'password_reset':
            raise AuthenticationException("Invalid token type")
        
        return payload
    except jwt.JWTError:
        raise AuthenticationException("Invalid or expired reset token")


