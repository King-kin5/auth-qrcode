from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.admin.model import Admin
from backend.database.config import get_db
from backend.security.token import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/admin/login")

async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Admin:
    """
    Dependency to get current authenticated admin user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify and decode JWT token
        payload = verify_access_token(token)
        admin_id = payload.get("sub")
        if admin_id is None:
            raise credentials_exception
            
        # Get admin from database
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if admin is None:
            raise credentials_exception
            
        return admin
    except JWTError:
        raise credentials_exception