from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.compiler import execute_python_code

router = APIRouter()

class CodeRequest(BaseModel):
    code: str
    stdin: str = ""

class CodeResponse(BaseModel):
    output: str
    error: str = None
    execution_time: float = None

@router.post("/compile", response_model=CodeResponse)
async def compile_code(request: CodeRequest):
    """
    Compile and execute Python code
    """
    try:
        result = execute_python_code(request.code, request.stdin)
        return CodeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
