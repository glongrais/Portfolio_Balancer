"""
API Middleware and Exception Handlers
"""
import logging
import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

async def log_requests_middleware(request: Request, call_next):
    """
    Middleware to log all incoming requests and their response times
    """
    start_time = time.time()
    
    # Log the request
    logger.debug(f"Incoming request: {request.method} {request.url.path}")
    
    # Process the request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    logger.debug(
        f"Completed: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.2f}s"
    )
    
    # Add custom header with response time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for validation errors
    """
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Request validation failed"
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Custom handler for HTTP exceptions
    """
    logger.warning(
        f"HTTP exception on {request.url.path}: "
        f"Status {exc.status_code} - {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc.detail),
            "status_code": exc.status_code
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions
    """
    logger.error(
        f"Unhandled exception on {request.url.path}: {type(exc).__name__} - {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "message": str(exc) if logger.level <= logging.DEBUG else "Internal server error"
        }
    )

