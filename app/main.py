import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException

from app.api.router import router
from app.utils.file_utils import purge_old_files
from app.core.config import settings

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dting_toolkit")

async def clean_temp_files_periodically():
    """
    Background worker that runs every minute to clean up files older than 15 minutes.
    """
    logger.info("Background cleanup task started.")
    while True:
        try:
            purge_old_files(max_age_seconds=900)  # 15 minutes
        except Exception as e:
            logger.error(f"Error during background file cleanup: {e}")
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: trigger cleanup once and start background loop
    try:
        purge_old_files(max_age_seconds=0) # Clean everything from previous run on start
    except Exception as e:
        logger.error(f"Initial cleanup failed: {e}")
        
    cleanup_task = asyncio.create_task(clean_temp_files_periodically())
    yield
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Background cleanup task stopped.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# CORS Configuration
# Astro usually runs on port 4321. We allow requests from typical local environments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(router)

# Custom Exception Handlers to match required error response schema: {"success": false, "message": "..."}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_messages = []
    for error in exc.errors():
        # Clean up path locations (e.g. ['body', 'quality'])
        loc = " -> ".join(str(x) for x in error.get("loc", []) if x not in ("body", "query", "header", "path"))
        msg = error.get("msg", "invalid value")
        error_messages.append(f"{loc}: {msg}" if loc else msg)
    
    joined_message = "; ".join(error_messages)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": f"Validation Error: {joined_message}"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled system error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "An internal server error occurred."}
    )

@app.get("/")
async def root():
    return {
        "success": True,
        "message": f"Welcome to the {settings.PROJECT_NAME} API."
    }
