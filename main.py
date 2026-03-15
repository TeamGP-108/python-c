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
            params      = parse_qs(parsed.query)
            code        = params.get("code",   [None])[0]
            stdin_input = params.get("stdin",  [""])[0]
            fmt         = params.get("format", ["json"])[0].lower()

            if not code or not code.strip():
                self._respond_json(400, {"error": "Missing 'code' query parameter"})
                return

            if fmt == "stream":
                self._stream_code(code, stdin_input)
            elif fmt == "text":
                result = self._execute_code(code, stdin_input)
                self._respond_plain(result)
            else:
                result = self._execute_code(code, stdin_input)
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

            if fmt == "stream":
                self._stream_code(code, stdin_input)
            elif fmt == "text":
                result = self._execute_code(code, stdin_input)
                self._respond_plain(result)
            else:
                result = self._execute_code(code, stdin_input)
                self._respond_json(200, result)
        else:
            self._respond_json(404, {"error": "Not found"})

    # ─── STREAMING (SSE) ────────────────────────────────────────────────────────

    def _stream_code(self, code: str, stdin_input: str = ""):
        """Stream output line-by-line using Server-Sent Events."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir="/tmp"
            ) as f:
                f.write(code)
                tmp_path = f.name

            # Send SSE headers
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")   # disable nginx buffering
            self.end_headers()

            proc = subprocess.Popen(
                [sys.executable, "-u", tmp_path],   # -u = unbuffered stdout
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONPATH": "",
                    "HOME": "/tmp",
                    "PYTHONUNBUFFERED": "1",
                }
            )

            # Feed stdin then close it
            if stdin_input:
                proc.stdin.write(stdin_input)
            proc.stdin.close()

            import threading, queue

            output_queue = queue.Queue()

            def read_stream(stream, stream_type):
                for line in iter(stream.readline, ""):
                    output_queue.put((stream_type, line))
                output_queue.put((stream_type, None))   # sentinel

            t_out = threading.Thread(target=read_stream, args=(proc.stdout, "stdout"))
            t_err = threading.Thread(target=read_stream, args=(proc.stderr, "stderr"))
            t_out.daemon = True
            t_err.daemon = True
            t_out.start()
            t_err.start()

            done_streams = 0
            import time
            deadline = time.time() + 10   # 10-second timeout

            while done_streams < 2:
                if time.time() > deadline:
                    proc.kill()
                    self._sse_send("stderr", "[Timed out after 10s]\n")
                    break
                try:
                    stream_type, line = output_queue.get(timeout=0.1)
                    if line is None:
                        done_streams += 1
                    else:
                        self._sse_send(stream_type, line)
                except queue.Empty:
                    continue

            proc.wait()
            exit_code = proc.returncode

            # Final "done" event so client knows execution finished
            self._sse_event("done", json.dumps({"exit_code": exit_code}))

        except Exception as e:
            self._sse_send("stderr", f"Internal error: {e}\n")
            self._sse_event("done", json.dumps({"exit_code": -1}))
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _sse_send(self, stream_type: str, line: str):
        """Send a single SSE data line."""
        self._sse_event(stream_type, line)

    def _sse_event(self, event: str, data: str):
        """Write a full SSE event block."""
        msg = f"event: {event}\ndata: {data}\n\n"
        try:
            self.wfile.write(msg.encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass

    # ─── NON-STREAMING ──────────────────────────────────────────────────────────

    def _execute_code(self, code: str, stdin_input: str = "") -> dict:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir="/tmp"
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
        output = result["stdout"]
        if result["stderr"]:
            output += result["stderr"]
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
