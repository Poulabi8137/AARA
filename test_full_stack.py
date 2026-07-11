import subprocess
import time
import sys
import urllib.request
import urllib.error
import json

print("[TEST] Starting full stack test...")

# Start backend
print("[TEST] Starting backend on port 8000...")
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\backend"
)

# Start frontend - use shell=True for the .cmd file
frontend_cwd = r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\aara-frontend"
frontend_cmd = r'cd /d "C:\Users\Poulabi Ghosh\Downloads\Agentic AI\aara-frontend" && node_modules\.bin\next.cmd dev --port 3000'
print("[TEST] Starting frontend on port 3000...")
frontend = subprocess.Popen(
    frontend_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    shell=True,
)

print("[TEST] Waiting for servers to start...")
time.sleep(20)

# Check if servers are running
if backend.poll() is not None:
    print("[TEST] Backend failed to start")
    stdout, stderr = backend.communicate()
    print("STDERR:", stderr.decode()[-1000:])
    frontend.terminate()
    sys.exit(1)

if frontend.poll() is not None:
    print("[TEST] Frontend failed to start")
    stdout, stderr = frontend.communicate()
    print("STDERR:", stderr.decode()[-1000:])
    backend.terminate()
    sys.exit(1)

print("[TEST] Both servers are running")

def req(url, method="GET", data=None, headers=None):
    body = json.dumps(data).encode() if data else None
    h = headers or {}
    if data and "Content-Type" not in h:
        h["Content-Type"] = "application/json"
    try:
        rq = urllib.request.Request(url, data=body, headers=h, method=method)
        with urllib.request.urlopen(rq, timeout=10) as resp:
            return resp.status, resp.read().decode()[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception as e:
        return None, str(e)

# Test backend directly
print("\n[TEST] Testing backend directly...")
status, body = req("http://127.0.0.1:8000/api/v1/projects", "POST", {"workspace_id": "test", "name": "Test"})
print(f"  POST http://127.0.0.1:8000/api/v1/projects -> {status}: {body[:200]}")

# Test frontend rewrite
print("\n[TEST] Testing frontend rewrite (port 3000 -> 8000)...")
status, body = req("http://127.0.0.1:3000/api/v1/projects", "POST", {"workspace_id": "test", "name": "Test"})
print(f"  POST http://127.0.0.1:3000/api/v1/projects -> {status}: {body[:200]}")

# Test frontend pages
print("\n[TEST] Testing frontend pages...")
pages = ["/", "/research", "/research/new", "/dashboard", "/login", "/register"]
for page in pages:
    status, body = req(f"http://127.0.0.1:3000{page}")
    print(f"  GET http://127.0.0.1:3000{page} -> {status}")

# Test dynamic project page
print("\n[TEST] Testing dynamic project pages...")
proj_pages = ["/projects/test-id", "/projects/test-id/agent-workspace"]
for page in proj_pages:
    status, body = req(f"http://127.0.0.1:3000{page}")
    print(f"  GET http://127.0.0.1:3000{page} -> {status}")

print("\n[TEST] Cleaning up...")
frontend.terminate()
backend.terminate()
frontend.wait(timeout=5)
backend.wait(timeout=5)
print("[TEST] Done")
