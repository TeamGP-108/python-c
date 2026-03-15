from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.compile import router as compile_router

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
        "endpoints": {
            "compile": "/api/compile",
            "health": "/api/health"
        }
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Python Compiler API"}
