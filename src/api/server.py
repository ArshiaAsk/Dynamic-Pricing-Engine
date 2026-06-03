import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.router import router
from src.api.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    ErrorHandlingMiddleware,
    TimeoutMiddleware
)
from src.api.error_handlers import (
     validation_exception_handler,
     generic_exception_handler,
     api_error_handler,
     APIError
 )
from fastapi.exceptions import RequestValidationError
from src.utils.env_config import get_config
from src.utils.logger import setup_logging
import os
import logging
 
 # Load configuration
config = get_config()
 
 # Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
log_format = os.getenv("LOG_FORMAT", "json")
log_dir = os.getenv("LOG_DIR", "logs")
setup_logging(level=log_level, log_format=log_format, log_dir=log_dir)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dynamic Pricing API",
    version="1.0.0",
    description="ML-powered dynamic pricing engine with demand forecasting and price optimization",
    docs_url="/docs",
    redoc_url="/redoc"
)
# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Add CORS middleware
cors_enabled = config.get_bool("CORS_ENABLED", True)
if cors_enabled:
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
 
 # Add custom middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Add rate limiting if enabled
rate_limit_enabled = config.get_bool("RATE_LIMIT_ENABLED", True)
if rate_limit_enabled:
    rate_limit_requests = config.get_int("RATE_LIMIT_REQUESTS", 100)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit_requests)

# Add timeout middleware
timeout = config.get_int("REQUEST_TIMEOUT", 30)
app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout)

 # Include API router
app.include_router(router, prefix="/v1")

 
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        f"Starting Dynamic Pricing API",
        extra={
            'environment': config.env,
            'version': '1.0.0'
        }
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Dynamic Pricing API")
 
 
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Dynamic Pricing API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/v1/health"
    }
 

if __name__ == "__main__":
     host = os.getenv("API_HOST", "0.0.0.0")
     port = int(os.getenv("API_PORT", "8000"))
     reload = config.get_bool("API_RELOAD", False)
     workers = config.get_int("API_WORKERS", 1)
     
     uvicorn.run(
         "src.api.server:app",
         host=host,
         port=port,
         reload=reload,
         workers=workers if not reload else 1
     )
