# utils/piston_compiler.py
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PistonCompiler:
    """Compile code using Piston API"""
    
    API_URL = "https://emkc.org/api/v2/piston/execute"
    
    @classmethod
    def execute(cls, code: str, stdin: str = "", timeout: int = 5) -> Dict[str, Any]:
        """Execute code using Piston API"""
        
        try:
            response = requests.post(
                cls.API_URL,
                json={
                    "language": "python",
                    "version": "3.10.0",
                    "files": [
                        {
                            "name": "script.py",
                            "content": code
                        }
                    ],
                    "stdin": stdin,
                    "args": [],
                    "compile_timeout": timeout * 1000,
                    "run_timeout": timeout * 1000
                },
                timeout=timeout + 2  # Add buffer for network
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("run"):
                    return {
                        "output": data["run"].get("stdout", ""),
                        "error": data["run"].get("stderr", None)
                    }
                else:
                    return {
                        "output": "",
                        "error": "No output from compiler"
                    }
            else:
                return {
                    "output": "",
                    "error": f"Compiler API error: {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "output": "",
                "error": f"Request timeout after {timeout} seconds"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                "output": "",
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "output": "",
                "error": f"Unexpected error: {str(e)}"
            }
