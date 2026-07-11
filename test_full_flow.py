import subprocess
import time
import sys
import urllib.request
import urllib.error
import json

# Start uvicorn in background
print("[TEST] Starting backend...")
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r"C:\Users\Poulabi Ghosh\Downloads\Agentic AI\backend"
)
time.sleep(5)

if backend.poll() is not None:
    print("[TEST] Backend failed to start")
    stdout, stderr = backend.communicate()
    print("STDERR:", stderr.decode()[-500:])
    sys.exit(1)

base = "http://127.0.0.1:8000"

def req(method, path, data=None, headers=None):
    url = base + path
    body = json.dumps(data).encode() if data else None
    h = headers or {}
    if data and "Content-Type" not in h:
        h["Content-Type"] = "application/json"
    try:
        rq = urllib.request.Request(url, data=body, headers=h, method=method)
        with urllib.request.urlopen(rq, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except:
            return e.code, {"raw": body}
    except Exception as e:
        return None, {"error": str(e)}

# Step 1: Register a user
print("\n[TEST] Step 1: Register user")
status, resp = req("POST", "/api/v1/auth/register", {
    "email": "test404@example.com",
    "password": "TestPass123!",
    "display_name": "Test User"
})
print(f"  Register: {status} -> {resp}")

# Step 2: Login
print("\n[TEST] Step 2: Login")
status, resp = req("POST", "/api/v1/auth/login", {
    "email": "test404@example.com",
    "password": "TestPass123!"
})
print(f"  Login: {status} -> {resp}")
if status != 200:
    print("[TEST] Login failed, cannot continue")
    backend.terminate()
    backend.wait(timeout=5)
    sys.exit(1)

access_token = resp.get("access_token")
headers = {"Authorization": f"Bearer {access_token}"}

# Step 3: Create workspace
print("\n[TEST] Step 3: Create workspace")
status, resp = req("POST", "/api/v1/workspaces", {"title": "Test Workspace", "name": "Test Workspace"}, headers)
print(f"  Create workspace: {status} -> {resp}")
workspace_id = resp.get("id") if status in (200, 201) else None

if not workspace_id:
    # Try listing workspaces
    status, resp = req("GET", "/api/v1/workspaces", headers=headers)
    print(f"  List workspaces: {status} -> {resp}")
    if status == 200 and resp.get("items"):
        workspace_id = resp["items"][0]["id"]

if not workspace_id:
    print("[TEST] No workspace available, cannot continue")
    backend.terminate()
    backend.wait(timeout=5)
    sys.exit(1)

# Step 4: Create project (this is what happens when clicking Start Research)
print("\n[TEST] Step 4: Create project")
status, resp = req("POST", "/api/v1/projects", {
    "workspace_id": workspace_id,
    "name": "Test Research Project",
    "research_goal": "Testing 404 issue"
}, headers)
print(f"  Create project: {status} -> {resp}")
project_id = resp.get("id") if status in (200, 201) else None

# Step 5: Submit research query
if project_id:
    print("\n[TEST] Step 5: Submit research query")
    status, resp = req("POST", "/api/v1/research/queries", {
        "query": "Test query",
        "project_id": project_id,
        "max_papers": 5
    }, headers)
    print(f"  Submit query: {status} -> {resp}")

# Check all project endpoints
print("\n[TEST] Checking project endpoints...")
proj_endpoints = [
    ("GET", f"/api/v1/projects/{project_id}"),
    ("PATCH", f"/api/v1/projects/{project_id}"),
    ("POST", f"/api/v1/projects/{project_id}/archive"),
]
for method, path in proj_endpoints:
    if project_id:
        status, resp = req(method, path, {"name": "Updated"} if method == "PATCH" else None, headers)
        print(f"  {method} {path}: {status}")

backend.terminate()
backend.wait(timeout=5)
print("\n[TEST] Done")
