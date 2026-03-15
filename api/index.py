from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.compile import router as compile_router
import logging
import sys
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Python Code Compiler API",
    description="API for compiling and running Python code",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(compile_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Python Code Compiler API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "compile": "/api/compile",
            "health": "/api/health",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Python Compiler API",
        "timestamp": "2024-01-01T00:00:00Z"  # You can use datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An error occurred"
        }
    )
