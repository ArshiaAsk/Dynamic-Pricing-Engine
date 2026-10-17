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
