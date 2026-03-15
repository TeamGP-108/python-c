import subprocess
import tempfile
import os
import time
import sys

def execute_python_code(code: str, stdin: str = "") -> dict:
    """
    Execute Python code in a safe environment
    """
    result = {
        "output": "",
        "error": None,
        "execution_time": 0
    }
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Start timing
        start_time = time.time()
        
        # Execute the code with timeout
        process = subprocess.Popen(
            [sys.executable, temp_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5  # 5 seconds timeout
        )
        
        stdout, stderr = process.communicate(input=stdin, timeout=5)
        
        # Calculate execution time
        result["execution_time"] = time.time() - start_time
        
        if stderr:
            result["error"] = stderr
        else:
            result["output"] = stdout
            
    except subprocess.TimeoutExpired:
        process.kill()
        result["error"] = "Execution timeout (max 5 seconds)"
    except Exception as e:
        result["error"] = str(e)
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except:
            pass
    
    return result
