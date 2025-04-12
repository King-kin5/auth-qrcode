import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.admin.adminservice import AdminStudentService
from backend.database.config import get_db
from backend.security.config import settings
from fastapi.exceptions import RequestValidationError, HTTPException
from backend.api import QRroute, admin, student
from starlette.middleware.base import BaseHTTPMiddleware
from backend.database.base import init_database, test_database_connection
from backend.security.exceptions import(
    custom_exception_handler,
    custom_validation_exception_handler,
    AuthenticationException,
    SecurityError
)
from backend.security.middleware import(
    PasswordChangeMiddleware,
    authentication_middleware,
    logging_middleware,
    admin_security_middleware,
)
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

async def debug_middleware(request: Request, call_next):
    """Temporary debugging middleware"""
    path = request.url.path
    logger.debug(f"Processing request: {request.method} {path}")
    logger.debug(f"Headers: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        logger.debug(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise

def create_application() -> FastAPI:
    """Application factory function"""
    # Create FastAPI app instance
    app = FastAPI(
        title="QRsystem",
        description="Web Auth Qr system",
        version="0.1.0",
    )
    
    # CORS middleware should be first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )

    # Exception handlers
    app.add_exception_handler(HTTPException, custom_exception_handler)
    app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)
    app.add_exception_handler(AuthenticationException, custom_exception_handler)
    app.add_exception_handler(SecurityError, custom_exception_handler)

    # Debug middleware (temporary)
    app.middleware("http")(debug_middleware)

    # Middleware stack - order matters (executes bottom to top)
    app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)
    app.add_middleware(PasswordChangeMiddleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=authentication_middleware)  # Auth first
    # Frontend paths setup
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
    
    # Initialize templates
    templates = Jinja2Templates(directory=frontend_path)
    
    # Mount static files
    
    # Mount static files
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    # Include the API routes
    app.include_router(QRroute.router, prefix="/qr", tags=["QR Code"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(student.router, prefix="/api/v1/students", tags=["students"])
    
    # Admin frontend routes
    @app.get("/admin/login", include_in_schema=False)
    async def get_admin_login():
        """Serve admin login page"""
        admin_file = os.path.join(frontend_path, "admin_login_page.html")
        return FileResponse(admin_file)
    
    @app.get("/admin/dashboard", include_in_schema=False)
    async def get_admin_dashboard():
        """Serve admin dashboard page"""
        dashboard_file = os.path.join(frontend_path, "admin_dashboard.html")
        return FileResponse(
            dashboard_file,
            headers={"Content-Type": "text/html; charset=utf-8"}
        )
       
    @app.get("/admin/register-student", include_in_schema=False)
    async def get_register_student():
        """Serve student registration page"""
        register_file = os.path.join(frontend_path, "student_registration.html")
        return FileResponse(register_file)
        
    @app.get("/admin/view-students", include_in_schema=False)
    async def get_view_students():
        """Serve view students page"""
        students_file = os.path.join(frontend_path, "view_students.html")
        return FileResponse(students_file)
    
    @app.get("/admin/create-admin", include_in_schema=False)
    async def get_create_admin():
        """Serve create admin page"""
        create_admin_file = os.path.join(frontend_path, "create_admin.html")
        return FileResponse(create_admin_file)
    
    @app.get("/admin/search-students", include_in_schema=False)
    async def get_search_students():
        """Serve search students page"""
        search_file = os.path.join(frontend_path, "search_students.html")
        return FileResponse(search_file)
    @app.get("/student/{student_matric:path}")
    async def student_details(request: Request, student_matric: str, db: Session = Depends(get_db)):
        service = AdminStudentService(db)
        try:
          student = service.get_student_by_id(student_matric)
        except Exception as e:
            raise HTTPException(status_code=404, detail="Student not found")
        return templates.TemplateResponse("student_details.html", {"request": request, "student": student})

    
    # Main index route
    @app.get("/", include_in_schema=False)
    async def get_index():
        """Serve main index page"""
        index_file = os.path.join(frontend_path, "index.html")
        return FileResponse(index_file)
    
    return app

# Create the application
app = create_application()

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        init_database()
        if not test_database_connection():
            logger.error("Failed to connect to database during startup")
            raise Exception("Database connection failed")
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    try:
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Application shutdown failed: {e}")
        raise
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )