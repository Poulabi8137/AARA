import subprocess
import time
import sys
import urllib.request
import urllib.error
import json

def test_backend():
    # Start uvicorn
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\backend"
    )

    # Wait for startup
    time.sleep(5)

    if p.poll() is not None:
        print("Uvicorn exited early, code:", p.poll())
        stdout, stderr = p.communicate()
        print("STDOUT:", stdout.decode()[-500:])
        print("STDERR:", stderr.decode()[-1000:])
        return

    base = "http://127.0.0.1:8000"
    endpoints = [
        ("GET", "/api/v1/projects", None),
        ("POST", "/api/v1/projects", b'{"workspace_id":"test","name":"Test"}'),
        ("GET", "/api/v1/workspaces", None),
        ("POST", "/api/v1/workspaces", b'{"title":"Test","name":"Test","description":"Test"}'),
        ("POST", "/api/v1/research/queries", b'{"topic":"test","max_papers":5}'),
        ("GET", "/api/v1/research/sessions", None),
        ("GET", "/health", None),
    ]

    for method, path, body in endpoints:
        url = base + path
        try:
            req = urllib.request.Request(url, data=body, method=method)
            if body:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp_body = resp.read().decode()
                print(f"{method} {path} -> {resp.status}: {resp_body[:200]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"{method} {path} -> {e.code}: {body[:200]}")
        except Exception as e:
            print(f"{method} {path} -> ERROR: {e}")

    p.terminate()
    p.wait(timeout=5)
    print("\nUvicorn stopped")

if __name__ == "__main__":
    test_backend()
