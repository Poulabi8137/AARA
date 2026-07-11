import subprocess
import time
import sys
import urllib.request
import urllib.error

# Start backend FIRST
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\backend"
)

print("[TEST] Backend started. Waiting 5 seconds...")
time.sleep(5)

# Start frontend WITHOUT turbopack
frontend_cmd = r'cd /d "C:\Users\Poulabi Ghosh\Downloads\Agentic AI\aara-frontend" && node_modules\.bin\next.cmd dev --port 3000 --no-turbopack'
print("[TEST] Starting frontend WITHOUT turbopack...")
frontend = subprocess.Popen(
    frontend_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    shell=True,
)

print("[TEST] Waiting 30 seconds for frontend to fully initialize...")
time.sleep(30)

if frontend.poll() is not None:
    print("[TEST] Frontend failed to start")
    stdout, stderr = frontend.communicate()
    try:
        err_text = stderr.decode('utf-8', errors='replace')
    except:
        err_text = str(stderr)
    print("STDERR:")
    print(err_text[-5000:])
    backend.terminate()
    sys.exit(1)

print("[TEST] Frontend is running")

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
print("\n[TEST] Testing routes WITHOUT turbopack...")
routes = [
    "http://127.0.0.1:3000/projects/test-id",
    "http://127.0.0.1:3000/projects/test-id/agent-workspace",
    "http://127.0.0.1:3000/projects/test-id/timeline",
    "http://127.0.0.1:3000/projects/test-id/papers",
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
