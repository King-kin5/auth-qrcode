
import logging
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

class QrcodesExecptions(Exception):
    """Base exception for all Qrcodes application errors"""
    pass

class AuthenticationException(QrcodesExecptions):
    """Raised when there are authentication-related errors"""
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)

class SecurityError(QrcodesExecptions):
    """Raised when there are Security errors"""
    def __init__(self, message: str = "Security problem"):
        self.message = message
        super().__init__(self.message)  

def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom handler for HTTP exceptions
    """
    logging.error(f"HTTP Error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        }
    )

def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
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