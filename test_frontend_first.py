import subprocess
import time
import sys
import urllib.request
import urllib.error

# Start frontend FIRST
frontend_cmd = r'cd /d "C:\Users\Poulabi Ghosh\Downloads\Agentic AI\aara-frontend" && node_modules\.bin\next.cmd dev --port 3000'
print("[TEST] Starting frontend on port 3000...")
frontend = subprocess.Popen(
    frontend_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    shell=True,
)

print("[TEST] Waiting 20 seconds for frontend to initialize...")
time.sleep(20)

if frontend.poll() is not None:
    print("[TEST] Frontend failed to start")
    stdout, stderr = frontend.communicate()
    try:
        err_text = stderr.decode('utf-8', errors='replace')[-1500:]
    except:
        err_text = str(stderr)[-1500:]
    print("STDERR:", err_text)
    sys.exit(1)

print("[TEST] Frontend is running. Now starting backend...")

# Start backend AFTER frontend
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\backend"
)

print("[TEST] Waiting 10 seconds for backend to initialize...")
time.sleep(10)

if backend.poll() is not None:
    print("[TEST] Backend failed to start")
    stdout, stderr = backend.communicate()
    try:
        err_text = stderr.decode('utf-8', errors='replace')[-1500:]
    except:
        err_text = str(stderr)[-1500:]
    print("STDERR:", err_text)
    frontend.terminate()
    sys.exit(1)

print("[TEST] Both servers are running")

def req(url, method="GET"):
    try:
        rq = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(rq, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return None

# Test routes
print("\n[TEST] Testing routes (frontend started first, then backend)...")
routes = [
    "http://127.0.0.1:3000/projects/test-id",
    "http://127.0.0.1:3000/projects/test-id/agent-workspace",
    "http://127.0.0.1:3000/projects/test-id/timeline",
]

for url in routes:
    status = req(url)
    print(f"  GET {url} -> {status}")

print("\n[TEST] Cleaning up...")
frontend.terminate()
backend.terminate()
frontend.wait(timeout=5)
backend.wait(timeout=5)
print("[TEST] Done")
