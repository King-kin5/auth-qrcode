import time
import logging
import traceback
import re
import uuid
from fastapi import Request, HTTPException
from starlette.middleware.base import RequestResponseEndpoint, BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from backend.security.permissions import is_whitelisted_ip, has_permission
from backend.security.token import verify_access_token
from backend.admin.service import AdminService
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CustomMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            logger.error(f"Unhandled middleware error: {e}")
            logger.error(traceback.format_exc())
            # Fallback error response
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [(b'content-type', b'application/json')]
            })
            await send({
                'type': 'http.response.body',
                'body': b'{"detail": "Internal Server Error"}'
            })

async def logging_middleware(request: Request, call_next: RequestResponseEndpoint):
    start_time = time.time()
    
    try:
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(f"Response time: {process_time:.4f} seconds")
        
        return response
    except Exception as e:
        logger.error(f"Logging middleware error: {e}")
        raise

async def authentication_middleware(request: Request, call_next: RequestResponseEndpoint):
    """
    Middleware for authentication checks.
    Uses regex patterns to determine which paths should be excluded.
    """
    # Skip authentication for OPTIONS requests
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Define regex patterns for paths to exclude from authentication
    excluded_patterns = [
        # Auth endpoints
        re.compile(r"^/api/v1/auth/(login|signup|me|forgot-password|reset-password|google-login|refresh-token)$"),
        # Admin login endpoint
        re.compile(r"^/admin/login$"),
        re.compile(r"^/api/v1/admin/login$"),
        re.compile(r"^/api/v1/admin/create$"),
        # Public API endpoints
        re.compile(r"^/api/v1/student/public/info$"),
        # Documentation endpoints
        re.compile(r"^/(docs|redoc|openapi\.json)$"),
        # Health check and metrics
        re.compile(r"^/(health|metrics|status)$"),
        re.compile(r"^/admin(?!/login).*$"),
        # Static files
        re.compile(r"^/static/.*$"),
        # Public student verification
        re.compile(r"^/api/v1/student/verify/[^/]+$")
    ]
    
    path = request.url.path
    logger.debug(f"Checking path for exclusion: {path}")
    
    if any(pattern.match(path) for pattern in excluded_patterns):
        logger.info(f"Authentication skipped for path: {path}")
        return await call_next(request)
    
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.error(f"Authorization header missing for path: {path}")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate token (adjust this implementation to your auth system)
    try:
        token = auth_header.split(" ")[-1] if "Bearer" in auth_header else auth_header
        decoded_token = verify_access_token(token)
        if decoded_token is None:
            logger.error(f"Invalid or expired token for path: {path}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        request.state.user = decoded_token
    except HTTPException:
        raise  # Re-raise HTTPException
    except Exception as e:
        logger.error(f"Unexpected token validation error for path {path}: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Authentication middleware error: {e}")
        raise

async def admin_security_middleware(request: Request, call_next: RequestResponseEndpoint):
    """
    Additional security checks for admin routes
    Verifies admin permissions, IP whitelisting, and additional security headers
    """
    # Only apply to admin routes, but exclude the login endpoint
    admin_path_patterns = [
        re.compile(r"^/api/v1/admin(?!/login).*$"),
        re.compile(r"^/admin(?!/login).*$"),
        re.compile(r"^/admin(?!/(login|home)$).*"),
    ]
    
    is_admin_route = any(pattern.match(request.url.path) for pattern in admin_path_patterns)
    
    if is_admin_route:
        try:
            # Verify admin IP whitelist
            client_ip = request.client.host if request.client else 'unknown'
            admin_ip_whitelist = getattr(request.app.state, 'admin_ip_whitelist', [])
            
            if not is_whitelisted_ip(client_ip, admin_ip_whitelist):
                logger.warning(f"Admin access attempt from non-whitelisted IP: {client_ip}")
                raise HTTPException(status_code=403, detail="Admin access denied: IP not allowed")
            
            # Check for required security headers for sensitive admin operations
            sensitive_admin_operations = [
                re.compile(r"^/api/v1/admin/(users|permissions|settings)/.*$"),
                re.compile(r"^/admin/(system|security)/.*$")
            ]
            
            is_sensitive_operation = any(
                pattern.match(request.url.path) 
                for pattern in sensitive_admin_operations
            )
            
            if is_sensitive_operation and not all(
                header in request.headers 
                for header in ['X-Admin-Token', 'X-Request-ID']
            ):
                raise HTTPException(
                    status_code=400, 
                    detail="Missing required security headers for admin operation"
                )
            
            # Verify admin permission level if user is authenticated
            if hasattr(request.state, 'user') and request.state.user:
                user_id = request.state.user.get('sub')
                if user_id:
                    # Get DB session from request state
                    db = request.app.state.db
                    admin_service = AdminService(db)
                    
                    admin_user = admin_service.get_admin_by_id(uuid.UUID(user_id))
                    if not admin_user or not admin_user.is_admin:
                        logger.warning(f"Non-admin user {user_id} attempted to access admin route")
                        raise HTTPException(
                            status_code=403,
                            detail="Admin privileges required for this operation"
                        )
                    
                    # Set the actual admin user model in request state for convenience
                    request.state.admin_user = admin_user
                    
                    # For extra security, check if admin account is active
                    if not admin_user.is_active:
                        logger.warning(f"Inactive admin {user_id} attempted to access admin route")
                        raise HTTPException(
                            status_code=403, 
                            detail="Admin account is inactive"
                        )
                    
                    # Log admin access
                    logger.info(f"Admin access: {admin_user.email} - {request.url.path}")
            else:
                # If we reach here on an admin route and no user is authenticated, deny access
                raise HTTPException(status_code=401, detail="Authentication required for admin access")
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin security middleware error: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Internal security error")
    
    return await call_next(request)


class PasswordChangeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip middleware for these endpoints
        excluded_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/change-password",
            "/api/v1/auth/reset-password",
            "/admin/login",
            "/api/v1/admin/login",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        ]
        
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return await call_next(request)

        # Check if user needs to change password
        user = getattr(request.state, "user", None)
        admin_user = None
        
        if user and 'sub' in user:
            try:
                # Get DB session from request state
                db = request.app.state.db
                admin_service = AdminService(db)
                
                admin_user = admin_service.get_admin_by_id(uuid.UUID(user['sub']))
                if admin_user and admin_user.requires_password_change:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "message": "Password change required",
                            "code": "PASSWORD_CHANGE_REQUIRED"
                        }
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Password check middleware error: {str(e)}")
        
        return await call_next(request)