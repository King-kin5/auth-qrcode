import logging
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

class QrcodesExceptions(Exception):
    """Base exception for all Qrcodes application errors"""
    status_code = 500  # Default status code
    
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)

class AuthenticationException(QrcodesExceptions):
    """Raised when there are authentication-related errors"""
    status_code = 401  # Default status code for authentication errors
    
    def __init__(self, message: str = "Authentication failed", status_code: int = None):
        super().__init__(message, status_code)

class SecurityError(QrcodesExceptions):
    """Raised when there are Security errors"""
    status_code = 403  # Default status code for security errors
    
    def __init__(self, message: str = "Security problem", status_code: int = None):
        super().__init__(message, status_code)

async def custom_exception_handler(request: Request, exc: Exception):
    """
    Generic exception handler that handles both HTTP and custom exceptions
    """
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
    elif isinstance(exc, QrcodesExceptions):
        status_code = exc.status_code
        detail = exc.message
    else:
        status_code = 500
        detail = "Internal Server Error"
    
    logging.error(f"Error {status_code}: {detail}")
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "message": detail
        }
    )

async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for validation errors
    """
    errors = exc.errors()
    error_details = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        } for error in errors
    ]
    
    logging.error(f"Validation Error: {error_details}")
    
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": error_details
        }
    )