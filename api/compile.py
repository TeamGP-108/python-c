from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from utils.compiler import execute_python_code
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter()

class CodeRequest(BaseModel):
    code: str = Field(..., description="Python code to execute", min_length=1)
    stdin: str = Field(default="", description="Standard input for the code")
    timeout: Optional[int] = Field(default=5, description="Execution timeout in seconds", ge=1, le=30)

class CodeResponse(BaseModel):
    output: str
    error: Optional[str] = None
    execution_time: float
    success: bool

@router.post("/compile", response_model=CodeResponse)
async def compile_code(request: CodeRequest):
    """
    Compile and execute Python code
    
    - **code**: Python code to execute
    - **stdin**: Optional input for the program
    - **timeout**: Maximum execution time (1-30 seconds)
    """
    logger.info(f"Received compilation request, code length: {len(request.code)}")
    
    try:
        start_time = time.time()
        result = execute_python_code(request.code, request.stdin, request.timeout)
        execution_time = time.time() - start_time
        
        return CodeResponse(
            output=result.get("output", ""),
            error=result.get("error"),
            execution_time=execution_time,
            success=result.get("error") is None
        )
    except Exception as e:
        logger.error(f"Compilation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compile/batch")
async def compile_batch(codes: list[CodeRequest]):
    """Execute multiple code snippets"""
    results = []
    for code_request in codes:
        try:
            result = await compile_code(code_request)
            results.append(result)
        except Exception as e:
            results.append({
                "error": str(e),
                "success": False,
                "code": code_request.code[:100] + "..."  # Truncated preview
            })
    return {"results": results}
