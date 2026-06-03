"""Custom error handlers for API."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with detailed messages."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    errors = []
    for error in exc.errors():
        errors.append({
            'field': '.'.join(str(x) for x in error['loc']),
            'message': error['msg'],
            'type': error['type']
        })
    
    logger.warning(
        f"Validation error",
        extra={
            'request_id': request_id,
            'errors': errors
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            'error': 'validation_error',
            'message': 'Request validation failed',
            'details': errors,
            'request_id': request_id
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={'request_id': request_id},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'error': 'internal_server_error',
            'message': 'An internal error occurred',
            'request_id': request_id
        }
    )


class APIError(Exception):
    """Base API error class."""
    
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or 'api_error'
        super().__init__(self.message)


class ModelNotFoundError(APIError):
    """Raised when model file is not found."""
    
    def __init__(self, message: str = "Model not found"):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE, 'model_not_found')


class OptimizationError(APIError):
    """Raised when optimization fails."""
    
    def __init__(self, message: str = "Optimization failed"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, 'optimization_error')


class InvalidInputError(APIError):
    """Raised when input data is invalid."""
    
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, 'invalid_input')


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(
        f"API error: {exc.message}",
        extra={
            'request_id': request_id,
            'error_code': exc.error_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'error': exc.error_code,
            'message': exc.message,
            'request_id': request_id
        }
    )
