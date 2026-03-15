import requests
import time

def execute_python_code(code: str, stdin: str = "") -> dict:
    """
    Execute Python code using Piston API (free, no API key required)
    """
    result = {
        "output": "",
        "error": None,
        "execution_time": 0
    }
    
    try:
        start_time = time.time()
        
        # Using Piston API (free public API)
        response = requests.post(
            "https://emkc.org/api/v2/piston/execute",
            json={
                "language": "python",
                "version": "3.10.0",
                "files": [
                    {
                        "name": "main.py",
                        "content": code
                    }
                ],
                "stdin": stdin,
                "args": [],
                "compile_timeout": 10000,
                "run_timeout": 3000
            },
            timeout=10
        )
        
        result["execution_time"] = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get("run"):
                if data["run"].get("stderr"):
                    result["error"] = data["run"]["stderr"]
                else:
                    result["output"] = data["run"]["stdout"]
        else:
            result["error"] = f"API Error: {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request failed: {str(e)}"
    except Exception as e:
        result["error"] = str(e)
    
    return result
