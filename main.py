from http.server import BaseHTTPRequestHandler
import json
import subprocess
import sys
import os
import tempfile
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._respond_json(200, {"status": "ok", "python": sys.version})
            return

        if parsed.path == "/run":
            params = parse_qs(parsed.query)

            code        = params.get("code",   [None])[0]
            stdin_input = params.get("stdin",  [""])[0]
            fmt         = params.get("format", ["json"])[0].lower()  # "json" or "text"

            if not code or not code.strip():
                if fmt == "text":
                    self._respond_text(400, "Error: Missing 'code' query parameter\n")
                else:
                    self._respond_json(400, {"error": "Missing 'code' query parameter"})
                return

            result = self._execute_code(code, stdin_input)

            if fmt == "text":
                self._respond_plain(result)
            else:
                self._respond_json(200, result)
            return

        self._respond_json(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data        = json.loads(body)
                code        = data.get("code", "")
                stdin_input = data.get("stdin", "")
                fmt         = data.get("format", "json").lower()
            except json.JSONDecodeError:
                self._respond_json(400, {"error": "Invalid JSON"})
                return

            if not code.strip():
                self._respond_json(400, {"error": "No code provided"})
                return

            result = self._execute_code(code, stdin_input)

            if fmt == "text":
                self._respond_plain(result)
            else:
                self._respond_json(200, result)
        else:
            self._respond_json(404, {"error": "Not found"})

    def _execute_code(self, code: str, stdin_input: str = "") -> dict:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                delete=False,
                dir="/tmp"
            ) as f:
                f.write(code)
                tmp_path = f.name

            try:
                proc = subprocess.run(
                    [sys.executable, tmp_path],
                    input=stdin_input,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={
                        "PATH": os.environ.get("PATH", ""),
                        "PYTHONPATH": "",
                        "HOME": "/tmp",
                    }
                )
                return {
                    "stdout":    proc.stdout[:50_000],
                    "stderr":    proc.stderr[:10_000],
                    "exit_code": proc.returncode,
                    "timed_out": False,
                }
            except subprocess.TimeoutExpired:
                return {
                    "stdout":    "",
                    "stderr":    "Execution timed out (10s limit).\n",
                    "exit_code": -1,
                    "timed_out": True,
                }
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except Exception as e:
            return {
                "stdout":    "",
                "stderr":    f"Internal error: {str(e)}\n",
                "exit_code": -1,
                "timed_out": False,
            }

    def _respond_plain(self, result: dict):
        """
        Return output exactly like a terminal:
        - stdout first
        - stderr after (if any)
        - if timed out, append a notice
        """
        output = result["stdout"]
        if result["stderr"]:
            output += result["stderr"]
        if result["timed_out"]:
            output += "\n[Process timed out after 10s]\n"

        self._respond_text(200, output)

    def _respond_text(self, status: int, text: str):
        body = text.encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _respond_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        pass
