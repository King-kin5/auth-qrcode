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
        re.compile(r"^/admin/login$"),
        #re.compile(r"^/admin/dashboard$"),
        # Static files
        re.compile(r"^/static/.*$"),
        re.compile(r"^/favicon\.ico$"),
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

# Update the admin_security_middleware function in middleware.py
async def admin_security_middleware(request: Request, call_next: RequestResponseEndpoint):
    """
    Additional security checks for admin routes
    Verifies admin permissions, IP whitelisting, and additional security headers
    """
    # Static file and initial page load exclusions
    excluded_patterns = [
        re.compile(r"^/admin/login$"),
        re.compile(r"^/admin/dashboard$"),  # Allow initial dashboard page load
        re.compile(r"^/static/.*$"),
    ]
    
    # Check if path should be excluded
    if any(pattern.match(request.url.path) for pattern in excluded_patterns):
        return await call_next(request)
    
    # Admin API patterns that require authentication
    admin_api_patterns = [
        re.compile(r"^/api/v1/admin(?!/login).*$"),
    ]
    
    # Protected admin page patterns
    protected_admin_patterns = [
        re.compile(r"^/admin/.*$"),  # All other admin routes need auth
    ]
    
    is_admin_api = any(pattern.match(request.url.path) for pattern in admin_api_patterns)
    is_protected_admin = any(pattern.match(request.url.path) for pattern in protected_admin_patterns)
    
    if is_admin_api or is_protected_admin:
        try:
            # Verify admin permission level if user is authenticated
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authentication required for admin access")
            
            # Validate token
            token = auth_header.split(" ")[-1] if "Bearer" in auth_header else auth_header
            decoded_token = verify_access_token(token)
            if not decoded_token:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            
            # Check admin privileges using dependency-based approach
            if decoded_token.get('sub'):
                # Import here to avoid circular imports
                from backend.database.base import SessionLocal
                
                # Create a new session for this request
                db = SessionLocal()
                try:
                    admin_service = AdminService(db)
                    admin_user = admin_service.get_admin_by_id(uuid.UUID(decoded_token['sub']))
                    
                    if not admin_user or not admin_user.is_admin:
                        raise HTTPException(status_code=403, detail="Admin privileges required")
                    
                    if not admin_user.is_active:
                        raise HTTPException(status_code=403, detail="Admin account is inactive")
                    
                    # Set admin user in request state
                    request.state.admin_user = admin_user
                    request.state.user = decoded_token
                finally:
                    # Always close the session when done
                    db.close()
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin security middleware error: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Internal security error")
    
    return await call_next(request)
# In middleware.py - update the PasswordChangeMiddleware class
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
                # Import database session here
                from backend.database.base import SessionLocal
                
                # Create a new session for this request
                db = SessionLocal()
                try:
                    admin_service = AdminService(db)
                    
                    admin_user = admin_service.get_admin_by_id(uuid.UUID(user['sub']))
                    # Check if attribute exists before accessing it
                    if admin_user and hasattr(admin_user, 'requires_password_change') and admin_user.requires_password_change:
                        raise HTTPException(
                            status_code=403,
                            detail={
                                "message": "Password change required",
                                "code": "PASSWORD_CHANGE_REQUIRED"
                            }
                        )
                finally:
                    # Always close the session when done
                    db.close()
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Password check middleware error: {str(e)}")
        
        return await call_next(request)