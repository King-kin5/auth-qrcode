from functools import wraps
from typing import Any, List, Optional
from fastapi import HTTPException
import ipaddress

def has_permission(user: Any, permission: str) -> bool:
    if not user:
        return False
    return user.has_full_access

def require_admin_permissions(permissions: Optional[List[str]] = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user or not current_user.is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Admin privileges required"
                )
            
            if permissions and not all(
                has_permission(current_user, perm) for perm in permissions
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient admin permissions"
                )
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def is_whitelisted_ip(ip: str, allowed_ips: List[str] = None) -> bool:
    if not allowed_ips:
        return True
        
    try:
        client_ip = ipaddress.ip_address(ip)
        return any(
            client_ip in ipaddress.ip_network(allowed)
            for allowed in allowed_ips
        )
    except ValueError:
        return False

async def admin_required(current_user):
    """Check if the current user has admin privileges"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return current_user